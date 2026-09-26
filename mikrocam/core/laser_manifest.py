"""Strict deterministic schema-one metadata for geometry-only transfer packages."""
import math

from .laser_job import LaserPass, LaserRecipe, _name
from .laser_json import PASS_FIELDS, _dump, _envelope, _fields, _load
from .laser_paths import validate_interlace_n
from .placement import _finite_real


MAX_PASSES = 1_000
MANIFEST_FIELDS = {'kind', 'schema_version', 'format', 'units', 'job_name', 'bounds_mm',
                   'interlace_n', 'coordinate_mapping', 'recipe_file', 'passes'}
ENTRY_FIELDS = {'index', 'name', 'file', 'sha256', 'path_count', 'settings'}


def _pass_entry(value: object, index: int, format: str) -> LaserPass:
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
    settings = LaserPass(**_fields(data['settings'], PASS_FIELDS, 'manifest pass settings'))
    if data['name'] != settings.name:
        raise ValueError('Manifest pass name must equal its settings name')
    return settings


def _validate_manifest(value: object) -> dict:
    data = _envelope(value, MANIFEST_FIELDS, 'mikrocam.laser-export', 'manifest')
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
    settings = tuple(_pass_entry(item, index, data['format'])
                     for index, item in enumerate(entries, 1))
    LaserRecipe(data['job_name'], settings)
    return data


def manifest_to_json(data: dict) -> str:
    """Validate every transfer field and emit stable JSON without implicit settings."""
    return _dump(_validate_manifest(data))


def manifest_from_json(text: str) -> dict:
    """Reject unknown, duplicate, incomplete, future or nonfinite transfer metadata."""
    return _validate_manifest(_load(text, 'manifest'))
