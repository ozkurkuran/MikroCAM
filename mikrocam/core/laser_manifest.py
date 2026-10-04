"""Strict deterministic versioned metadata for geometry transfer packages.

Schema 1 has no device profile, schema 2 a device profile, and schema 3 records island
tiling with an optional (nullable) device profile. Older manifests read unchanged and
``upgrade_manifest`` migrates them to schema 3 with ``island: null``.
"""
import json
import math

from .laser_job import LaserPass, LaserRecipe, _name
from .laser_json import PASS_FIELDS, DEVICE_PASS_FIELDS, device_from_data, _dump, _envelope, _fields, _load
from .laser_paths import IslandSettings, validate_interlace_n
from .placement import _finite_real


MAX_PASSES = 1_000
MANIFEST_FIELDS = {'kind', 'schema_version', 'format', 'units', 'job_name', 'bounds_mm',
                   'interlace_n', 'coordinate_mapping', 'recipe_file', 'passes'}
ENTRY_FIELDS = {'index', 'name', 'file', 'sha256', 'path_count', 'settings'}
ISLAND_FIELDS = ('tile_size_mm', 'overlap_mm', 'angle_step_deg', 'order')
MANIFEST_VERSIONS = (1, 2, 3)


def island_to_data(island: IslandSettings | None) -> dict | None:
    """Encode explicit island tiling settings, or None when tiling is off."""
    if island is None:
        return None
    if not isinstance(island, IslandSettings):
        raise ValueError('Expected IslandSettings or None')
    return {field: getattr(island, field) for field in ISLAND_FIELDS}


def island_from_data(value: object) -> IslandSettings | None:
    """Decode strict island settings without substituting defaults."""
    if value is None:
        return None
    data = _fields(value, set(ISLAND_FIELDS), 'manifest.island')
    return IslandSettings(**data)


def _pass_entry(value: object, index: int, format: str, profiled: bool = False) -> LaserPass:
    data = _fields(value, ENTRY_FIELDS, f'manifest.passes[{index - 1}]')
    if type(data['index']) is not int or data['index'] != index:
        raise ValueError('Manifest pass index must follow consecutive 1-based order')
    if data['file'] != f'pass-{index:03d}.{format}':
        raise ValueError('Manifest pass file must match its ordinal index and format')
    digest = data['sha256']
    if (not isinstance(digest, str) or len(digest) != 64
            or any(character not in '0123456789abcdef' for character in digest)):
        raise ValueError('Manifest sha256 must contain 64 lowercase hex characters')
    if type(data['path_count']) is not int or data['path_count'] <= 0:
        raise ValueError('Manifest path_count must be a positive integer')
    settings = LaserPass(**_fields(data['settings'], DEVICE_PASS_FIELDS if profiled else PASS_FIELDS, 'manifest pass settings'))
    if data['name'] != settings.name:
        raise ValueError('Manifest pass name must equal its settings name')
    return settings


def _version(value: object) -> int | None:
    version = value.get('schema_version') if isinstance(value, dict) else None
    return version if type(version) is int else None


def _validate_manifest(value: object) -> dict:
    version = _version(value)
    extra = {2: {'device'}, 3: {'device', 'island'}}.get(version, set())
    data = _envelope(value, MANIFEST_FIELDS | extra, 'mikrocam.laser-export', 'manifest', MANIFEST_VERSIONS)
    device = None
    if version == 2 or (version == 3 and data['device'] is not None):
        device = device_from_data(data['device'])
    if version == 3:
        island_from_data(data['island'])
    profiled = device is not None
    if data['format'] not in ('svg', 'dxf'):
        raise ValueError('Manifest format must be svg or dxf')
    expected_mapping = 'svg-local-y-down' if data['format'] == 'svg' else 'placed-xy'
    if data['coordinate_mapping'] != expected_mapping:
        raise ValueError('Manifest coordinate mapping must match its format')
    if data['units'] != 'mm' or data['recipe_file'] != 'recipe.json':
        raise ValueError('Manifest units must be mm and recipe_file must be recipe.json')
    _name(data['job_name'], 'manifest job')
    validate_interlace_n(data['interlace_n'])
    bounds = data['bounds_mm']
    if not isinstance(bounds, list) or len(bounds) != 4:
        raise ValueError('Manifest bounds_mm must be four finite numbers')
    xmin, ymin, xmax, ymax = (_finite_real(value, 'bounds_mm') for value in bounds)
    if (xmin > xmax or ymin > ymax
            or not math.isfinite(xmax - xmin) or not math.isfinite(ymax - ymin)):
        raise ValueError('Manifest bounds must have ordered finite extents')
    entries = data['passes']
    if not isinstance(entries, list) or not entries or len(entries) > MAX_PASSES:
        raise ValueError(f'Manifest passes must be a nonempty array of at most {MAX_PASSES} passes')
    settings = tuple(_pass_entry(item, index, data['format'], profiled)
                     for index, item in enumerate(entries, 1))
    LaserRecipe(data['job_name'], settings, device)
    return data


def manifest_to_json(data: dict) -> str:
    """Validate every transfer field and emit stable JSON without implicit settings."""
    return _dump(_validate_manifest(data))


def manifest_from_json(text: str) -> dict:
    """Reject unknown, duplicate, incomplete, future or nonfinite transfer metadata."""
    return _validate_manifest(_load(text, 'manifest'))


def manifest_island(data: dict) -> IslandSettings | None:
    """Return the island tiling of a validated manifest; schemas 1 and 2 have none."""
    data = _validate_manifest(data)
    return island_from_data(data['island']) if data['schema_version'] == 3 else None


def upgrade_manifest(data: dict) -> dict:
    """Migrate a validated schema 1/2 manifest to schema 3 without changing any value."""
    upgraded = json.loads(_dump(_validate_manifest(data)))
    if upgraded['schema_version'] != 3:
        upgraded.setdefault('device', None)
        upgraded.update(schema_version=3, island=None)
    return _validate_manifest(upgraded)
