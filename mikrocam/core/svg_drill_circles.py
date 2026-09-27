"""Conservative circle evidence in the already imported physical SVG frame."""
import math

import numpy as np
from shapely.geometry import LinearRing

from .svg_models import SvgElement, SvgRendered
from .svg_transform import apply_svg_point, parse_svg_length


Circle = tuple[tuple[float, float], float]


def _primitive(element: SvgElement) -> Circle | None:
    attributes = dict(element.attributes)
    cx = parse_svg_length(attributes.get('cx', '0'))
    cy = parse_svg_length(attributes.get('cy', '0'))
    if element.kind == 'circle':
        rx = ry = parse_svg_length(attributes.get('r', '0'))
    else:
        rx = parse_svg_length(attributes.get('rx', attributes.get('ry', '0')))
        ry = parse_svg_length(attributes.get('ry', attributes.get('rx', '0')))
    if rx <= 0 or ry <= 0:
        return None
    a, b, d, e, _, _ = element.matrix
    first, second = (a * rx, d * rx), (b * ry, e * ry)
    r1, r2 = math.hypot(*first), math.hypot(*second)
    if not math.isclose(r1, r2, rel_tol=1e-10, abs_tol=1e-12):
        return None
    if abs(first[0] * second[0] + first[1] * second[1]) > r1 * r2 * 1e-10:
        return None
    return apply_svg_point(element.matrix, (cx, cy)), (r1 + r2) / 2


def _fitted(rendered: SvgRendered) -> Circle | None:
    if len(rendered.paths_mm) != 1 or not rendered.paths_mm[0].closed:
        return None
    raw = rendered.paths_mm[0].points
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


def circle_evidence(element: SvgElement, rendered: SvgRendered) -> Circle | None:
    """Return a physical circle only from exact native axes or a fully resolved closed path."""
    if (element.clips or not element.paint.fill or element.fill_is_white is None
            or not rendered.paths_mm or not rendered.geometry_mm):
        return None
    if element.kind in ('circle', 'ellipse'):
        return _primitive(element)
    if element.kind == 'path':
        return _fitted(rendered)
    return None
