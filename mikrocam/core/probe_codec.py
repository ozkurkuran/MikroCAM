"""Strict deterministic schema-one millimetre probe map JSON."""
import json

from mikrocam.core.probe_map import ProbeGrid, ProbeMap

MAX_MAP_BYTES = 1048576
_FIELDS = {'schema', 'units', 'grid', 'heights_mm', 'g54_offset_mm', 'outcome', 'origin'}


def _fields(value: object, fields: set[str]) -> dict:
    if type(value) is not dict or set(value) != fields:
        raise ValueError('Probe JSON requires exactly the declared schema fields')
    return value


def _array(value: object, limit: int) -> tuple:
    if type(value) is not list or len(value) > limit:
        raise ValueError('Probe JSON requires a bounded array')
    return tuple(value)


def map_to_dict(value: ProbeMap) -> dict:
    """Produce fresh mutable JSON containers from an immutable measured map."""
    if type(value) is not ProbeMap:
        raise ValueError('Probe serialization requires an exact ProbeMap')
    return {'schema': 1, 'units': 'mm',
            'grid': {'x_mm': list(value.grid.x_mm), 'y_mm': list(value.grid.y_mm)},
            'heights_mm': list(value.heights_mm), 'g54_offset_mm': list(value.g54_offset_mm),
            'outcome': value.outcome, 'origin': value.origin}


def map_from_dict(value: object) -> ProbeMap:
    """Validate exact schema and numeric records without inferred defaults."""
    data = _fields(value, _FIELDS)
    if (type(data['schema']) is not int or data['schema'] != 1
            or type(data['units']) is not str or data['units'] != 'mm'):
        raise ValueError('Probe map requires schema1 and units mm')
    grid = _fields(data['grid'], {'x_mm', 'y_mm'})
    return ProbeMap(ProbeGrid(_array(grid['x_mm'], 64), _array(grid['y_mm'], 64)),
                    _array(data['heights_mm'], 1024), _array(data['g54_offset_mm'], 3),
                    data['outcome'], data['origin'])


def _unique(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate probe JSON key: {key}')
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ValueError(f'Nonfinite probe JSON number: {value}')


def _size(text: str) -> None:
    if type(text) is not str or not text or len(text) > MAX_MAP_BYTES:
        raise ValueError('Probe JSON requires bounded nonempty text')
    try:
        valid = len(text.encode('utf-8')) <= MAX_MAP_BYTES
    except UnicodeError as error:
        raise ValueError('Probe JSON requires strict UTF8 text') from error
    if not valid:
        raise ValueError('Probe JSON exceeds 1MiB')


def dumps_map(value: ProbeMap) -> str:
    """Serialize deterministically, retaining floating-point measurement precision."""
    text = json.dumps(map_to_dict(value), ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(',', ':'))
    _size(text)
    return text


def loads_map(text: str) -> ProbeMap:
    """Reject duplicate keys, nonfinite constants and malformed/oversized JSON."""
    _size(text)
    try:
        return map_from_dict(json.loads(text, object_pairs_hook=_unique, parse_constant=_constant))
    except (ValueError, RecursionError, OverflowError) as error:
        raise ValueError(f'Invalid probe map JSON: {error}') from error
