"""Strict bounded capture artifacts, preserving real stages and complete input evidence."""
import gzip
import os
from pathlib import Path
import re
import tempfile
import zlib

from mikrocam.core.reference_compare import MAX_PATHS, MAX_VERTICES, ReferencePath, ReferenceTool, _decode
from . import reference_data as codec


CAPTURE_FIELDS = {'board_id', 'engine', 'source', 'runtime', 'inputs', 'configuration', 'stages'}
STAGE_FIELDS = {'input_path', 'stage', 'status', 'units', 'source_units', 'tools',
                'geometry_wkb', 'paths', 'gcode', 'diagnostic'}


def _hashed_files(data: object, context: str) -> list:
    if not isinstance(data, list) or not data:
        raise ValueError(f'{context} requires nonempty file evidence')
    paths = []
    for item in data:
        record = codec._fields(item, {'path', 'sha256'}, context)
        paths.append(codec._relative(record['path'], context))
        codec._hash(record['sha256'], context)
    if len(paths) != len(set(paths)):
        raise ValueError(f'{context} contains duplicate paths')
    return data


def _runtime(data: object) -> dict:
    runtime = codec._fields(data, {'python', 'architecture', 'dependencies', 'harness_sha256'}, 'runtime')
    if not re.fullmatch(r'3\.13\.[0-9]+', codec._text(runtime['python'], 'runtime.python')) or runtime['architecture'] != '64bit':
        raise ValueError('Runtime requires Python 3.13 x64 evidence')
    dependencies = runtime['dependencies']
    if not isinstance(dependencies, dict) or not dependencies:
        raise ValueError('Runtime requires dependency versions')
    for name, version in dependencies.items():
        codec._text(name, 'dependency name')
        codec._text(version, 'dependency version')
    codec._hash(runtime['harness_sha256'], 'runtime.harness_sha256')
    return runtime


def _tools(values: object) -> None:
    if not isinstance(values, list):
        raise ValueError('Stage tools must be a list')
    if len(values) > MAX_PATHS:
        raise ValueError('Tool count exceeds resource limit')
    identifiers = []
    hits = 0
    vertices = 0
    for value in values:
        tool = codec._fields(value, {'id', 'diameter_mm', 'drills', 'slots'}, 'tool')
        if not isinstance(tool['drills'], list) or not isinstance(tool['slots'], list):
            raise ValueError('Tool drills and slots require ordered lists')
        vertices += len(tool['drills']) + 2 * len(tool['slots'])
        if vertices > MAX_VERTICES:
            raise ValueError('Drill/slot vertex count exceeds resource limit')
        if any(not isinstance(slot, list) or len(slot) != 2 for slot in tool['slots']):
            raise ValueError('Slot requires exactly two XY endpoints')
        ReferenceTool(tool['id'], tool['diameter_mm'], tuple(tool['drills']),
                      tuple(tuple(slot) for slot in tool['slots']))
        identifiers.append(tool['id'])
        hits += len(tool['drills']) + len(tool['slots'])
    if len(identifiers) != len(set(identifiers)):
        raise ValueError('Duplicate Excellon tool ID')
    if values and hits == 0:
        raise ValueError('Successful Excellon stage requires actual drill/slot hits')


def _stage(data: object) -> dict:
    stage = codec._fields(data, STAGE_FIELDS, 'stage')
    codec._relative(stage['input_path'], 'stage.input_path')
    if codec._text(stage['stage'], 'stage.stage') not in {'gerber', 'excellon', 'isolation', 'cnc'}:
        raise ValueError('Unsupported requested stage')
    if (codec._text(stage['status'], 'stage.status') not in {'ok', 'error', 'unsupported'} or stage['units'] != 'mm'
            or stage['source_units'] not in ('MM', 'IN', None)):
        raise ValueError('Invalid stage status or declared units')
    for field in ('geometry_wkb', 'paths', 'tools'):
        if not isinstance(stage[field], list):
            raise ValueError(f'stage.{field} requires an ordered list')
    if stage['status'] != 'ok':
        codec._text(stage['diagnostic'], 'stage.diagnostic')
        if any(stage[field] for field in ('geometry_wkb', 'paths', 'tools')) or stage['gcode'] is not None:
            raise ValueError('Failed/unavailable stage cannot retain fabricated outputs')
        return stage
    if stage['diagnostic'] is not None or stage['source_units'] is None:
        raise ValueError('Successful stage needs source units and no failure diagnostic')
    for geometry in stage['geometry_wkb']:
        _decode(geometry)
    if len(stage['paths']) > MAX_PATHS:
        raise ValueError('Stage path count exceeds limit')
    vertices = 0
    for value in stage['paths']:
        path = codec._fields(value, {'kind', 'wkb_hex'}, 'path')
        if not isinstance(path['kind'], list):
            raise ValueError('Path kind requires an ordered list')
        ReferencePath(tuple(path['kind']), path['wkb_hex'])
        vertices += len(_decode(path['wkb_hex']).coords)
        if vertices > MAX_VERTICES:
            raise ValueError('Stage vertex count exceeds limit')
    _tools(stage['tools'])
    if stage['stage'] == 'excellon':
        if not stage['tools'] or not stage['geometry_wkb'] or stage['paths'] or stage['gcode'] is not None:
            raise ValueError('Excellon success requires geometry/tools and no CNC output')
    elif stage['stage'] == 'cnc':
        if not stage['paths'] or stage['tools']:
            raise ValueError('CNC success requires actual ordered paths, not drill tools')
        codec._text(stage['gcode'], 'cnc.gcode')
    elif not stage['geometry_wkb'] or stage['paths'] or stage['tools'] or stage['gcode'] is not None:
        raise ValueError('Parser/isolation success requires actual geometry only')
    return stage


