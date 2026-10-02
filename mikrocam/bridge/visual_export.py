"""Complementary full-canvas PNG transfer; distinct from native LightBurn export."""
from collections.abc import Callable
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
import zipfile
from mikrocam.core.interlace_job import VisualInterlaceJob, InterlacePlan
from mikrocam.core.visual_interlace import materialize_group
from mikrocam.core.laser_paths import check_cancelled
from mikrocam.laser.visual_plan import validate_plan
from .visual_png import encode_mask_png
from .visual_recipe import job_to_payload


def export_png_package(job: VisualInterlaceJob, plan: InterlacePlan, destination: Path,
                       cancelled: Callable[[], bool] | None = None) -> None:
    validate_plan(job.mask, plan, job.revision)
    if plan.settings != job.interlace: raise ValueError('PLAN_STALE: settings')
    destination = Path(destination)
    temporary = None
    try:
        check_cancelled(cancelled)
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
                for k in range(job.interlace.count):
                    check_cancelled(cancelled)
                    part = materialize_group(job.mask, k, job.interlace.count)
                    archive.writestr(f'group-{k:02d}.png', encode_mask_png(part))
                archive.writestr('job.json', json.dumps(job_to_payload(job), ensure_ascii=False, allow_nan=False))
                manifest = {'kind': 'visual_interlace_png', 'schema_version': 1, 'units': 'mm',
                            'dpi': job.preparation.requested_dpi, 'pitch_mm': job.mask.grid.pitch_mm,
                            'canvas_mm': [job.mask.grid.canvas_width_mm, job.mask.grid.canvas_height_mm],
                            'placement': asdict(job.placement), 'passes': [asdict(p) for p in plan.passes],
                            'native_lightburn_settings_applied': False}
                archive.writestr('manifest.json', json.dumps(manifest, allow_nan=False))
            stream.flush(); os.fsync(stream.fileno())
        check_cancelled(cancelled)
        os.replace(temporary, destination); temporary = None
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
