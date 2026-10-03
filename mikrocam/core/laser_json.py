"""Strict deterministic versioned JSON text for laser recipes and jobs."""
import json
from dataclasses import asdict

from .laser_job import LaserJob, LaserPass, LaserRecipe, PlanarRegion
from .placement import Placement
from .laser_device import LaserDeviceProfile, PARAMETER_FIELDS


PASS_FIELDS = {'name', 'power_percent', 'speed_mm_s', 'frequency_khz', 'pulse_width_ns'}
DEVICE_PASS_FIELDS = PARAMETER_FIELDS | {'name'}
RECIPE_FIELDS = {'kind', 'schema_version', 'name', 'passes'}
JOB_FIELDS = {'kind', 'schema_version', 'units', 'name', 'region_wkb_hex', 'recipe', 'placement'}
PLACEMENT_FIELDS = {'origin', 'translation', 'rotation_deg', 'mirror_x'}


def _fields(value: object, expected: set[str], context: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f'{context} must be an object')
    missing, unknown = expected - value.keys(), value.keys() - expected
    if missing or unknown:
        raise ValueError(f'{context}: missing fields {sorted(missing)}; unknown fields {sorted(unknown)}')
    return value


def _envelope(value: object, expected: set[str], kind: str, context: str,
              versions: tuple[int, ...] = (1,)) -> dict:
    data = _fields(value, expected, context)
    if data['kind'] != kind:
        raise ValueError(f'{context}.kind must be {kind!r}')
    if type(data['schema_version']) is not int or data['schema_version'] not in versions:
        raise ValueError(f'{context}.schema_version is unsupported: {data["schema_version"]!r}')
    return data


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError(f'duplicate JSON key: {key}')
        data[key] = value
    return data


def _reject_constant(value: str) -> None:
    raise ValueError(f'Non-finite JSON value is unsupported: {value}')


def _load(text: str, context: str) -> object:
    if not isinstance(text, str):
        raise ValueError(f'{context} JSON must be text')
    try:
        return json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except ValueError as error:
        raise ValueError(f'{context} JSON: {error}') from error


def _dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _recipe_data(recipe: LaserRecipe) -> dict:
    if not isinstance(recipe, LaserRecipe):
        raise ValueError('Expected LaserRecipe')
    profiled = recipe.device is not None
    data = {'kind': 'mikrocam.laser-recipe', 'schema_version': 2 if profiled else 1, 'name': recipe.name,
            'passes': [{field: getattr(value, field) for field in (DEVICE_PASS_FIELDS if profiled else PASS_FIELDS)}
                       for value in recipe.passes]}
    if profiled: data['device'] = asdict(recipe.device)
    return data


def device_from_data(value: object) -> LaserDeviceProfile:
    """Decode an explicit immutable profile without guessing a model or limits."""
    data = dict(_fields(value, set(LaserDeviceProfile.__dataclass_fields__), 'device'))
    for field in ('frequency_range_khz', 'pulse_width_range_ns', 'pulse_widths_ns', 'pwm_frequency_range_khz'):
        if data[field] is None and field != 'pulse_widths_ns': continue
        if type(data[field]) is not list: raise ValueError(f'device.{field} must be an array')
        data[field] = tuple(data[field])
    return LaserDeviceProfile(**data)


def _recipe_from_data(value: object) -> LaserRecipe:
    profiled = isinstance(value, dict) and type(value.get('schema_version')) is int and value['schema_version'] == 2
    data = _envelope(value, RECIPE_FIELDS | ({'device'} if profiled else set()),
                     'mikrocam.laser-recipe', 'recipe', (1, 2))
    device = device_from_data(data['device']) if profiled else None
    if not isinstance(data['passes'], list):
        raise ValueError('recipe.passes must be an ordered array')
    passes = []
    for index, item in enumerate(data['passes']):
        fields = _fields(item, DEVICE_PASS_FIELDS if profiled else PASS_FIELDS, f'recipe.passes[{index}]')
        try:
            passes.append(LaserPass(**fields))
        except ValueError as error:
            raise ValueError(f'recipe.passes[{index}]: {error}') from error
    return LaserRecipe(data['name'], tuple(passes), device)


def recipe_to_json(recipe: LaserRecipe) -> str:
    """Serialize explicit recipe values in deterministic UTF-8-compatible JSON text."""
    return _dump(_recipe_data(recipe))


def recipe_from_json(text: str) -> LaserRecipe:
    """Read versions one and two, rejecting malformed fields and implicit parameters."""
    return _recipe_from_data(_load(text, 'recipe'))


def job_to_json(job: LaserJob) -> str:
    """Serialize source mm copper and placement separately, never preplacing the source."""
    if not isinstance(job, LaserJob):
        raise ValueError('Expected LaserJob')
    placement = job.placement
    return _dump({'kind': 'mikrocam.laser-job', 'schema_version': 2 if job.recipe.device else 1, 'units': 'mm',
                  'name': job.name, 'region_wkb_hex': job.region.wkb_hex, 'recipe': _recipe_data(job.recipe),
                  'placement': {'origin': list(placement.origin), 'translation': list(placement.translation),
                                'rotation_deg': placement.rotation_deg, 'mirror_x': placement.mirror_x}})


def job_from_json(text: str) -> LaserJob:
    """Read a complete versioned job envelope without changing source units or applying placement."""
    data = _envelope(_load(text, 'job'), JOB_FIELDS, 'mikrocam.laser-job', 'job', (1, 2))
    if data['units'] != 'mm':
        raise ValueError('job.units must be mm')
    placement = _fields(data['placement'], PLACEMENT_FIELDS, 'job.placement')
    for field in ('origin', 'translation'):
        if not isinstance(placement[field], list) or len(placement[field]) != 2:
            raise ValueError(f'job.placement.{field} must contain exactly two coordinates')
    try:
        transform = Placement(**placement)
    except ValueError as error:
        raise ValueError(f'job.placement: {error}') from error
    recipe = _recipe_from_data(data['recipe'])
    if (recipe.device is not None) != (data['schema_version'] == 2):
        raise ValueError('job.schema_version must match its recipe version')
    return LaserJob(data['name'], PlanarRegion(data['region_wkb_hex']), recipe, transform)
