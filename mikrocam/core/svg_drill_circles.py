"""Conservative circle evidence in the already imported physical SVG frame."""
import math

from .circle_fit import fit_closed_circle

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
    return fit_closed_circle(rendered.paths_mm[0].points)


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
