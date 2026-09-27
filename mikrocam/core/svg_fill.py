"""Bounded SVG fill winding, preserving multiplicity through noded compound contours."""
from shapely import get_num_coordinates, STRtree, union_all
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize

from .svg_models import MAX_ELEMENT_POINTS, MAX_SVG_RINGS, SvgPath

MAX_COMPLEX_SEGMENTS = 2048
MAX_INTERSECTION_PAIRS = 32768
MAX_FILL_FACES = 2048
MAX_WINDING_OPERATIONS = 2000000


def _simple_fill(contours: tuple[tuple, ...], rule: str) -> list[Polygon] | None:
    rings = []
    for points in contours:
        polygon = Polygon(points)
        if polygon.is_empty or not polygon.is_valid or not polygon.exterior.is_simple:
            return None
        rings.append((polygon, 1 if polygon.exterior.is_ccw else -1))
    rings.sort(key=lambda item: item[0].area, reverse=True)
    parents, winding, depths = [], [], []
    for index, (polygon, sign) in enumerate(rings):
        containers = []
        for previous, (outer, _) in enumerate(rings[:index]):
            if polygon.boundary.intersects(outer.boundary):
                return None
            if outer.contains(polygon):
                containers.append(previous)
        parent = containers[-1] if containers else None
        parents.append(parent)
        winding.append(sign + (winding[parent] if parent is not None else 0))
        depths.append(1 + (depths[parent] if parent is not None else 0))
    filled = []
    for index, (polygon, _) in enumerate(rings):
        if (depths[index] % 2 == 1) if rule == 'evenodd' else (winding[index] != 0):
            children = [rings[child][0] for child, parent in enumerate(parents) if parent == index]
            filled.append(polygon.difference(union_all(children)) if children else polygon)
    return filled


def _segments(contours: tuple[tuple, ...]) -> list[tuple]:
    result = []
    for points in contours:
        for start, end in zip(points, points[1:]):
            if start == end:
                continue
            if len(result) >= MAX_COMPLEX_SEGMENTS:
                raise ValueError('SVG complex fill segment budget exceeded; simplify the source')
            result.append((start, end))
    return result


def _faces(segments: list[tuple]) -> list[Polygon]:
    lines = [LineString(segment) for segment in segments]
    tree = STRtree(lines)
    pairs = 0
    for index, line in enumerate(lines):
        pairs += sum(int(other) > index for other in tree.query(line, predicate='intersects'))
        if pairs > MAX_INTERSECTION_PAIRS:
            raise ValueError('SVG complex fill intersection budget exceeded; simplify the source')
    faces, coordinates = [], 0
    for face in polygonize(union_all(lines)):
        coordinates += int(get_num_coordinates(face))
        if len(faces) >= MAX_FILL_FACES or coordinates > MAX_ELEMENT_POINTS:
            raise ValueError('SVG compound fill face/coordinate budget exceeded; simplify the source')
        if not face.is_valid:
            raise ValueError('SVG compound fill produced invalid topology')
        faces.append(face)
    if len(faces) * len(segments) > MAX_WINDING_OPERATIONS:
        raise ValueError('SVG compound winding operation budget exceeded; simplify the source')
    return faces


def _winding(point: tuple[float, float], segments: list[tuple]) -> int:
    x, y = point
    winding = 0
    for (ax, ay), (bx, by) in segments:
        cross = (bx - ax) * (y - ay) - (x - ax) * (by - ay)
        if ay <= y < by and cross > 0:
            winding += 1
        elif by <= y < ay and cross < 0:
            winding -= 1
    return winding


def fill_svg_paths(paths: tuple[SvgPath, ...], rule: str) -> list[Polygon]:
    """Fill original source contours with a bounded exact winding interpretation."""
    if type(paths) is not tuple or any(type(path) is not SvgPath for path in paths):
        raise ValueError('SVG fill requires immutable source paths')
    if rule not in ('nonzero', 'evenodd') or type(rule) is not str:
        raise ValueError('SVG fill rule must be nonzero or evenodd')
    if sum(len(path.points) for path in paths) > MAX_ELEMENT_POINTS:
        raise ValueError('SVG fill coordinate budget exceeded')
    contours = tuple(path.points if path.points[0] == path.points[-1] else path.points + (path.points[0],)
                     for path in paths if len(set(path.points)) >= 3)
    if len(contours) > MAX_SVG_RINGS:
        raise ValueError('SVG fill ring budget exceeded')
    simple = _simple_fill(contours, rule)
    if simple is not None:
        return simple
    segments = _segments(contours)
    result = []
    for face in _faces(segments):
        point = face.representative_point()
        winding = _winding((point.x, point.y), segments)
        if (winding % 2 != 0) if rule == 'evenodd' else (winding != 0):
            result.append(face)
    return result
