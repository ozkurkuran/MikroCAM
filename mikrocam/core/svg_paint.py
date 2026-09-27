"""Bounded SVG primitive construction and local fill/stroke material geometry."""
import math

from shapely import affinity, get_coordinates, get_num_coordinates, union_all
from shapely.geometry import LineString, Point, Polygon

from .svg_curves import flatten_arc
from .svg_fill import fill_svg_paths
from .svg_models import (CURVE_TOLERANCE_MM, MAX_ELEMENT_POINTS, MAX_SVG_RINGS,
                         SvgNotice, SvgPaint, SvgPath, SvgRendered, validate_attributes)
from .svg_transform import (affine_scale_bound, apply_svg_point, parse_svg_length,
                            parse_svg_numbers, validate_affine)
from .placement import Affine2D


def _tolerance(value: float) -> None:
    if type(value) not in (int, float):
        raise ValueError('SVG tolerance must be positive and finite')
    try:
        valid = math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError('SVG tolerance must be positive and finite')


def _closed(points: list[tuple[float, float]]) -> SvgPath:
    if points[-1] != points[0]:
        points.append(points[0])
    return SvgPath(tuple(points), True)


def _ellipse(cx: float, cy: float, rx: float, ry: float, tolerance: float) -> SvgPath:
    points = []
    endpoints = ((cx + rx, cy), (cx, cy + ry), (cx - rx, cy), (cx, cy - ry), (cx + rx, cy))
    for index in range(4):
        arc = flatten_arc((cx, cy), (rx, ry), 0., index * 90., 90.,
                          endpoints[index], endpoints[index + 1], tolerance)
        points.extend(arc if not points else arc[1:])
        if len(points) > MAX_ELEMENT_POINTS:
            raise ValueError('SVG primitive point budget exceeded')
    return _closed(points)


def _rect(values: dict[str, str], tolerance: float) -> tuple[SvgPath, ...]:
    number = lambda key, default='0': parse_svg_length(values.get(key, default))
    x, y, width, height = (number(key) for key in ('x', 'y', 'width', 'height'))
    rx = number('rx', values.get('ry', '0'))
    ry = number('ry', values.get('rx', '0'))
    if min(width, height, rx, ry) < 0:
        raise ValueError('SVG rectangle dimensions must be nonnegative')
    if width == 0 or height == 0:
        return ()
    rx, ry = min(rx, width / 2), min(ry, height / 2)
    if rx == 0 or ry == 0:
        return (_closed([(x, y), (x + width, y), (x + width, y + height), (x, y + height)]),)
    centers = ((x + width - rx, y + ry), (x + width - rx, y + height - ry),
               (x + rx, y + height - ry), (x + rx, y + ry))
    endpoints = (((x + width - rx, y), (x + width, y + ry)),
                 ((x + width, y + height - ry), (x + width - rx, y + height)),
                 ((x + rx, y + height), (x, y + height - ry)),
                 ((x, y + ry), (x + rx, y)))
    points = []
    for index, (center, ends) in enumerate(zip(centers, endpoints)):
        arc = flatten_arc(center, (rx, ry), 0., -90. + index * 90., 90., *ends, tolerance)
        points.extend(arc)
        if len(points) + 1 > MAX_ELEMENT_POINTS:
            raise ValueError('SVG primitive point budget exceeded')
    return (_closed(points),)


