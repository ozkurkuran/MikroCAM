"""Deterministic white-alpha compositing and single threshold operation."""
from collections.abc import Callable
import numpy as np
from .visual import BurnMask, PreparationSettings, RasterFrame, build_grid
from .laser_paths import check_cancelled


def make_burn_mask(frame: RasterFrame, preparation: PreparationSettings,
                   cancelled: Callable[[], bool] | None = None) -> BurnMask:
    if frame.grid != build_grid(preparation): raise ValueError('INVALID_GRID')
    burn = np.empty(frame.valid_area.shape, dtype=bool)
    pixels = frame.rgba.reshape(-1, 4)
    valid = frame.valid_area.reshape(-1)
    result = burn.reshape(-1)
    for start in range(0, len(pixels), 262144):
        check_cancelled(cancelled)
        rgba = pixels[start:start + 262144].astype(np.uint32)
        alpha = rgba[:, 3:4]
        rgb = (rgba[:, :3] * alpha + 255 * (255 - alpha) + 127) // 255
        gray = (299 * rgb[:, 0] + 587 * rgb[:, 1] + 114 * rgb[:, 2] + 500) // 1000
        selected = gray < preparation.threshold
        if preparation.invert: selected = ~selected
        result[start:start + 262144] = selected & valid[start:start + 262144]
    check_cancelled(cancelled)
    return BurnMask(burn, frame.grid)