def _linkage(data: dict, manifest: dict | None, config: dict | None, expected_board: str | None) -> None:
    if expected_board is not None and data['board_id'] != expected_board:
        raise ValueError('Capture board differs from requested board')
    requested = data['configuration']['requested']
    if config is not None and codec.config_sha256(codec.validate_config(config)) != data['configuration']['sha256']:
        raise ValueError('Capture configuration differs from supplied config')
    if manifest is None:
        return
    manifest = codec.validate_manifest(manifest)
    boards = [board for board in manifest['boards'] if board['id'] == data['board_id']]
    if len(boards) != 1:
        raise ValueError('Capture board is not admitted by manifest')
    board = boards[0]
    expected = {record['path']: record['sha256'] for record in board['files']}
    actual = {record['path']: record['sha256'] for record in data['inputs']}
    if expected != actual:
        raise ValueError('Capture input hashes differ from admitted board')
    required = {(record['path'], stage) for record in board['files']
                for stage in requested['stages'][record['role']]}
    actual_stages = {(stage['input_path'], stage['stage']) for stage in data['stages']}
    if actual_stages != required:
        raise ValueError('Capture requested stages are missing or unexpected')


def validate_capture(data: object, *, manifest: dict | None = None, config: dict | None = None,
                     expected_engine: str | None = None, expected_board: str | None = None) -> dict:
    data = codec._envelope(data, 'mikrocam.reference-capture', CAPTURE_FIELDS)
    codec._text(data['board_id'], 'capture.board_id')
    if codec._text(data['engine'], 'capture.engine') not in {'legacy8994', 'evo', 'current'} or (expected_engine is not None and data['engine'] != expected_engine):
        raise ValueError('Capture engine is invalid or differs from requested engine')
    source = codec._fields(data['source'], {'revision', 'files'}, 'source')
    codec._hash(source['revision'], 'source.revision', 40)
    _hashed_files(source['files'], 'source.files')
    if data['engine'] in codec.BASELINE_REVISIONS and source['revision'] != codec.BASELINE_REVISIONS[data['engine']]:
        raise ValueError('Baseline source revision is not the pinned unchanged baseline')
    _runtime(data['runtime'])
    _hashed_files(data['inputs'], 'inputs')
    configuration = codec._fields(data['configuration'], {'sha256', 'requested', 'effective_optimization'}, 'configuration')
    codec._hash(configuration['sha256'], 'configuration.sha256')
    requested = codec.validate_config(configuration['requested'])
    if configuration['sha256'] != codec.config_sha256(requested):
        raise ValueError('Configuration SHA256 mismatch')
    optimization = 'RTree' if data['engine'] == 'legacy8994' else 'N'
    if configuration['effective_optimization'] != optimization:
        raise ValueError('Effective optimization does not match unchanged engine identity')
    if not isinstance(data['stages'], list) or not data['stages']:
        raise ValueError('Capture requires actual requested stage records')
    keys = []
    paths = {record['path'] for record in data['inputs']}
    for stage in data['stages']:
        stage = _stage(stage)
        if stage['input_path'] not in paths:
            raise ValueError('Stage input is absent from captured evidence')
        keys.append((stage['input_path'], stage['stage']))
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate captured stage')
    _linkage(data, manifest, config, expected_board)
    return data


def load_capture(path: str | Path, **kwargs) -> dict:
    try:
        with gzip.open(path, 'rb') as stream:
            data = stream.read(codec.MAX_JSON_BYTES + 1)
        if len(data) > codec.MAX_JSON_BYTES:
            raise ValueError('Decoded gzip JSON exceeds size limit')
        return codec.capture_from_json(data.decode('utf-8'), **kwargs)
    except (OSError, EOFError, UnicodeError, zlib.error) as error:
        raise ValueError(f'Invalid compressed capture {path}: {error}') from error


def write_capture(path: str | Path, data: dict) -> None:
    text = codec.capture_to_json(data).encode('utf-8')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f'.{path.name}.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as archive:
                archive.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
