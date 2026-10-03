"""Bounded display-only reductions; never generate production data from previews."""
from collections.abc import Callable
import math
import numpy as np
from .visual import BurnMask, RasterFrame, integer_range
from .laser_paths import check_cancelled

COLORS = ((220, 40, 40), (35, 165, 50), (45, 75, 220), (200, 125, 20),
          (155, 50, 175), (20, 160, 175), (135, 100, 65), (90, 90, 90))


def _counts(mask: BurnMask, step: int, count: int, group: int | None) -> np.ndarray:
    selected = mask.burn
    if group is not None:
        selected = np.zeros(mask.burn.shape, dtype=bool)
        selected[group::count] = mask.burn[group::count]
    reduced = np.add.reduceat(selected, np.arange(0, mask.grid.width_px, step), axis=1, dtype=np.uint32)
    return np.add.reduceat(reduced, np.arange(0, mask.grid.height_px, step), axis=0, dtype=np.uint32)


def preview_rgb(mask: BurnMask, count: int, group: int | None = None,
                combined: bool = False, max_side: int = 1200) -> np.ndarray:
    integer_range(count, 1, 8, 'count'); integer_range(max_side, 1, 4096, 'max_side')
    if group is not None: integer_range(group, 0, count - 1, 'group')
    step = max(1, math.ceil(max(mask.burn.shape) / max_side))
    counts = _counts(mask, step, count, group)
    rgb = np.full((*counts.shape, 3), 255, dtype=np.uint8)
    rgb[counts > 0] = 0
    if combined:
        weighted = np.zeros((*counts.shape, 3), dtype=np.float64)
        for k in range(count): weighted += _counts(mask, step, count, k)[:, :, None] * np.array(COLORS[k])
        nonempty = counts > 0
        rgb[nonempty] = np.rint(weighted[nonempty] / counts[nonempty, None]).astype(np.uint8)
    return rgb


def preview_images(mask: BurnMask, count: int, cancelled: Callable[[], bool] | None = None) -> dict:
    """Build compact thumbnails in the worker, with no N full-resolution copies."""
    check_cancelled(cancelled)
    master = preview_rgb(mask, count)
    groups = []
    for k in range(count):
        check_cancelled(cancelled)
        groups.append(preview_rgb(mask, count, k))
    check_cancelled(cancelled)
    combined = preview_rgb(mask, count, combined=True)
    check_cancelled(cancelled)
    return {'master': master, 'groups': tuple(groups), 'combined': combined, 'source': None}


def frame_preview(frame: RasterFrame, max_side: int = 1200) -> np.ndarray:
    integer_range(max_side, 1, 4096, 'max_side')
    step = max(1, math.ceil(max(frame.rgba.shape[:2]) / max_side))
    rgba = frame.rgba[::step, ::step].astype(np.uint32)
    alpha = rgba[:, :, 3:4]
    return ((rgba[:, :, :3] * alpha + 255 * (255 - alpha) + 127)//255).astype(np.uint8)
