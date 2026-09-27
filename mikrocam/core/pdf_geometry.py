"""Bounded PDF material overlays and affine physical stroke expansion."""
from dataclasses import dataclass
import math
from shapely import get_coordinates, get_num_coordinates, STRtree
from shapely.geometry import Polygon, LineString, box
from shapely.geometry.base import BaseGeometry
from .placement import Affine2D, Point2D
from .pdf_models import MAX_PDF_POINTS
from .svg_models import SvgPath, SvgPaint
from .svg_fill import fill_svg_paths
from .svg_paint import render_svg_paths
from .svg_transform import apply_svg_point, validate_affine


@dataclass
class PdfGraphicsState:
    matrix: Affine2D
    clip: BaseGeometry
    width: float = 1.
    cap: int = 0
    join: int = 0
    miter: float = 10.
    fill_white: bool = False
    stroke_white: bool = False


def polygon_parts(geometry: BaseGeometry) -> tuple[Polygon, ...]:
    """Discard boundary-only intersections; retain all polygon material components."""
    if geometry.is_empty:
        return ()
    if geometry.geom_type == 'Polygon':
        return (geometry,)
    if geometry.geom_type in ('MultiPolygon', 'GeometryCollection'):
        return tuple(part for child in geometry.geoms for part in polygon_parts(child))
    return ()


def _validate(geometry: BaseGeometry) -> None:
    if get_num_coordinates(geometry) > MAX_PDF_POINTS:
        raise ValueError('PDF output point budget exceeded')
    if geometry.has_z or geometry.has_m or not geometry.is_valid:
        raise ValueError('PDF geometry must be valid and planar')
    if any(not math.isfinite(v) or abs(v) > 1e9 for xy in get_coordinates(geometry) for v in xy):
        raise ValueError('PDF coordinates exceed finite physical limits')


def _edges(geometry: BaseGeometry) -> list[LineString]:
    lines = []
    for polygon in polygon_parts(geometry):
        for ring in (polygon.exterior, *polygon.interiors):
            points = ring.coords
            lines.extend(LineString((a, b)) for a, b in zip(points, points[1:]) if a != b)
    return lines


def _inverse(matrix: Affine2D) -> Affine2D:
    a, b, d, e, x, y = matrix
    determinant = a * e - b * d
    result = (e / determinant, -b / determinant, -d / determinant, a / determinant,
              (b * y - e * x) / determinant, (d * x - a * y) / determinant)
    validate_affine(result)
    return result


def pdf_strokes(paths: tuple[SvgPath, ...], state: PdfGraphicsState) -> tuple[BaseGeometry, ...]:
    """Expand in the current pen coordinate system; preserve earlier path coordinates."""
    inverse = _inverse(state.matrix)
    local = tuple(SvgPath(tuple(apply_svg_point(inverse, p) for p in path.points), path.closed)
                  for path in paths)
    paint = SvgPaint(False, True, state.width, ('butt', 'round', 'square')[state.cap],
                     ('miter', 'round', 'bevel')[state.join], state.miter)
    # Render each independent subpath separately, so every cross-path union is budgeted below.
    geometries, count = [], 0
    for path in local:
        for geometry in render_svg_paths((path,), paint, state.matrix).geometry_mm:
            count += int(get_num_coordinates(geometry))
            if count > MAX_PDF_POINTS:
                raise ValueError('PDF stroke point budget exceeded')
            geometries.append(geometry)
    return tuple(geometries)


class PdfCanvas:
    """Conservative preflight before every GEOS material/clip overlay."""

    def __init__(self, viewport: Point2D) -> None:
        self.page_clip = box(0., 0., *viewport)
        self.material: BaseGeometry = Polygon()
        self.edge_work = 0

    def overlay(self, first: BaseGeometry, second: BaseGeometry, operation: str) -> BaseGeometry:
        _validate(first)
        _validate(second)
        self.edge_work += int(get_num_coordinates(first) + get_num_coordinates(second))
        if self.edge_work > 2000000:
            raise ValueError('PDF cumulative overlay edge-work budget exceeded')
        left, right = _edges(first), _edges(second)
        if left and right:
            tree, pairs = STRtree(right), 0
            for edge in left:
                pairs += len(tree.query(edge))
                if pairs > 32768:
                    raise ValueError('PDF overlay intersection candidate budget exceeded')
        result = getattr(first, operation)(second)
        _validate(result)
        # GEOS may include line/point contacts in an intersection; those are not painted material.
        parts = polygon_parts(result)
        if not parts:
            return Polygon()
        if len(parts) == 1:
            return parts[0]
        from shapely.geometry import MultiPolygon
        result = MultiPolygon(parts)
        _validate(result)
        return result

    def combine(self, geometries: tuple[BaseGeometry, ...] | list[BaseGeometry]) -> BaseGeometry:
        result = Polygon()
        for geometry in geometries:
            result = self.overlay(result, geometry, 'union')
        return result

    def paint(self, geometries: tuple[BaseGeometry, ...] | list[BaseGeometry],
              state: PdfGraphicsState, white: bool) -> None:
        # Clip each paint group then apply once: white stroke components erase as one paint.
        marked = self.overlay(self.combine(geometries), state.clip, 'intersection')
        self.material = self.overlay(self.material, marked, 'difference' if white else 'union')

    def finish_path(self, paths: tuple[SvgPath, ...], state: PdfGraphicsState,
                    operator: str, pending_clip: str | None) -> None:
        rule = 'evenodd' if operator.endswith('*') else 'nonzero'
        if operator in ('f', 'F', 'f*', 'B', 'B*', 'b', 'b*'):
            self.paint(fill_svg_paths(paths, rule), state, state.fill_white)
        if operator in ('S', 's', 'B', 'B*', 'b', 'b*'):
            self.paint(pdf_strokes(paths, state), state, state.stroke_white)
        if pending_clip is not None:
            clip = self.combine(fill_svg_paths(paths, pending_clip))
            state.clip = self.overlay(state.clip, clip, 'intersection')
