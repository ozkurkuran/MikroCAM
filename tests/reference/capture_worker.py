"""One sandboxed board's real parser/CAM stages from the declared source checkout."""
import argparse
from contextlib import redirect_stdout
import importlib.metadata
import hashlib
import inspect
import json
import math
from pathlib import Path
import platform
import sys
import sysconfig
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from baseline_host import construct, load_engine, sandbox_settings


def runtime_info() -> dict:
    """Record the explicitly selected interpreter's actual runtime, without CAM imports."""
    if (sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 13)
            or platform.architecture()[0] != '64bit' or sysconfig.get_config_var('Py_GIL_DISABLED')):
        raise ValueError('Reference capture requires standard CPython 3.13 x64')
    dependencies = {distribution.metadata['Name']: distribution.version
                    for distribution in importlib.metadata.distributions()
                    if distribution.metadata['Name']}
    return {'python': platform.python_version(), 'architecture': platform.architecture()[0],
            'dependencies': dict(sorted(dependencies.items())), 'harness_sha256': '0' * 64}


def _record(input_path: str, stage: str, source_units: str | None = None) -> dict:
    return {'input_path': input_path, 'stage': stage, 'status': 'ok', 'units': 'mm',
            'source_units': source_units, 'tools': [], 'geometry_wkb': [], 'paths': [],
            'gcode': None, 'diagnostic': None}


def _normalize(parser) -> str:
    units = parser.units
    if units not in ('MM', 'IN'):
        raise ValueError(f'Actual parser units are unsupported: {units!r}')
    parser.convert_units('MM')
    if parser.units != 'MM':
        raise ValueError('Native parser conversion did not produce MM')
    return units


def _wkb(value, *, ordered: bool = False) -> list[str]:
    from shapely import get_coordinate_dimension, get_coordinates, get_num_coordinates, normalize, to_wkb
    values = []
    children = value if isinstance(value, (list, tuple)) else [value]
    for geometry in children:
        if isinstance(geometry, (list, tuple)):
            values.extend(_wkb(geometry, ordered=ordered))
            continue
        if (geometry is None or geometry.is_empty or not geometry.is_valid
                or get_coordinate_dimension(geometry) != 2):
            raise ValueError('Actual output is empty, invalid or not planar XY geometry')
        if get_num_coordinates(geometry) > 2_000_000:
            raise ValueError('Actual output exceeds geometry vertex limit')
        if any(not math.isfinite(float(coordinate)) for point in get_coordinates(geometry)
               for coordinate in point):
            raise ValueError('Actual output contains nonfinite XY coordinates')
        encoded = to_wkb(geometry if ordered else normalize(geometry), hex=True,
                         byte_order=1, output_dimension=2, flavor='iso', include_srid=False)
        if len(encoded) > 128 * 1024 * 1024:
            raise ValueError('Actual output exceeds decoded WKB limit')
        values.append(encoded)
    if not values:
        raise ValueError('Actual stage produced no geometry')
    return values


def _gerber(engine, filename: Path) -> object:
    parser = construct(engine, engine.Gerber)
    result = parser.parse_file(str(filename))
    if result == 'fail':
        raise ValueError('Actual Gerber parser returned fail')
    return parser


def _excellon(engine, filename: Path, parameters: dict) -> object:
    kwargs = dict(parameters)
    circle = kwargs.pop('circle_steps')
    key = ('excellon_circle_steps' if 'excellon_circle_steps'
           in inspect.signature(engine.Excellon).parameters else 'geo_steps_per_circle')
    parser = construct(engine, engine.Excellon, **kwargs, **{key: circle})
    # The real Excellon host object supplies this non-geometric tool metadata.
    parser.default_data = {}
    result = parser.parse_file(str(filename))
    if result == 'fail':
        raise ValueError('Actual Excellon parser returned fail')
    return parser


def _tools(parser) -> list[dict]:
    """Retain exact native tool/drill/slot multiplicity after native mm conversion."""
    tools = []
    for tool_id in sorted(parser.tools, key=lambda value: str(value)):
        tool = parser.tools[tool_id]
        if not math.isfinite(tool['tooldia']) or tool['tooldia'] <= 0:
            raise ValueError('Actual Excellon tool diameter is not positive finite mm')
        tools.append({'id': str(tool_id), 'diameter_mm': tool['tooldia'],
                      'drills': [list(point.coords[0]) for point in tool['drills']],
                      'slots': [[list(start.coords[0]), list(end.coords[0])]
                                for start, end in tool['slots']]})
    if not tools:
        raise ValueError('Actual Excellon parser produced no tools')
    return tools


