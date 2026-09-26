"""Deterministic contour and hatch geometry in source millimetres."""
import math

from shapely.geometry import GeometryCollection, LineString, MultiLineString, Polygon
from shapely.geometry.base import BaseGeometry

from .laser_job import PlanarRegion
from .laser_paths import (CONTOUR_MODES, MAX_SCAN_LINES, CancelCheck, CopperFeatures,
                          LaserPath, PlanOptions, check_cancelled, check_path_count)
from .placement import Placement


def _polygons(region: PlanarRegion) -> tuple[Polygon, ...]:
    geometry = region.to_geometry()
    return (geometry,) if isinstance(geometry, Polygon) else tuple(geometry.geoms)


def selected_area(features: CopperFeatures, region_mode: str) -> PlanarRegion:
    """Select copper or explicit containing-board minus copper, preserving cutouts."""
    if region_mode == 'copper':
        return features.copper
    if region_mode != 'clearance':
        raise ValueError('Area must be copper or clearance')
    if features.board is None:
        raise ValueError('Clearance requires an explicit closed board outline')
    board, copper = features.board.to_geometry(), features.copper.to_geometry()
    if not board.covers(copper):
        raise ValueError('Board outline must contain all source copper')
    result = board.difference(copper)
    if result.is_empty:
        raise ValueError('No clearance area remains inside the board')
    return PlanarRegion.from_geometry(result)


def contour_paths(features: CopperFeatures, mode: str, cancelled: CancelCheck = None) -> tuple[LaserPath, ...]:
    """Select exterior, hole, semantic-feature or explicit-board boundary rings."""
    check_cancelled(cancelled)
    if mode not in CONTOUR_MODES:
        raise ValueError('Unsupported contour mode')
    if mode == 'none':
        return ()
    source = {'trace': features.traces, 'pad': features.pads, 'board': features.board}.get(mode, features.copper)
    if source is None:
        raise ValueError(f'No {mode} geometry available; supply Gerber feature metadata or an explicit board outline')
    paths = []
    for polygon in _polygons(source):
        check_cancelled(cancelled)
        rings = [] if mode == 'inner' else [polygon.exterior]
        if mode != 'outer':
            rings.extend(polygon.interiors)
        for ring in rings:
            check_path_count(len(paths)+1)
            paths.append(LaserPath(tuple(ring.coords), 'contour'))
    return tuple(paths)


def _lines(geometry: BaseGeometry) -> list[LineString]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, LineString):
        return [geometry] if geometry.length > 0 else []
    if isinstance(geometry, (MultiLineString, GeometryCollection)):
        return [line for child in geometry.geoms for line in _lines(child)]
    return []


def _scan_frame(region: PlanarRegion, spacing: float, angle: float) -> tuple[BaseGeometry, int, int, Placement]:
    inverse = Placement(rotation_deg=-angle)
    geometry = inverse.apply_geometry(region.to_geometry())
    _, ymin, _, ymax = geometry.bounds
    low, high = ymin/spacing, ymax/spacing
    if not math.isfinite(low) or not math.isfinite(high):
        raise ValueError('Hatch extent/spacing exceeds numeric range')
    return geometry, math.ceil(low), math.floor(high), inverse.inverse()


def _family_paths(geometry: BaseGeometry, first: int, last: int, spacing: float,
                  restore: Placement, family: int, cancelled: CancelCheck,
                  previous_count: int) -> list[LaserPath]:
    xmin, _, xmax, _ = geometry.bounds
    paths = []
    for index in range(first, last+1):
        check_cancelled(cancelled)
        y = index*spacing
        clipped = geometry.intersection(LineString([(xmin, y), (xmax, y)]))
        segments = sorted((tuple(sorted(line.coords)) for line in _lines(clipped)), key=lambda p: p[0])
        for segment in segments:
            check_path_count(previous_count+len(paths)+1)
            points = restore.apply_points(segment)
            paths.append(LaserPath(points, 'hatch', index, family))
    return paths


def hatch_paths(region: PlanarRegion, spacing_mm: float, angle_deg: float, cross_hatch: bool = False,
                cancelled: CancelCheck = None) -> tuple[LaserPath, ...]:
    """Clip origin-anchored lines, retaining boundary overlaps but omitting point tangencies."""
    options = PlanOptions('none', True, spacing_mm, angle_deg, cross_hatch)
    check_cancelled(cancelled)
    frames = [_scan_frame(region, options.spacing_mm, (options.angle_deg % 360)+90*family)
              for family in range(2 if cross_hatch else 1)]
    count = sum(max(0, last-first+1) for _, first, last, _ in frames)
    if count > MAX_SCAN_LINES:
        raise ValueError(f'Hatch exceeds {MAX_SCAN_LINES} candidate scan lines; increase spacing')
    paths = []
    for family, (geometry, first, last, restore) in enumerate(frames):
        paths.extend(_family_paths(geometry, first, last, options.spacing_mm, restore,
                                   family, cancelled, len(paths)))
    check_cancelled(cancelled)
    return tuple(paths)
