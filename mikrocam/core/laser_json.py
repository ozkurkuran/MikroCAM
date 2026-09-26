"""Strict deterministic schema-one JSON text for laser recipes and jobs."""
import json

from .laser_job import LaserJob, LaserPass, LaserRecipe, PlanarRegion
from .placement import Placement


PASS_FIELDS = {'name', 'power_percent', 'speed_mm_s', 'frequency_khz', 'pulse_width_ns'}
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


def _envelope(value: object, expected: set[str], kind: str, context: str) -> dict:
    data = _fields(value, expected, context)
    if data['kind'] != kind:
        raise ValueError(f'{context}.kind must be {kind!r}')
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
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
    return {'kind': 'mikrocam.laser-recipe', 'schema_version': 1, 'name': recipe.name,
            'passes': [{field: getattr(value, field) for field in PASS_FIELDS} for value in recipe.passes]}


def _recipe_from_data(value: object) -> LaserRecipe:
    data = _envelope(value, RECIPE_FIELDS, 'mikrocam.laser-recipe', 'recipe')
    if not isinstance(data['passes'], list):
        raise ValueError('recipe.passes must be an ordered array')
    passes = []
    for index, item in enumerate(data['passes']):
        fields = _fields(item, PASS_FIELDS, f'recipe.passes[{index}]')
        try:
            passes.append(LaserPass(**fields))
        except ValueError as error:
            raise ValueError(f'recipe.passes[{index}]: {error}') from error
    return LaserRecipe(data['name'], tuple(passes))


def recipe_to_json(recipe: LaserRecipe) -> str:
    """Serialize explicit recipe values in deterministic UTF-8-compatible JSON text."""
    return _dump(_recipe_data(recipe))


def recipe_from_json(text: str) -> LaserRecipe:
    """Read schema one, rejecting omitted/unknown/duplicate fields and implicit parameters."""
    return _recipe_from_data(_load(text, 'recipe'))


def job_to_json(job: LaserJob) -> str:
    """Serialize source mm copper and placement separately, never preplacing the source."""
    if not isinstance(job, LaserJob):
        raise ValueError('Expected LaserJob')
    placement = job.placement
    return _dump({'kind': 'mikrocam.laser-job', 'schema_version': 1, 'units': 'mm',
                  'name': job.name, 'region_wkb_hex': job.region.wkb_hex, 'recipe': _recipe_data(job.recipe),
                  'placement': {'origin': list(placement.origin), 'translation': list(placement.translation),
                                'rotation_deg': placement.rotation_deg, 'mirror_x': placement.mirror_x}})


def job_from_json(text: str) -> LaserJob:
    """Read a complete versioned job envelope without changing source units or applying placement."""
    data = _envelope(_load(text, 'job'), JOB_FIELDS, 'mikrocam.laser-job', 'job')
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
    return LaserJob(data['name'], PlanarRegion(data['region_wkb_hex']),
                    _recipe_from_data(data['recipe']), transform)
