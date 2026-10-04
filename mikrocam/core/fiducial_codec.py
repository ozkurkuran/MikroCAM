"""Strict deterministic `mikrocam.fiducial-set` JSON, schema version 1 (millimetres).

Schema 1 is the first version, so no migration step exists yet. The committed v1 fixture
test is the gate: a future schema change must add a migration that keeps it opening.
"""
from dataclasses import dataclass
import json

from .fiducial import MAX_PAIRS, AlignmentPolicy, FiducialPair


KIND = 'mikrocam.fiducial-set'
SCHEMA_VERSION = 1
MAX_BYTES = 1024 * 1024
_FIELDS = {'kind', 'schema_version', 'units', 'name', 'method', 'policy', 'pairs'}
_POLICY = {'max_residual_mm', 'max_scale_deviation', 'min_separation_mm'}
_PAIR = {'name', 'design_mm', 'machine_mm', 'enabled'}


@dataclass(frozen=True)
class FiducialSet:
    """A named policy and ordered pairs; measured values are valid for one fixture setup only."""
    name: str
    policy: AlignmentPolicy
    pairs: tuple[FiducialPair, ...]

    def __post_init__(self) -> None:
        if type(self.name) is not str or not 1 <= len(self.name) <= 256 or not self.name.isprintable():
            raise ValueError('Fiducial set name requires 1..256 printable characters')
        if type(self.policy) is not AlignmentPolicy:
            raise ValueError('Fiducial set requires an AlignmentPolicy')
        if (type(self.pairs) is not tuple or not 1 <= len(self.pairs) <= MAX_PAIRS
                or any(type(pair) is not FiducialPair for pair in self.pairs)):
            raise ValueError(f'Fiducial set requires 1..{MAX_PAIRS} FiducialPair values')
        if len({pair.name for pair in self.pairs}) != len(self.pairs):
            raise ValueError('Fiducial names must be unique')


def dumps_fiducial_set(value: FiducialSet) -> str:
    if type(value) is not FiducialSet:
        raise ValueError('Expected FiducialSet')
    policy = value.policy
    data = {'kind': KIND, 'schema_version': SCHEMA_VERSION, 'units': 'mm', 'name': value.name,
            'method': policy.method,
            'policy': {'max_residual_mm': policy.max_residual_mm,
                       'max_scale_deviation': policy.max_scale_deviation,
                       'min_separation_mm': policy.min_separation_mm},
            'pairs': [{'name': pair.name, 'design_mm': list(pair.design_mm),
                       'machine_mm': None if pair.machine_mm is None else list(pair.machine_mm),
                       'enabled': pair.enabled} for pair in value.pairs]}
    return json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + '\n'


def _fields(value: object, fields: set[str], label: str) -> dict:
    if type(value) is not dict or set(value) != fields:
        raise ValueError(f'{label} requires exactly the declared schema fields')
    return value


def _xy(value: object, label: str) -> tuple:
    if type(value) is not list or len(value) != 2 or any(type(item) not in (int, float) for item in value):
        raise ValueError(f'{label} must be a two-number array')
    return tuple(value)


def _unique(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, item in pairs:
        if key in result:
            raise ValueError(f'Duplicate fiducial JSON key: {key}')
        result[key] = item
    return result


def _constant(value: str) -> None:
    raise ValueError(f'Nonfinite fiducial JSON number: {value}')


def _load(text: str) -> object:
    if type(text) is not str or not text or len(text.encode('utf-8')) > MAX_BYTES:
        raise ValueError('Fiducial set requires bounded nonempty JSON text')
    try:
        return json.loads(text, object_pairs_hook=_unique, parse_constant=_constant)
    except json.JSONDecodeError as error:
        raise ValueError(f'Invalid fiducial set JSON: {error.msg}') from error


def _version_one(data: dict) -> FiducialSet:
    if data['units'] != 'mm':
        raise ValueError('Fiducial set units must be mm')
    policy_data = _fields(data['policy'], _POLICY, 'policy')
    policy = AlignmentPolicy(data['method'], **policy_data)
    if type(data['pairs']) is not list:
        raise ValueError('pairs must be an array')
    pairs = []
    for item in data['pairs']:
        record = _fields(item, _PAIR, 'pair')
        machine = None if record['machine_mm'] is None else _xy(record['machine_mm'], 'machine_mm')
        pairs.append(FiducialPair(record['name'], _xy(record['design_mm'], 'design_mm'), machine,
                                  record['enabled']))
    return FiducialSet(data['name'], policy, tuple(pairs))


def loads_fiducial_set(text: str) -> FiducialSet:
    """Read a complete versioned document; unknown kinds, versions and fields are refused."""
    data = _fields(_load(text), _FIELDS, 'fiducial set')
    if data['kind'] != KIND:
        raise ValueError(f'Expected {KIND}')
    version = data['schema_version']
    if type(version) is not int or version != SCHEMA_VERSION:
        raise ValueError(f'Unsupported fiducial set schema_version: {version!r}')
    return _version_one(data)