def _cnc(engine, isolation, parameters: dict) -> tuple[str, list]:
    from shapely import union_all
    polygons = union_all(isolation if isinstance(isolation, list) else [isolation])
    geometry = construct(engine, engine.Geometry, geo_steps_per_circle=parameters['steps_per_circle'])
    geometry.solid_geometry = [polygons.boundary]
    bounds = polygons.bounds
    options = dict(name='reference-isolation', type='Geometry', tool_dia=parameters['tooldia'],
                   xmin=bounds[0], ymin=bounds[1], xmax=bounds[2], ymax=bounds[3])
    geometry.obj_options = geometry.options = options
    geometry.multigeo = False
    cnc = construct(engine, engine.CNCjob, units='MM', steps_per_circle=parameters['steps_per_circle'])
    cnc.obj_options = cnc.options = options
    cnc.origin_kind = 'geometry'
    cnc.coords_decimals, cnc.fr_decimals = parameters['coords_decimals'], parameters['fr_decimals']
    kwargs = {key: value for key, value in parameters.items()
              if key not in ('coords_decimals', 'fr_decimals', 'steps_per_circle',
                             'coords_type', 'spindle_direction')}
    direction = ('spindle_dir' if 'spindle_dir'
                 in inspect.signature(cnc.generate_from_geometry_2).parameters else 'spindledir')
    kwargs[direction] = parameters['spindle_direction']
    generated = cnc.generate_from_geometry_2(geometry, **kwargs)
    if (not isinstance(generated, tuple) or len(generated) != 2
            or generated[0] == 'fail' or not all(isinstance(part, str) for part in generated)):
        raise ValueError('Actual CNC generation did not return body/header G-code')
    cnc.gcode = generated[1] + generated[0]
    if not cnc.gcode.strip():
        raise ValueError('Actual CNC generation produced empty G-code')
    parsed = cnc.gcode_parse(force_parsing=True)
    if not isinstance(parsed, list) or not parsed or len(parsed) > 200_000:
        raise ValueError('Actual CNC parser produced no usable bounded paths')
    paths = []
    vertices = 0
    for item in parsed:
        if item['geom'].geom_type not in ('Point', 'LineString'):
            raise ValueError('Actual parsed CNC path is not Point/LineString')
        vertices += len(item['geom'].coords)
        if vertices > 2_000_000:
            raise ValueError('Actual parsed CNC paths exceed vertex limit')
        paths.append({'kind': list(item['kind']), 'wkb_hex': _wkb(item['geom'], ordered=True)[0]})
    return cnc.gcode, paths


def capture_board(request: dict) -> dict:
    """Record real results or contextual failures without repairing or fabricating stages."""
    source = Path(request['source']).resolve(strict=True)
    if Path.cwd().resolve() != source:
        raise ValueError('Worker cwd differs from declared source')
    config, board, root = request['config'], request['board'], Path(request['root']).resolve(strict=True)
    engine = load_engine(source, config['parameters'])
    records = []
    for item in board['files']:
        parser, isolation, source_units, previous_error = None, None, None, None
        filename = (root / item['path']).resolve(strict=True)
        if not filename.is_relative_to(root):
            raise ValueError('Board input escapes declared dataset root')
        with filename.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != item['sha256']:
                raise ValueError(f'Board input changed after provenance validation: {item["path"]}')
        for stage in config['stages'][item['role']]:
            record = _record(item['path'], stage, source_units)
            try:
                if previous_error is not None:
                    raise ValueError(f'Previous actual stage failed: {previous_error}')
                if stage == 'gerber':
                    parser = _gerber(engine, filename)
                    source_units = parser.units if parser.units in ('MM', 'IN') else None
                    _normalize(parser)
                    record['geometry_wkb'] = _wkb(parser.solid_geometry)
                elif stage == 'excellon':
                    parser = _excellon(
                        engine, filename, config['parameters']['parser']['excellon'])
                    source_units = parser.units if parser.units in ('MM', 'IN') else None
                    _normalize(parser)
                    record['tools'] = _tools(parser)
                    record['geometry_wkb'] = _wkb(parser.solid_geometry)
                elif stage == 'isolation':
                    isolation = parser.isolation_geometry(config['parameters']['isolation']['offset_mm'])
                    record['geometry_wkb'] = _wkb(isolation)
                elif stage == 'cnc':
                    record['gcode'], record['paths'] = _cnc(engine, isolation, config['parameters']['cnc'])
                else:
                    raise ValueError(f'Unsupported requested stage: {stage}')
                record['source_units'] = source_units
            except Exception as error:
                previous_error = f'{type(error).__name__}: {error}'
                record = _record(item['path'], stage, source_units)
                record.update(status='error', diagnostic=f'{board["id"]}/{item["path"]}/{stage}: {previous_error}')
            records.append(record)
    return {'stages': records}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', action='store_true')
    parser.add_argument('--request', type=Path)
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix='mikrocam-reference-settings-') as directory:
        sandbox_settings(Path(directory))
        with redirect_stdout(sys.stderr):
            if args.runtime:
                result = runtime_info()
            else:
                if args.request is None:
                    raise ValueError('Worker requires an explicit request')
                request = json.loads(args.request.read_text(encoding='utf-8'))
                result = capture_board(request)
        print(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