def primitive_paths(kind: str, attributes: tuple[tuple[str, str], ...],
                    tolerance: float) -> tuple[SvgPath, ...]:
    """Construct local source paths without applying viewport or element transforms."""
    _tolerance(tolerance)
    validate_attributes(attributes)
    values = dict(attributes)
    number = lambda key: parse_svg_length(values.get(key, '0'))
    if kind == 'rect':
        return _rect(values, tolerance)
    if kind in ('circle', 'ellipse'):
        cx, cy = number('cx'), number('cy')
        rx = number('r') if kind == 'circle' else number('rx')
        ry = rx if kind == 'circle' else number('ry')
        if min(rx, ry) < 0:
            raise ValueError('SVG radii must be nonnegative')
        return () if rx == 0 or ry == 0 else (_ellipse(cx, cy, rx, ry, tolerance),)
    if kind == 'line':
        return (SvgPath(((number('x1'), number('y1')), (number('x2'), number('y2')))),)
    if kind in ('polygon', 'polyline'):
        numbers = parse_svg_numbers(values.get('points', ''))
        if not numbers:
            return ()
        minimum = 6 if kind == 'polygon' else 4
        if len(numbers) % 2 or len(numbers) < minimum or len(numbers) // 2 + (kind == 'polygon') > MAX_ELEMENT_POINTS:
            raise ValueError('SVG points require a bounded complete coordinate sequence')
        points = list(zip(numbers[::2], numbers[1::2]))
        return (_closed(points) if kind == 'polygon' else SvgPath(tuple(points)),)
    raise ValueError('Unsupported SVG primitive kind')


def _miter_patches(path: SvgPath, radius: float, limit: float) -> list[Polygon]:
    # GEOS clips long miters; SVG's miter mode instead falls back completely to bevel.
    if limit <= 1:
        return []
    points = [point for index, point in enumerate(path.points)
              if index == 0 or point != path.points[index - 1]]
    if path.closed:
        ring = points[:-1]
        points = [ring[-1], *ring, ring[0]]
    patches = []
    for before, corner, after in zip(points, points[1:], points[2:]):
        incoming = (corner[0] - before[0], corner[1] - before[1])
        outgoing = (after[0] - corner[0], after[1] - corner[1])
        incoming = tuple(value / math.hypot(*incoming) for value in incoming)
        outgoing = tuple(value / math.hypot(*outgoing) for value in outgoing)
        cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
        denominator = 1 + incoming[0] * outgoing[0] + incoming[1] * outgoing[1]
        if cross == 0 or denominator < 2 / (limit * limit):
            continue
        side = 1 if cross > 0 else -1
        normal1 = (side * incoming[1], -side * incoming[0])
        normal2 = (side * outgoing[1], -side * outgoing[0])
        first = tuple(corner[axis] + radius * normal1[axis] for axis in range(2))
        last = tuple(corner[axis] + radius * normal2[axis] for axis in range(2))
        tip = tuple(corner[axis] + radius * (normal1[axis] + normal2[axis]) / denominator
                    for axis in range(2))
        patch = Polygon((first, tip, last))
        if patch.area > 0:
            patches.append(patch)
    return patches


def _open_ring_buffer(path: SvgPath, radius: float, segments: int, cap: int, join: int) -> Polygon:
    """GEOS closes coincident endpoints; preserve SVG's explicit open-path caps."""
    points = [point for index, point in enumerate(path.points)
              if index == 0 or point != path.points[index - 1]]
    pieces = [LineString(triple).buffer(radius, quad_segs=segments, cap_style=2, join_style=join)
              for triple in zip(points, points[1:], points[2:])]
    for endpoint, neighbor in ((points[0], points[1]), (points[-1], points[-2])):
        if cap == 1:
            pieces.append(Point(endpoint).buffer(radius, quad_segs=segments))
        elif cap == 3:
            length = math.dist(endpoint, neighbor)
            direction = tuple((endpoint[axis] - neighbor[axis]) / length for axis in range(2))
            normal = (-direction[1], direction[0])
            pieces.append(Polygon(tuple(tuple(endpoint[axis] + radius * (
                forward * direction[axis] + side * normal[axis]) for axis in range(2))
                for forward, side in ((0, -1), (1, -1), (1, 1), (0, 1)))))
    return union_all(pieces)


