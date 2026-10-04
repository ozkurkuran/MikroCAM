"""Deterministic island (tile) hatch with checkerboard ordering in source millimetres.

Tiles are origin-anchored half-open squares ``[c*T, (c+1)*T) x [r*T, (r+1)*T)``, each
expanded by half the configured overlap. Every tile clips the same origin-anchored scan
lines as ordinary hatch, first to the region and then to its closed cell; a segment
lying entirely on the cell's top or right edge belongs to the neighbouring tile.
"""
from dataclasses import dataclass
import math

from shapely import get_parts, union_all
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.base import BaseGeometry

from .laser_geometry import _lines
from .laser_job import PlanarRegion
from .laser_paths import (MAX_SCAN_LINES, CancelCheck, IslandSettings, LaserPath, PlanOptions,
                          check_cancelled, check_path_count)
from .placement import Placement


MAX_ISLAND_TILES = 10_000
EDGE_TOLERANCE_MM = 1e-9


@dataclass(frozen=True)
class IslandTile:
    """One occupied grid cell, its hatch angle and exposure segments in scan order."""
    column: int
    row: int
    angle_deg: float
    paths: tuple[LaserPath, ...]

    @property
    def parity(self) -> int:
        """Checkerboard colour: 0 for even ``column + row``, otherwise 1."""
        return (self.column + self.row) % 2


def tile_cells(bounds: tuple[float, float, float, float],
               island: IslandSettings) -> list[tuple[int, int]]:
    """Return candidate ``(column, row)`` cells covering bounds, in scan order."""
    xmin, ymin, xmax, ymax = bounds
    size, half = island.tile_size_mm, island.overlap_mm / 2
    spans = []
    for low, high in ((xmin, xmax), (ymin, ymax)):
        first, last = (low - half) / size, (high + half) / size
        if not math.isfinite(first) or not math.isfinite(last):
            raise ValueError('Island tile extent exceeds numeric range')
        spans.append(range(math.floor(first), math.floor(last) + 1))
    columns, rows = spans
    if len(columns) * len(rows) > MAX_ISLAND_TILES:
        raise ValueError(f'Island tiling exceeds {MAX_ISLAND_TILES} candidate tiles; increase tile size')
    cells = [(column, row) for row in rows for column in columns]
    if island.order == 'checkerboard':
        cells.sort(key=lambda cell: (cell[0] + cell[1]) % 2)
    return cells


def _cell_bounds(column: int, row: int, island: IslandSettings) -> tuple[float, float, float, float]:
    size, half = island.tile_size_mm, island.overlap_mm / 2
    return column * size - half, row * size - half, (column + 1) * size + half, (row + 1) * size + half


def _polygonal(geometry: BaseGeometry) -> BaseGeometry:
    parts = [part for part in get_parts(get_parts(geometry)) if part.geom_type == 'Polygon' and not part.is_empty]
    return union_all(parts) if parts else Polygon()


def _on_upper_edge(points: tuple[tuple[float, float], ...],
                   cell: tuple[float, float, float, float]) -> bool:
    _, _, x1, y1 = cell
    return (all(abs(y - y1) <= EDGE_TOLERANCE_MM for _, y in points)
            or all(abs(x - x1) <= EDGE_TOLERANCE_MM for x, _ in points))


def _frame(window: BaseGeometry, cell: tuple[float, float, float, float], spacing: float,
           rotation: float) -> tuple[BaseGeometry, BaseGeometry, int, int, Placement]:
    inverse = Placement(rotation_deg=-rotation)
    rotated = inverse.apply_geometry(window)
    rotated_cell = inverse.apply_geometry(box(*cell))
    low = max(rotated.bounds[1], rotated_cell.bounds[1]) / spacing
    high = min(rotated.bounds[3], rotated_cell.bounds[3]) / spacing
    if not math.isfinite(low) or not math.isfinite(high):
        raise ValueError('Hatch extent/spacing exceeds numeric range')
    return rotated, rotated_cell, math.ceil(low), math.floor(high), inverse.inverse()


def _tile_family(frame: tuple, cell: tuple[float, float, float, float], spacing: float,
                 family: int, cancelled: CancelCheck, previous: int) -> list[LaserPath]:
    rotated, rotated_cell, first, last, restore = frame
    xmin, _, xmax, _ = rotated.bounds
    paths = []
    for index in range(first, last + 1):
        check_cancelled(cancelled)
        y = index * spacing
        clipped = rotated.intersection(LineString([(xmin, y), (xmax, y)]))
        pieces = [piece for line in _lines(clipped) for piece in _lines(line.intersection(rotated_cell))]
        for segment in sorted(tuple(sorted(piece.coords)) for piece in pieces):
            points = restore.apply_points(segment)
            if _on_upper_edge(points, cell) or LineString(points).length <= EDGE_TOLERANCE_MM:
                continue
            check_path_count(previous + len(paths) + 1)
            paths.append(LaserPath(points, 'hatch', index, family))
    return paths


def _planned_tiles(geometry: BaseGeometry, options: PlanOptions,
                   cancelled: CancelCheck) -> list[tuple[int, int, float, tuple, list]]:
    island, spacing = options.island, options.spacing_mm
    planned, lines = [], 0
    for column, row in tile_cells(geometry.bounds, island):
        check_cancelled(cancelled)
        cell = _cell_bounds(column, row, island)
        window = _polygonal(geometry.intersection(box(cell[0] - spacing, cell[1] - spacing,
                                                      cell[2] + spacing, cell[3] + spacing)))
        if window.is_empty:
            continue
        angle = options.angle_deg + island.angle_step_deg * ((column + row) % 2)
        frames = [_frame(window, cell, spacing, (angle % 360) + 90 * family)
                  for family in range(2 if options.cross_hatch else 1)]
        lines += sum(max(0, frame[3] - frame[2] + 1) for frame in frames)
        if lines > MAX_SCAN_LINES:
            raise ValueError(f'Hatch exceeds {MAX_SCAN_LINES} candidate scan lines; increase spacing')
        planned.append((column, row, angle, cell, frames))
    return planned


def island_hatch_paths(region: PlanarRegion, spacing_mm: float, angle_deg: float,
                       cross_hatch: bool, island: IslandSettings,
                       cancelled: CancelCheck = None) -> tuple[IslandTile, ...]:
    """Return occupied tiles in scan order; empty cells are omitted."""
    options = PlanOptions('none', True, spacing_mm, angle_deg, cross_hatch, island=island)
    if not isinstance(region, PlanarRegion):
        raise ValueError('Island hatch requires a PlanarRegion')
    check_cancelled(cancelled)
    tiles, count = [], 0
    for column, row, angle, cell, frames in _planned_tiles(region.to_geometry(), options, cancelled):
        paths = []
        for family, frame in enumerate(frames):
            paths.extend(_tile_family(frame, cell, options.spacing_mm, family, cancelled, count + len(paths)))
        if paths:
            count += len(paths)
            tiles.append(IslandTile(column, row, angle, tuple(paths)))
    check_cancelled(cancelled)
    return tuple(tiles)
