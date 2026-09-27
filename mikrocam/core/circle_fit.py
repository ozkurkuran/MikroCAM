"""Conservative complete-circle fitting in a physical millimetre frame."""
import math

import numpy as np
from shapely.geometry import LinearRing

from .placement import Point2D


def fit_closed_circle(raw: tuple[Point2D, ...]) -> tuple[Point2D, float] | None:
    """Fit a finite, explicitly closed, sufficiently resolved simple contour."""
    if type(raw) is not tuple or len(raw) > 100000:
        raise ValueError('Circle points must be an immutable tuple of at most 100000 points')
    for point in raw:
        if type(point) is not tuple or len(point) != 2 or any(
                type(v) not in (int, float) or abs(v) > 1e9 or not math.isfinite(v)
                for v in point):
            raise ValueError('Circle points require finite bounded XY coordinates')
    if len(raw) < 4 or raw[0] != raw[-1]:
        return None
    points = [p for i, p in enumerate(raw[:-1]) if i == 0 or p != raw[i - 1]]
    while len(points) > 1 and points[-1] == points[0]:
        points.pop()
    if len(set(points)) < 12 or not LinearRing(points).is_simple:
        return None
    xy = np.asarray(points, dtype=float)
    origin = xy.mean(axis=0)
    scale = float(np.max(np.abs(xy - origin)))
    if scale <= 0:
        return None
    normal = (xy - origin) / scale
    matrix = np.column_stack((2 * normal[:, 0], 2 * normal[:, 1], np.ones(len(xy))))
    solution, _, rank, _ = np.linalg.lstsq(matrix, np.sum(normal * normal, axis=1), rcond=None)
    if rank != 3:
        return None
    squared = float(solution[2] + solution[0] ** 2 + solution[1] ** 2)
    if squared <= 0:
        return None
    center = origin + solution[:2] * scale
    radius = math.sqrt(squared) * scale
    relative = xy - center
    tolerance = min(.01, radius * .02)
    if float(np.max(np.abs(np.linalg.norm(relative, axis=1) - radius))) > tolerance:
        return None
    midpoints = (relative + np.roll(relative, -1, axis=0)) / 2
    if float(np.max(np.abs(np.linalg.norm(midpoints, axis=1) - radius))) > tolerance:
        return None
    angles = np.arctan2(relative[:, 1], relative[:, 0])
    steps = (np.roll(angles, -1) - angles + math.pi) % (2 * math.pi) - math.pi
    if not (np.all(steps > 0) or np.all(steps < 0)):
        return None
    if float(np.max(np.abs(steps))) > math.pi / 4 or not math.isclose(
            abs(float(np.sum(steps))), 2 * math.pi, abs_tol=1e-8):
        return None
    return (float(center[0]), float(center[1])), radius
