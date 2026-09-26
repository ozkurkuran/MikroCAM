"""Geometry-only interpretation of detached Gerber features and explicit outlines."""
from collections.abc import Iterable

from shapely import union_all
from shapely.affinity import scale
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry

from .laser_job import PlanarRegion, region_from_polygons
from .laser_paths import CopperFeatures
from .placement import _validate_geometry


MAX_OUTLINE_RINGS = 500


def _polygon_parts(geometry: BaseGeometry) -> list[Polygon]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, (MultiPolygon, GeometryCollection)):
        return [part for child in geometry.geoms for part in _polygon_parts(child)]
    return []


def _semantic_area(solids: list[BaseGeometry], units: str, copper: PlanarRegion) -> PlanarRegion | None:
    if not solids:
        return None
    selected = region_from_polygons(solids, units).to_geometry().intersection(copper.to_geometry())
    polygons = _polygon_parts(selected)
    return PlanarRegion.from_geometry(union_all(polygons)) if polygons else None


def _outline_rings(value: object) -> list[Polygon]:
    if isinstance(value, LineString):
        _validate_geometry(value)
        if not value.is_ring:
            raise ValueError('Board outline must contain simple closed rings, not open or crossing paths')
        return [Polygon(value)]
    if isinstance(value, (MultiLineString, GeometryCollection)):
        values = value.geoms
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        raise ValueError('Board outline must contain closed planar line rings')
    result = []
    for child in values:
        result.extend(_outline_rings(child))
        if len(result) > MAX_OUTLINE_RINGS:
            raise ValueError(f'Board outline exceeds {MAX_OUTLINE_RINGS} rings')
    return result


def _board_area(outline: object, units: str) -> PlanarRegion:
    if not isinstance(units, str) or units.strip().upper() not in ('MM', 'IN'):
        raise ValueError('Board outline units must be explicit MM or IN')
    rings = _outline_rings(outline)
    if not rings:
        raise ValueError('Board outline must be nonempty')
    for index, ring in enumerate(rings):
        for other in rings[index+1:]:
            if ring.boundary.intersects(other.boundary):
                raise ValueError('Board outline rings must not touch, cross or overlap boundaries')
    area = Polygon()
    for ring in rings:
        area = area.symmetric_difference(ring)
    if units.strip().upper() == 'IN':
        area = scale(area, 25.4, 25.4, origin=(0, 0))
    return PlanarRegion.from_geometry(area)


def features_from_gerber(copper: PlanarRegion, records: Iterable[tuple[str, object, object]],
                         units: str, outline: object = None, outline_units: str | None = None) -> CopperFeatures:
    """Clip classified positive solids to final copper, preserving clear polarity.

    Point follows are flashes; line follows of non-region apertures are traces. None means
    no usable semantic area, whether metadata is absent or those features were fully cleared.
    The supplied copper is already mm; only metadata and outline coordinates are converted.
    """
    if not isinstance(copper, PlanarRegion):
        raise ValueError('Expected source copper PlanarRegion')
    if not isinstance(units, str) or units.strip().upper() not in ('MM', 'IN'):
        raise ValueError('Gerber metadata units must be explicit MM or IN')
    traces, pads = [], []
    for aperture, solid, follow in records:
        if solid is None or follow is None or str(aperture).upper() == 'REG':
            continue
        if isinstance(follow, Point):
            _validate_geometry(follow)
            pads.append(solid)
        elif isinstance(follow, LineString):
            _validate_geometry(follow)
            traces.append(solid)
    board = _board_area(outline, outline_units) if outline is not None else None
    return CopperFeatures(copper, _semantic_area(traces, units, copper),
                          _semantic_area(pads, units, copper), board)
