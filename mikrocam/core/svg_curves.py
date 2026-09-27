"""Finite SVG curve samples with conservative error and allocation bounds."""
import math

from .placement import Point2D
from .svg_models import MAX_ELEMENT_POINTS


def _number(value: float, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f'{label} must be a finite number')
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f'{label} exceeds numeric limit') from error
    if not math.isfinite(result) or abs(result) > 1e9:
        raise ValueError(f'{label} exceeds finite numeric limit')
    return result


def _point(value: Point2D) -> Point2D:
    if type(value) is not tuple or len(value) != 2:
        raise ValueError('Curve point must be an immutable XY tuple')
    return (_number(value[0], 'X'), _number(value[1], 'Y'))


def _tolerance(value: float) -> float:
    result = _number(value, 'Tolerance')
    if result <= 0:
        raise ValueError('Tolerance must be positive')
    return result


def _midpoint(first: Point2D, second: Point2D) -> Point2D:
    return ((first[0] + second[0]) / 2, (first[1] + second[1]) / 2)


def _chord_distance(point: Point2D, start: Point2D, end: Point2D) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return math.dist(point, start)
    projection = ((point[0] - start[0]) * (dx / length)
                  + (point[1] - start[1]) * (dy / length)) / length
    position = min(1., max(0., projection))
    return math.hypot(point[0] - start[0] - position * dx,
                      point[1] - start[1] - position * dy)


def flatten_cubic(start: Point2D, c1: Point2D, c2: Point2D, end: Point2D,
                  tolerance: float) -> tuple[Point2D, ...]:
    """Subdivide until the control hull lies within tolerance of its finite chord."""
    start, c1, c2, end = map(_point, (start, c1, c2, end))
    tolerance = _tolerance(tolerance)
    points = [start]
    pending = [(start, c1, c2, end, 0)]
    while pending:
        first, control1, control2, last, depth = pending.pop()
        error = max(_chord_distance(control1, first, last),
                    _chord_distance(control2, first, last))
        if error <= tolerance:
            if len(points) >= MAX_ELEMENT_POINTS:
                raise ValueError('SVG curve point budget exceeded')
            points.append(last)
            continue
        if depth >= 24:
            raise ValueError('SVG curve subdivision depth limit exceeded')
        a, b, c = (_midpoint(first, control1), _midpoint(control1, control2),
                   _midpoint(control2, last))
        left, right = _midpoint(a, b), _midpoint(b, c)
        middle = _midpoint(left, right)
        pending.append((middle, right, c, last, depth + 1))
        pending.append((first, a, left, middle, depth + 1))
    return tuple(points)


def flatten_quadratic(start: Point2D, control: Point2D, end: Point2D,
                      tolerance: float) -> tuple[Point2D, ...]:
    """Degree-elevate a quadratic without changing its geometry or error budget."""
    start, control, end = map(_point, (start, control, end))
    c1 = tuple(start[axis] / 3 + 2 * control[axis] / 3 for axis in range(2))
    c2 = tuple(end[axis] / 3 + 2 * control[axis] / 3 for axis in range(2))
    return flatten_cubic(start, c1, c2, end, tolerance)


def flatten_arc(center: Point2D, radii: Point2D, rotation_deg: float, start_deg: float,
                sweep_deg: float, start: Point2D, end: Point2D,
                tolerance: float) -> tuple[Point2D, ...]:
    """Use a maximum-radius sagitta bound, including exact caller-supplied endpoints."""
    center, radii, start, end = map(_point, (center, radii, start, end))
    rotation_deg = _number(rotation_deg, 'Arc rotation')
    start_deg = _number(start_deg, 'Arc start angle')
    sweep_deg = _number(sweep_deg, 'Arc sweep')
    tolerance = _tolerance(tolerance)
    if min(radii) <= 0 or abs(sweep_deg) > 360:
        raise ValueError('Arc requires positive radii and at most a full turn')
    rotation = math.radians(rotation_deg % 360)
    cosine, sine = math.cos(rotation), math.sin(rotation)

    def ellipse_point(degrees: float) -> Point2D:
        angle = math.radians(degrees)
        x, y = radii[0] * math.cos(angle), radii[1] * math.sin(angle)
        return _point((center[0] + x * cosine - y * sine,
                       center[1] + x * sine + y * cosine))

    first = start_deg % 360
    endpoint_error = max(math.dist(ellipse_point(first), start),
                         math.dist(ellipse_point(first + sweep_deg), end))
    remaining = tolerance - endpoint_error
    if remaining <= 0:
        raise ValueError('SVG arc endpoints disagree with its ellipse beyond tolerance')
    ratio = min(1., remaining / (2 * max(radii)))
    if ratio == 0:
        raise ValueError('SVG arc precision exceeds point budget')
    step = min(math.pi / 2, 4 * math.asin(math.sqrt(ratio)))
    count = max(1, math.ceil(abs(math.radians(sweep_deg)) / step))
    if count + 1 > MAX_ELEMENT_POINTS:
        raise ValueError('SVG arc point budget exceeded')
    points = [ellipse_point(first + sweep_deg * index / count) for index in range(count + 1)]
    points[0], points[-1] = start, end
    return tuple(points)
