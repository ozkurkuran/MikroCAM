"""Native PNG boundary for portable, embedded visual jobs."""
import json
from pathlib import Path
from collections.abc import Callable
from mikrocam.core.interlace_job import VisualInterlaceJob
from mikrocam.core.visual import MAX_JSON_BYTES, build_grid
from mikrocam.core.laser_paths import check_cancelled
from mikrocam.laser.visual_recipe import (decode_base64, job_to_data, job_from_data, read_document,
                                          preparation_from_data, validate_document)
from mikrocam.laser.visual_files import atomic_write
from .visual_png import encode_mask_png, decode_mask_png


def job_to_payload(job: VisualInterlaceJob) -> dict:
    return job_to_data(job, encode_mask_png(job.mask))


def job_from_payload(payload: object) -> VisualInterlaceJob:
    data = validate_document(payload)
    grid = build_grid(preparation_from_data(data['preparation']))
    if type(data['mask']) is not dict or 'data_base64' not in data['mask']: raise ValueError('RECIPE_CORRUPT: mask')
    mask = decode_mask_png(decode_base64(data['mask']['data_base64']), grid)
    return job_from_data(data, mask)


def save_visual_recipe(job: VisualInterlaceJob, destination: Path,
                       cancelled: Callable[[], bool] | None = None) -> None:
    check_cancelled(cancelled)
    text = json.dumps(job_to_payload(job), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    data = text.encode('utf-8')
    if len(data) > MAX_JSON_BYTES: raise ValueError('SOURCE_TOO_LARGE: JSON limit')
    atomic_write(destination, data, cancelled)


def load_visual_recipe(source: Path, cancelled: Callable[[], bool] | None = None) -> VisualInterlaceJob:
    check_cancelled(cancelled)
    with Path(source).open('rb') as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES: raise ValueError('RECIPE_CORRUPT: JSON limit')
    try: text = raw.decode('utf-8')
    except UnicodeError as error: raise ValueError('RECIPE_CORRUPT: UTF-8') from error
    result = job_from_payload(read_document(text))
    check_cancelled(cancelled)
    return result
