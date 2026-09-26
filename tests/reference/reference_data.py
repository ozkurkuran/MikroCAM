"""Strict developer reference codecs and unchanged corpus/configuration validation."""
import hashlib
import json
import math
from numbers import Real
from pathlib import Path, PurePosixPath
import re
import zipfile


MAX_JSON_BYTES = 512 * 1024 * 1024
BASELINE_REVISIONS = {'legacy8994': '6ba378bca139aa306f8c94f09461a98f95d3c75b',
                      'evo': 'd0a86cf4f1ac41a206b20f316d4a29f28a93bbff'}
ROLES = {'copper', 'drill', 'outline', 'drill-map', 'native', 'notice', 'archive'}
REQUIRED_ORIGINS = {'KiCad', 'EasyEDA', 'Altium', 'Eagle', 'Proteus'}
STAGES = {'copper': ['gerber', 'isolation', 'cnc'], 'drill': ['excellon'],
          'outline': ['gerber'], 'drill-map': [], 'native': [], 'notice': [], 'archive': []}


def _fields(value: object, expected: set[str], context: str) -> dict:
    if not isinstance(value, dict) or value.keys() != expected:
        raise ValueError(f'{context} requires exact fields {sorted(expected)}')
    return value


def _text(value: object, context: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError(f'{context} must be a nonempty string')
    return value


def _hash(value: object, context: str, length: int = 64) -> str:
    if not isinstance(value, str) or not re.fullmatch(f'[0-9a-f]{{{length}}}', value):
        raise ValueError(f'{context} requires a lowercase SHA{length * 4} hash')
    return value


def _relative(value: object, context: str) -> str:
    value = _text(value, context)
    if (value.startswith('/') or '\\' in value or ':' in value
            or any(part in {'', '.', '..'} for part in value.split('/'))):
        raise ValueError(f'{context} must be a safe relative path')
    return value


def _envelope(data: object, kind: str, fields: set[str]) -> dict:
    data = _fields(data, fields | {'kind', 'schema_version'}, kind)
    if data['kind'] != kind or type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError(f'{kind} requires kind and schema_version 1')
    return data


def _unique(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key {key}')
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ValueError(f'Nonfinite JSON value {value}')


def _from_json(text: str) -> dict:
    if not isinstance(text, str) or len(text) > MAX_JSON_BYTES or len(text.encode('utf-8')) > MAX_JSON_BYTES:
        raise ValueError('JSON text exceeds size limit or is not text')
    try:
        return json.loads(text, object_pairs_hook=_unique, parse_constant=_nonfinite)
    except (ValueError, RecursionError) as error:
        raise ValueError(f'Invalid reference JSON: {error}') from error


def canonical_json(data: object) -> str:
    try:
        text = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError(f'Invalid reference JSON: {error}') from error
    if len(text.encode('utf-8')) > MAX_JSON_BYTES:
        raise ValueError('JSON text exceeds size limit')
    return text


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _resolved(root: Path, relative: str) -> Path:
    path = (root / PurePosixPath(relative)).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'Corpus path escapes outside root: {relative}')
    if not path.is_file():
        raise ValueError(f'Corpus file is missing: {relative}')
    return path


def _file(record: object, context: str) -> dict:
    data = _fields(record, {'path', 'source_path', 'sha256', 'source_sha256', 'role'}, context)
    _relative(data['path'], f'{context}.path')
    source = _text(data['source_path'], f'{context}.source_path')
    if source.count('!') > 1:
        raise ValueError(f'{context} has invalid archive member syntax')
    for part in source.split('!'):
        _relative(part, f'{context}.source_path')
    _hash(data['sha256'], context)
    _hash(data['source_sha256'], context)
    if data['sha256'] != data['source_sha256'] or _text(data['role'], context) not in ROLES:
        raise ValueError(f'{context} requires unchanged source SHA and supported role')
    return data


def _verify_files(board: dict, root: Path) -> None:
    archives = {record['source_path']: record for record in board['files'] if record['role'] == 'archive'}
    for record in board['files']:
        path = _resolved(root, record['path'])
        if sha256_file(path) != record['sha256']:
            raise ValueError(f'Corpus SHA256 hash mismatch: {record["path"]}')
        if '!' not in record['source_path']:
            continue
        archive_source, member = record['source_path'].split('!')
        if archive_source not in archives:
            raise ValueError(f'Original archive is missing for member {record["path"]}')
        try:
            with zipfile.ZipFile(_resolved(root, archives[archive_source]['path'])) as archive:
                entries = [entry for entry in archive.infolist() if entry.filename == member]
                if len(entries) != 1 or entries[0].file_size != path.stat().st_size:
                    raise ValueError(f'Archive member is missing/duplicate/changed: {member}')
                digest = hashlib.sha256()
                with archive.open(entries[0]) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(chunk)
                if digest.hexdigest() != record['source_sha256']:
                    raise ValueError(f'Archive member SHA256 mismatch: {member}')
        except (OSError, zipfile.BadZipFile, RuntimeError) as error:
            raise ValueError(f'Invalid original archive: {error}') from error


def _board(data: object) -> dict:
    board = _fields(data, {'id', 'name', 'origin', 'design_identity', 'source', 'license', 'files'}, 'board')
    if not isinstance(board['id'], str) or not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', board['id']):
        raise ValueError('board.id requires a stable slug')
    for field in ('name', 'origin', 'design_identity'):
        _text(board[field], f'board.{field}')
    source = _fields(board['source'], {'url', 'revision', 'origin_evidence'}, 'board.source')
    if not _text(source['url'], 'source.url').startswith('https://'):
        raise ValueError('Source URL must be immutable HTTPS evidence')
    _hash(source['revision'], 'source.revision', 40)
    _text(source['origin_evidence'], 'source.origin_evidence')
    license = _fields(board['license'], {'identifier', 'evidence', 'notices'}, 'board.license')
    if _text(license['identifier'], 'license.identifier') not in {'MIT', 'BSD-3-Clause', 'CC-BY-3.0', 'CERN-OHL-W-2.0'}:
        raise ValueError('License identifier requires audited redistribution evidence')
    _text(license['evidence'], 'license.evidence')
    if not isinstance(board['files'], list) or not board['files']:
        raise ValueError('board.files must be nonempty')
    records = [_file(record, f'{board["id"]}.file') for record in board['files']]
    paths = [record['path'] for record in records]
    if len(paths) != len(set(paths)) or any(not path.startswith(board['id'] + '/') for path in paths):
        raise ValueError('Board file paths must be unique and inside its board directory')
    if not any(record['role'] == 'copper' for record in records):
        raise ValueError('Board requires authentic copper input')
    notices = license['notices']
    if (not isinstance(notices, list) or not notices or any(not isinstance(value, str) for value in notices)
            or len(notices) != len(set(notices))):
        raise ValueError('License notices must be a nonempty unique list')
    notice_paths = {record['path'] for record in records if record['role'] == 'notice'}
    if not set(notices) <= notice_paths:
        raise ValueError('License notice is not a retained original notice file')
    return board


def validate_manifest(data: object, root: str | Path | None = None) -> dict:
    data = _envelope(data, 'mikrocam.reference-dataset', {'boards'})
    if not isinstance(data['boards'], list) or not 10 <= len(data['boards']) <= 20:
        raise ValueError('Corpus requires 10–20 distinct boards')
    boards = [_board(board) for board in data['boards']]
    for field in ('id', 'design_identity'):
        if len({board[field] for board in boards}) != len(boards):
            raise ValueError(f'Duplicate board {field}')
    if not REQUIRED_ORIGINS <= {board['origin'] for board in boards}:
        raise ValueError('Corpus is missing a required CAD origin: ' + ', '.join(sorted(REQUIRED_ORIGINS)))
    if root is not None:
        for board in boards:
            _verify_files(board, Path(root))
    return data


def manifest_from_json(text: str, root: str | Path | None = None) -> dict:
    return validate_manifest(_from_json(text), root=root)


def manifest_to_json(data: dict) -> str:
    return canonical_json(validate_manifest(data))


def load_manifest(path: str | Path) -> dict:
    path = Path(path)
    return manifest_from_json(path.read_text(encoding='utf-8'), root=path.parent)


GERBER_FIELDS = set('units gerber_def_units gerber_def_zeros gerber_circle_steps gerber_simp_tolerance '
                    'gerber_simplification gerber_buffering gerber_extra_buffering gerber_clean_apertures '
                    'gerber_use_buffer_for_union global_tolerance'.split())
EXCELLON_FIELDS = set('zeros excellon_format_upper_mm excellon_format_lower_mm excellon_format_upper_in '
                     'excellon_format_lower_in excellon_units circle_steps'.split())
CNC_FIELDS = set('append tooldia offset tolerance z_cut z_move feedrate feedrate_z feedrate_rapid spindlespeed '
                 'spindle_direction dwell dwelltime multidepth depthpercut toolchange toolchangez toolchangexy '
                 'extracut extracut_length startz endz endxy pp_geometry_name tool_no is_first coords_decimals '
                 'fr_decimals steps_per_circle coords_type'.split())
BOOL_FIELDS = set('gerber_simplification gerber_clean_apertures gerber_use_buffer_for_union append dwell '
                  'multidepth toolchange extracut is_first'.split())
INT_FIELDS = set('gerber_circle_steps excellon_format_upper_mm excellon_format_lower_mm excellon_format_upper_in '
                 'excellon_format_lower_in circle_steps tool_no coords_decimals fr_decimals steps_per_circle'.split())
STRING_CHOICES = {'units': {'MM', 'IN'}, 'gerber_def_units': {'MM', 'IN'}, 'gerber_def_zeros': {'L', 'T'},
                  'gerber_buffering': {'full', 'no'}, 'zeros': {'L', 'T'}, 'excellon_units': {'MM', 'IN'},
                  'spindle_direction': {'CW', 'CCW'}, 'coords_type': {'G90', 'G91'},
                  'toolchangexy': None, 'endxy': None, 'pp_geometry_name': None}
POSITIVE_FIELDS = {'tooldia', 'feedrate', 'feedrate_z', 'feedrate_rapid', 'depthpercut'}
NONNEGATIVE_FIELDS = {'gerber_simp_tolerance', 'gerber_extra_buffering', 'global_tolerance',
                      'tolerance', 'spindlespeed', 'dwelltime', 'extracut_length', 'offset_mm'}


def _parameters(data: object, fields: set[str], context: str) -> dict:
    data = _fields(data, fields, context)
    for field, value in data.items():
        if field in BOOL_FIELDS:
            if type(value) is not bool:
                raise ValueError(f'{context}.{field} requires bool')
        elif field in INT_FIELDS:
            minimum = 0 if field in {'coords_decimals', 'fr_decimals'} else 1
            if type(value) is not int or not minimum <= value <= 1_000_000:
                raise ValueError(f'{context}.{field} requires a bounded integer')
        elif field in STRING_CHOICES:
            _text(value, f'{context}.{field}', empty=field == 'toolchangexy')
            choices = STRING_CHOICES[field]
            if choices is not None and value not in choices:
                raise ValueError(f'{context}.{field} is unsupported')
        else:
            if isinstance(value, bool) or not isinstance(value, Real):
                raise ValueError(f'{context}.{field} requires a finite number')
            try:
                finite = math.isfinite(float(value))
            except OverflowError:
                finite = False
            if (not finite or (field in POSITIVE_FIELDS and value <= 0)
                    or (field in NONNEGATIVE_FIELDS and value < 0)):
                raise ValueError(f'{context}.{field} is outside its finite range')
    return data


def validate_config(data: object) -> dict:
    data = _envelope(data, 'mikrocam.reference-config', {'parameters', 'stages'})
    parameters = _fields(data['parameters'], {'parser', 'isolation', 'cnc'}, 'parameters')
    parser = _fields(parameters['parser'], {'gerber', 'excellon'}, 'parser')
    _parameters(parser['gerber'], GERBER_FIELDS, 'gerber')
    _parameters(parser['excellon'], EXCELLON_FIELDS, 'excellon')
    _parameters(parameters['isolation'], {'offset_mm'}, 'isolation')
    _parameters(parameters['cnc'], CNC_FIELDS, 'cnc')
    if _fields(data['stages'], ROLES, 'stages') != STAGES:
        raise ValueError('Requested stages must be the explicit supported role mapping')
    return data


def config_from_json(text: str) -> dict:
    return validate_config(_from_json(text))


def config_to_json(data: dict) -> str:
    return canonical_json(validate_config(data))


def config_sha256(data: dict) -> str:
    return hashlib.sha256(config_to_json(data).encode('utf-8')).hexdigest()


def load_config(path: str | Path) -> dict:
    return config_from_json(Path(path).read_text(encoding='utf-8'))


def validate_capture(data: object, **kwargs) -> dict:
    from .reference_capture_data import validate_capture as validate
    return validate(data, **kwargs)


def capture_from_json(text: str, **kwargs) -> dict:
    return validate_capture(_from_json(text), **kwargs)


def capture_to_json(data: dict) -> str:
    return canonical_json(validate_capture(data))


def load_capture(path: str | Path, **kwargs) -> dict:
    from .reference_capture_data import load_capture as load
    return load(path, **kwargs)


def write_capture(path: str | Path, data: dict) -> None:
    from .reference_capture_data import write_capture as write
    write(path, data)
