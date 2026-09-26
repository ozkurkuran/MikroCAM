"""Build geometry-only pass ZIPs and publish them at one atomic commit boundary."""
import hashlib
import math
import os
from pathlib import Path
import tempfile
import zipfile
from typing import BinaryIO

from mikrocam.core.laser_json import PASS_FIELDS, recipe_to_json
from mikrocam.core.laser_manifest import MAX_PASSES, manifest_to_json
from mikrocam.core.laser_paths import CancelCheck, LaserPlan, check_cancelled


MAX_EXPORT_PATHS = 2_000_000
MAX_EXPORT_VERTICES = 10_000_000
MAX_GEOMETRY_BYTES = 512 * 1024 * 1024
README = '''MikroCAM geometry-only laser transfer

Import each ordinal pass file separately into LightBurn or EZCAD, in manifest pass order.
Verify import scale in mm against manifest bounds and a known dimension before proceeding.
SVG maps placed coordinates to a shared local Y-down frame: x'=x-xmin, y'=ymax-y.
SVG physical dimensions are mm; a zero extent uses a 1 mm viewport without extra geometry.
DXF preserves placed XY and declares millimetres. Check orientation and registration of all
passes after import; never automatically centre each pass independently.

Manually transfer each pass's power_percent (power %), speed_mm_s (speed mm/s),
frequency_khz (frequency kHz), and pulse_width_ns (pulse width ns) from recipe.json.
Geometry files do not apply these settings. Check target machine support and calibration.
Target optimization can reorder paths and defeat interlace order; inspect or disable it.

Structural/parser checks do not establish target-app import or physical process validation.
Verify the actual licensed target application and a suitable physical test coupon separately.
This package connects to no hardware, arms no laser, and performs no motion or emission.
'''


def _measure(plan: LaserPlan, cancelled: CancelCheck) -> list[float]:
    passes = len(plan.job.recipe.passes)
    if passes > MAX_PASSES or len(plan.paths) * passes > MAX_EXPORT_PATHS:
        raise ValueError('Export exceeds pass or emitted path limit')
    vertices = 0
    xmin = ymin = math.inf
    xmax = ymax = -math.inf
    for path in plan.paths:
        check_cancelled(cancelled)
        vertices += len(path.points)
        if vertices * passes > MAX_EXPORT_VERTICES:
            raise ValueError('Export exceeds emitted vertex limit')
        for x, y in path.points:
            xmin, ymin = min(xmin, x), min(ymin, y)
            xmax, ymax = max(xmax, x), max(ymax, y)
    if not math.isfinite(xmax - xmin) or not math.isfinite(ymax - ymin):
        raise ValueError('Export bounds exceed finite coordinate extents')
    return [xmin, ymin, xmax, ymax]


def _geometry_document(plan: LaserPlan, bounds: list[float], format: str,
                       index: int, cancelled: CancelCheck) -> str:
    if format == 'svg':
        from mikrocam.core.laser_svg import svg_document
        return svg_document(plan.paths, bounds, plan.job.recipe.passes[index - 1].name, cancelled)
    from mikrocam.core.laser_dxf import dxf_document
    return dxf_document(plan.paths, index, cancelled)


def _write_entry(archive: zipfile.ZipFile, name: str, data: bytes,
                 cancelled: CancelCheck) -> None:
    check_cancelled(cancelled)
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data)
    check_cancelled(cancelled)


def _write_archive(stream: BinaryIO, plan: LaserPlan, bounds: list[float], format: str,
                   cancelled: CancelCheck) -> None:
    entries = []
    geometry_bytes = 0
    with zipfile.ZipFile(stream, 'w') as archive:
        for index, settings in enumerate(plan.job.recipe.passes, 1):
            check_cancelled(cancelled)
            geometry = _geometry_document(plan, bounds, format, index, cancelled).encode('utf-8')
            geometry_bytes += len(geometry)
            if geometry_bytes > MAX_GEOMETRY_BYTES:
                raise ValueError('Export exceeds uncompressed geometry byte limit')
            filename = f'pass-{index:03d}.{format}'
            _write_entry(archive, filename, geometry, cancelled)
            entries.append({'index': index, 'name': settings.name, 'file': filename,
                            'sha256': hashlib.sha256(geometry).hexdigest(),
                            'path_count': len(plan.paths),
                            'settings': {field: getattr(settings, field) for field in PASS_FIELDS}})
        manifest = {'kind': 'mikrocam.laser-export', 'schema_version': 1, 'format': format,
                    'units': 'mm', 'job_name': plan.job.name, 'bounds_mm': bounds,
                    'interlace_n': plan.options.interlace_n,
                    'coordinate_mapping': 'svg-local-y-down' if format == 'svg' else 'placed-xy',
                    'recipe_file': 'recipe.json', 'passes': entries}
        _write_entry(archive, 'recipe.json', recipe_to_json(plan.job.recipe).encode('utf-8'), cancelled)
        _write_entry(archive, 'manifest.json', manifest_to_json(manifest).encode('utf-8'), cancelled)
        _write_entry(archive, 'README.txt', README.encode('utf-8'), cancelled)


def export_plan(plan: LaserPlan, destination: Path | str, format: str,
                cancelled: CancelCheck = None) -> Path:
    """Write a complete package or preserve the existing destination on failure/cancel."""
    if not isinstance(plan, LaserPlan):
        raise ValueError('Export requires a LaserPlan')
    if format not in ('svg', 'dxf'):
        raise ValueError('Export format must be svg or dxf')
    if not isinstance(destination, (str, Path)) or not str(destination):
        raise ValueError('Export destination must be a nonempty path')
    destination = Path(destination).resolve()
    check_cancelled(cancelled)
    bounds = _measure(plan, cancelled)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w+b', prefix='.mikrocam-export-', suffix='.tmp',
                                         dir=destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            _write_archive(stream, plan, bounds, format, cancelled)
            stream.flush()
            os.fsync(stream.fileno())
        check_cancelled(cancelled)
        os.replace(temporary, destination)
        temporary = None
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