def _stroke(paths: tuple[SvgPath, ...], paint: SvgPaint, tolerance: float) -> list[Polygon]:
    radius = paint.width / 2
    if radius == 0:
        return []
    rounded = paint.linecap == 'round' or paint.linejoin == 'round'
    if rounded and tolerance < radius:
        angle = math.acos(max(-1., 1. - tolerance / radius))
        if angle == 0:
            raise ValueError('SVG stroke point budget exceeded')
        segments = max(1, math.ceil(math.pi / (4 * angle)))
    else:
        segments = 1
    cap = {'round': 1, 'butt': 2, 'square': 3}[paint.linecap]
    join = 1 if paint.linejoin == 'round' else 3
    result = []
    budget = 0
    for path in paths:
        budget += len(path.points) * (4 * segments + 4)
        if budget > MAX_ELEMENT_POINTS:
            raise ValueError('SVG stroke point budget exceeded')
        if len(set(path.points)) == 1:
            if paint.linecap == 'butt':
                continue
            if paint.linecap == 'square':
                x, y = path.points[0]
                solid = Polygon(((x-radius, y-radius), (x+radius, y-radius),
                                 (x+radius, y+radius), (x-radius, y+radius)))
            else:
                solid = Point(path.points[0]).buffer(radius, quad_segs=segments)
        else:
            line = LineString(path.points)
            if not line.is_simple:
                raise ValueError('Self-intersecting or overlapping SVG strokes are unsupported')
            solid = (_open_ring_buffer(path, radius, segments, cap, join)
                     if line.is_ring and not path.closed else
                     line.buffer(radius, quad_segs=segments, cap_style=cap, join_style=join))
            if paint.linejoin == 'miter':
                patches = _miter_patches(path, radius, paint.miterlimit)
                if patches:
                    solid = union_all([solid, *patches])
        if not solid.is_empty:
            result.append(solid)
    return result


def _validate_output(geometries: tuple, points: int) -> None:
    for geometry in geometries:
        points += get_num_coordinates(geometry)
        if points > MAX_ELEMENT_POINTS:
            raise ValueError('SVG rendered point budget exceeded')
        if geometry.is_empty or not geometry.is_valid or geometry.has_z or geometry.has_m:
            raise ValueError('SVG material must be valid nonempty planar geometry')
        coordinates = get_coordinates(geometry)
        if any(not math.isfinite(value) or abs(value) > 1e9 for point in coordinates for value in point):
            raise ValueError('SVG material coordinates exceed finite bounds')


def render_svg_paths(paths: tuple[SvgPath, ...], paint: SvgPaint, matrix: Affine2D, *,
                     retain_centerlines: bool = False) -> SvgRendered:
    """Expand local stroke before mapping, retaining original transformed path facts."""
    if type(paths) is not tuple or any(type(path) is not SvgPath for path in paths):
        raise ValueError('SVG rendering requires immutable SvgPath values')
    if type(paint) is not SvgPaint or type(retain_centerlines) is not bool:
        raise ValueError('SVG rendering requires validated paint and boolean retention')
    validate_affine(matrix)
    count = sum(len(path.points) for path in paths)
    if count > MAX_ELEMENT_POINTS or sum(path.closed for path in paths) > MAX_SVG_RINGS:
        raise ValueError('SVG path point/ring budget exceeded')
    transformed = tuple(SvgPath(tuple(apply_svg_point(matrix, point) for point in path.points), path.closed)
                        for path in paths)
    materials = fill_svg_paths(paths, paint.fill_rule) if paint.fill else []
    if paint.stroke:
        tolerance = CURVE_TOLERANCE_MM / (2 * affine_scale_bound(matrix))
        materials.extend(_stroke(paths, paint, tolerance))
    geometries, notices = (), ()
    if materials:
        local = union_all(materials)
        _validate_output((local,), count)
        geometries = (affinity.affine_transform(local, matrix),) if not local.is_empty else ()
    if retain_centerlines and not (paint.stroke and paint.width > 0):
        lines = tuple(LineString(path.points) for path in transformed if not path.closed
                      and len(set(path.points)) >= 2 and (not paint.fill or len(set(path.points)) < 3))
        geometries += lines
        if lines:
            notices = (SvgNotice('retained-centerline', 'Unpainted open paths retained as CAM centrelines.'),)
    _validate_output(geometries, count)
    return SvgRendered(transformed, geometries, notices)
