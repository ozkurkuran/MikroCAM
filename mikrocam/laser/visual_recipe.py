"""Versioned portable visual job payloads, without native codecs or Qt."""
from base64 import b64decode, b64encode
from dataclasses import asdict
import json
from mikrocam.core.visual import BurnMask, MAX_JSON_BYTES, MAX_SOURCE_BYTES, PreparationSettings, RasterGrid, SourceAsset, SourceInfo, build_grid
from mikrocam.core.interlace_job import InterlaceSettings, VisualInterlaceJob
from mikrocam.core.placement import Placement
from mikrocam.core.laser_json import _fields, _load, recipe_from_json, recipe_to_json
from .visual_plan import build_plan

JOB_KEYS = {'schema_version', 'kind', 'source', 'preparation', 'grid', 'mask',
            'interlace', 'placement', 'laser_recipe', 'revision', 'provenance'}


def grid_data(grid: RasterGrid) -> dict:
    return {**asdict(grid), 'pitch_mm': grid.pitch_mm,
            'canvas_width_mm': grid.canvas_width_mm, 'canvas_height_mm': grid.canvas_height_mm}


def decode_base64(value: object, limit: int = MAX_SOURCE_BYTES) -> bytes:
    if type(value) is not str or len(value) > 4 * ((limit + 2) // 3): raise ValueError('RECIPE_CORRUPT: base64 size')
    try:
        result = b64decode(value, validate=True)
    except (ValueError, UnicodeError) as error:
        raise ValueError('RECIPE_CORRUPT: invalid base64') from error
    if not 1 <= len(result) <= limit: raise ValueError('RECIPE_CORRUPT: decoded size')
    return result


def job_to_data(job: VisualInterlaceJob, mask_png: bytes) -> dict:
    plan = build_plan(job.mask, job.interlace, job.revision)
    source = {'name': job.source.name, 'data_base64': b64encode(job.source.data).decode('ascii'),
              'sha256': job.source.sha256, 'page_index': job.source.page_index, 'info': asdict(job.source.info)}
    return {'schema_version': 2 if job.laser_recipe and job.laser_recipe.device else 1, 'kind': 'visual_interlace', 'source': source,
            'preparation': asdict(job.preparation), 'grid': grid_data(job.mask.grid),
            'mask': {'encoding': 'png-1bit', 'data_base64': b64encode(mask_png).decode('ascii'),
                     'sha256': job.mask.sha256, 'black_pixel_count': job.mask.black_pixel_count},
            'interlace': {**asdict(job.interlace), 'effective_orders': [list(x) for x in plan.effective_orders]},
            'placement': asdict(job.placement), 'laser_recipe': None if job.laser_recipe is None else
                json.loads(recipe_to_json(job.laser_recipe)), 'revision': job.revision,
            'provenance': {'normalizer_version': 1, 'renderer_name': job.renderer_name,
                           'renderer_version': job.renderer_version}}


def read_document(text: str) -> dict:
    if type(text) is not str or len(text.encode('utf-8')) > MAX_JSON_BYTES: raise ValueError('RECIPE_CORRUPT: JSON size')
    return validate_document(_load(text, 'visual_interlace'))


def validate_document(value: object) -> dict:
    if type(value) is not dict: raise ValueError('RECIPE_CORRUPT: expected object')
    # A missing interlace field in older payloads deliberately means disabled.
    data = dict(value)
    data.setdefault('interlace', {'count': 1})
    _fields(data, JOB_KEYS, 'visual_interlace')
    if type(data['schema_version']) is not int or data['schema_version'] not in (1, 2):
        raise ValueError('RECIPE_VERSION_UNSUPPORTED')
    if data['kind'] != 'visual_interlace': raise ValueError('RECIPE_CORRUPT: kind')
    recipe = data['laser_recipe']
    profiled = isinstance(recipe, dict) and type(recipe.get('schema_version')) is int and recipe['schema_version'] == 2
    if profiled != (data['schema_version'] == 2): raise ValueError('RECIPE_CORRUPT: nested recipe version')
    return data


def preparation_from_data(value: object) -> PreparationSettings:
    fields = set(PreparationSettings.__dataclass_fields__)
    data = dict(_fields(value, fields, 'preparation'))
    if data['crop_rect'] is not None:
        if type(data['crop_rect']) not in (list, tuple): raise ValueError('RECIPE_CORRUPT: crop_rect')
        data['crop_rect'] = tuple(data['crop_rect'])
    return PreparationSettings(**data)


def job_from_data(data: dict, mask: BurnMask) -> VisualInterlaceJob:
    data = validate_document(data)
    preparation = preparation_from_data(data['preparation'])
    grid = build_grid(preparation)
    cached = _fields(data['grid'], set(grid_data(grid)), 'grid')
    for key, value in cached.items():
        valid_type = type(value) is int if key in ('width_px', 'height_px') else type(value) in (int, float)
        if not valid_type: raise ValueError('RECIPE_CORRUPT: grid numeric type')
    if cached != grid_data(grid) or mask.grid != grid: raise ValueError('RECIPE_CORRUPT: grid')
    raw_mask = _fields(data['mask'], {'encoding', 'data_base64', 'sha256', 'black_pixel_count'}, 'mask')
    if raw_mask['encoding'] != 'png-1bit' or raw_mask['sha256'] != mask.sha256 or (
        type(raw_mask['black_pixel_count']) is not int or raw_mask['black_pixel_count'] != mask.black_pixel_count
    ): raise ValueError('RECIPE_CORRUPT: mask integrity')
    source = _fields(data['source'], {'name', 'data_base64', 'sha256', 'page_index', 'info'}, 'source')
    info = dict(_fields(source['info'], set(SourceInfo.__dataclass_fields__), 'source.info'))
    for field in ('native_size_px', 'suggested_size_mm', 'import_notes'):
        if info[field] is not None:
            if type(info[field]) not in (list, tuple): raise ValueError('RECIPE_CORRUPT: source info')
            info[field] = tuple(info[field])
    asset = SourceAsset(source['name'], decode_base64(source['data_base64']), SourceInfo(**info), source['page_index'])
    if asset.sha256 != source['sha256']: raise ValueError('RECIPE_CORRUPT: source hash')
    settings = dict(data['interlace'])
    orders = settings.pop('effective_orders', None)
    unknown = settings.keys() - InterlaceSettings.__dataclass_fields__.keys()
    if unknown: raise ValueError('RECIPE_CORRUPT: interlace fields')
    settings.setdefault('count', 1)
    interlace = InterlaceSettings(**settings)
    expected = build_plan(mask, interlace, data['revision']).effective_orders
    if orders is not None and orders != [list(x) for x in expected]: raise ValueError('RECIPE_CORRUPT: orders')
    placed = dict(_fields(data['placement'], set(Placement.__dataclass_fields__), 'placement'))
    for field in ('origin', 'translation'):
        if type(placed[field]) not in (tuple, list): raise ValueError('RECIPE_CORRUPT: placement')
        placed[field] = tuple(placed[field])
    recipe = None if data['laser_recipe'] is None else recipe_from_json(json.dumps(data['laser_recipe'], allow_nan=False))
    provenance = _fields(data['provenance'], {'normalizer_version', 'renderer_name', 'renderer_version'}, 'provenance')
    if type(provenance['normalizer_version']) is not int or provenance['normalizer_version'] != 1:
        raise ValueError('RECIPE_VERSION_UNSUPPORTED: normalizer')
    if any(type(provenance[k]) is not str or not 1 <= len(provenance[k]) <= 256
           for k in ('renderer_name', 'renderer_version')): raise ValueError('RECIPE_CORRUPT: provenance')
    return VisualInterlaceJob(asset, preparation, mask, interlace, Placement(**placed), recipe,
                             data['revision'], provenance['renderer_name'], provenance['renderer_version'])
