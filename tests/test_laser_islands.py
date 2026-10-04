"""Island (tile) hatch: validation, origin-anchored grid, exact coverage and ordering."""
from dataclasses import replace
import math

import pytest
from shapely import union_all
from shapely.geometry import LineString, MultiLineString, Polygon, box

from mikrocam.core.laser_geometry import hatch_paths
from mikrocam.core.laser_job import LaserJob, LaserPass, LaserRecipe, PlanarRegion
from mikrocam.core.laser_paths import IslandSettings, PlanOptions, PlanningCancelled
from mikrocam.core.placement import Placement
from mikrocam.laser.planner import plan_laser


def region(geometry=None):
    return PlanarRegion.from_geometry(box(0, 0, 10, 10) if geometry is None else geometry)


def tiles(area=None, spacing=0.5, angle=0.0, cross=False, **island):
    from mikrocam.core.laser_islands import island_hatch_paths
    values = {'tile_size_mm': 5.0}
    values.update(island)
    return island_hatch_paths(region(area), spacing, angle, cross, IslandSettings(**values))


def lines(paths):
    return MultiLineString([path.points for path in paths])


def job(area=None):
    recipe = LaserRecipe('explicit', (LaserPass('one', 30, 100, 20, 80),))
    return LaserJob('board', region(area), recipe)


@pytest.mark.parametrize('kwargs', [
    {'tile_size_mm': 0}, {'tile_size_mm': -1}, {'tile_size_mm': float('inf')},
    {'tile_size_mm': True}, {'tile_size_mm': '5'},
    {'tile_size_mm': 5, 'overlap_mm': -0.1}, {'tile_size_mm': 5, 'overlap_mm': 5},
    {'tile_size_mm': 5, 'overlap_mm': float('nan')},
    {'tile_size_mm': 5, 'angle_step_deg': float('inf')},
    {'tile_size_mm': 5, 'order': 'random'}, {'tile_size_mm': 5, 'order': None},
])
def test_invalid_island_settings_are_rejected(kwargs):
    with pytest.raises(ValueError):
        IslandSettings(**kwargs)


def test_island_settings_normalize_and_defaults_are_geometric_only():
    value = IslandSettings(5)
    assert (value.tile_size_mm, value.overlap_mm, value.angle_step_deg, value.order) == (5.0, 0.0, 90.0, 'checkerboard')
    assert type(value.tile_size_mm) is float


def test_plan_options_require_hatch_and_tile_not_smaller_than_spacing():
    island = IslandSettings(2)
    assert PlanOptions(hatch=True, spacing_mm=0.5, island=island).island == island
    assert PlanOptions().island is None
    with pytest.raises(ValueError, match='[Hh]atch'):
        PlanOptions(island=island)
    with pytest.raises(ValueError, match='spacing'):
        PlanOptions(hatch=True, spacing_mm=3, island=island)
    with pytest.raises(ValueError):
        PlanOptions(hatch=True, island={'tile_size_mm': 2})


def test_grid_is_origin_anchored_and_tiles_never_leave_their_cells():
    result = tiles(box(1, 1, 9, 9))
    assert sorted((tile.column, tile.row) for tile in result) == [(0, 0), (0, 1), (1, 0), (1, 1)]
    for tile in result:
        cell = box(tile.column * 5, tile.row * 5, (tile.column + 1) * 5, (tile.row + 1) * 5)
        assert tile.paths and all(path.role == 'hatch' for path in tile.paths)
        assert cell.buffer(1e-9).covers(lines(tile.paths))
        assert box(1, 1, 9, 9).buffer(1e-9).covers(lines(tile.paths))


def test_negative_coordinates_use_floor_cells_and_parity():
    result = tiles(box(-4.5, -4.5, 4.5, 4.5), spacing=1)
    assert sorted((tile.column, tile.row) for tile in result) == [(-1, -1), (-1, 0), (0, -1), (0, 0)]
    assert {(tile.column, tile.row): tile.parity for tile in result} == {
        (-1, -1): 0, (-1, 0): 1, (0, -1): 1, (0, 0): 0}


def test_checkerboard_order_rotation_and_no_consecutive_edge_neighbours():
    result = tiles(box(0.2, 0.2, 19.8, 14.8), spacing=1, angle=10, angle_step_deg=90)
    order = [(tile.column, tile.row) for tile in result]
    even = [cell for cell in order if sum(cell) % 2 == 0]
    odd = [cell for cell in order if sum(cell) % 2 == 1]
    assert order == even + odd
    assert even == sorted(even, key=lambda cell: (cell[1], cell[0]))
    assert odd == sorted(odd, key=lambda cell: (cell[1], cell[0]))
    for first, second in zip(order, order[1:]):
        if sum(first) % 2 == sum(second) % 2:
            assert abs(first[0] - second[0]) + abs(first[1] - second[1]) != 1
    assert {tile.parity: tile.angle_deg for tile in result} == {0: 10.0, 1: 100.0}
    for tile in result:
        x0, y0 = tile.paths[0].points
        direction = math.degrees(math.atan2(y0[1] - x0[1], y0[0] - x0[0])) % 180
        assert direction == pytest.approx(tile.angle_deg % 180, abs=1e-6)


def test_raster_order_is_row_major():
    result = tiles(box(0.2, 0.2, 14.8, 9.8), spacing=1, order='raster')
    assert [(tile.column, tile.row) for tile in result] == [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)]


def scan_intervals(paths, angle):
    """Merge each scan line's exposure as 1-D intervals along its family direction."""
    grouped = {}
    for path in paths:
        if LineString(path.points).length <= 1e-9:
            continue  # floating-point corner tangency artefact of ordinary hatch, not exposure
        theta = math.radians(angle + 90 * path.hatch_family)
        u = (math.cos(theta), math.sin(theta))
        values = sorted(x * u[0] + y * u[1] for x, y in path.points)
        grouped.setdefault((path.hatch_family, path.scan_index), []).append((values[0], values[-1]))
    merged, total = {}, 0.0
    for key, spans in grouped.items():
        spans.sort()
        result = [list(spans[0])]
        for low, high in spans[1:]:
            if low <= result[-1][1] + 1e-7:
                result[-1][1] = max(result[-1][1], high)
            else:
                result.append([low, high])
        merged[key] = result
        total += sum(high - low for low, high in spans)
    return merged, total


@pytest.mark.parametrize('angle', [0, 30, 90, 137.5])
@pytest.mark.parametrize('area', [box(0, 0, 10, 10), box(0.3, -1.7, 12.9, 7.1),
                                  Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], [[(3, 3), (7, 3), (7, 7), (3, 7)]])])
def test_zero_step_zero_overlap_union_equals_plain_hatch_without_duplicates(angle, area):
    plain = hatch_paths(region(area), 0.5, angle, cross_hatch=True)
    island = [path for tile in tiles(area, 0.5, angle, True, angle_step_deg=0) for path in tile.paths]
    plain_spans, plain_total = scan_intervals(plain, angle)
    island_spans, island_total = scan_intervals(island, angle)
    assert plain_spans.keys() == island_spans.keys()
    for key, spans in plain_spans.items():
        assert len(island_spans[key]) == len(spans)
        for (low, high), (other_low, other_high) in zip(spans, island_spans[key]):
            assert other_low == pytest.approx(low, abs=1e-7) and other_high == pytest.approx(high, abs=1e-7)
    assert island_total == pytest.approx(plain_total, abs=1e-6)


def test_boundary_line_on_shared_tile_edge_is_kept_exactly_once():
    result = tiles(box(0, 0, 10, 10), spacing=0.5, angle=0, angle_step_deg=0)
    on_edge = [path for tile in result for path in tile.paths if {y for _, y in path.points} == {5.0}]
    assert sum(LineString(path.points).length for path in on_edge) == pytest.approx(10)
    top = [path for tile in result for path in tile.paths if {y for _, y in path.points} == {10.0}]
    assert sum(LineString(path.points).length for path in top) == pytest.approx(10)


@pytest.mark.parametrize('angle,step', [(0, 90), (15, 45), (45, 90)])
def test_rotated_tiles_cover_region_within_hatch_spacing(angle, step):
    area = Polygon([(0, 0), (17, 0), (17, 11), (0, 11)], [[(4, 4), (8, 4), (8, 8), (4, 8)]])
    result = tiles(area, 0.4, angle, angle_step_deg=step, tile_size_mm=3)
    exposure = lines([path for tile in result for path in tile.paths])
    assert area.buffer(1e-9).covers(exposure)
    assert exposure.buffer(0.4 * 1.0001).covers(area)


def test_overlap_expands_each_tile_by_half_on_every_side():
    plain = tiles(box(0, 0, 10, 10), 0.5, angle_step_deg=0)
    overlap = tiles(box(0, 0, 10, 10), 0.5, angle_step_deg=0, overlap_mm=1.0)
    length = lambda result: sum(LineString(p.points).length for t in result for p in t.paths)
    assert length(overlap) > length(plain)
    for tile in overlap:
        cell = box(tile.column * 5 - 0.5, tile.row * 5 - 0.5, (tile.column + 1) * 5 + 0.5, (tile.row + 1) * 5 + 0.5)
        assert cell.buffer(1e-9).covers(lines(tile.paths))
    first = next(t for t in overlap if (t.column, t.row) == (0, 0))
    assert max(x for p in first.paths for x, _ in p.points) == pytest.approx(5.5)


def test_tile_and_scan_limits_and_cancellation():
    from mikrocam.core.laser_islands import MAX_ISLAND_TILES
    with pytest.raises(ValueError, match='tiles'):
        tiles(box(0, 0, 1000, 1000), spacing=0.5, tile_size_mm=1)
    assert MAX_ISLAND_TILES == 10_000
    with pytest.raises(ValueError, match='scan lines'):
        tiles(box(0, 0, 200, 200), spacing=0.003, tile_size_mm=100)
    from mikrocam.core.laser_islands import island_hatch_paths
    with pytest.raises(PlanningCancelled):
        island_hatch_paths(region(), 0.5, 0, False, IslandSettings(5), cancelled=lambda: True)


def test_islands_are_deterministic_and_skip_empty_cells():
    area = union_all([box(0, 0, 4, 4), box(11, 11, 14, 14)])
    first, second = tiles(area, 0.5), tiles(area, 0.5)
    assert first == second
    assert [(tile.column, tile.row) for tile in first] == [(0, 0), (2, 2)]


def test_planner_contours_first_then_tiles_in_order_with_interlace_inside_each_tile():
    island = IslandSettings(5, angle_step_deg=90)
    options = PlanOptions(contour_mode='outer', hatch=True, spacing_mm=1, interlace_n=2, island=island)
    plan = plan_laser(job(), options)
    assert plan.paths[0].role == 'contour' and all(p.role == 'hatch' for p in plan.paths[1:])
    from mikrocam.core.laser_islands import island_hatch_paths
    from mikrocam.laser.interlace import interlace_paths
    expected = [path for tile in island_hatch_paths(job().region, 1, 0, False, island)
                for path in interlace_paths(tile.paths, 2)]
    assert list(plan.paths[1:]) == expected
    assert plan == plan_laser(job(), options)
    assert plan_laser(job(), replace(options, island=None)).paths != plan.paths


def test_planner_places_island_paths_once_and_keeps_source():
    options = PlanOptions(contour_mode='none', hatch=True, spacing_mm=1, island=IslandSettings(5))
    placement = Placement(origin=(1, 2), translation=(50, 60), rotation_deg=33, mirror_x=True)
    source = plan_laser(job(), options)
    placed = plan_laser(replace(job(), placement=placement), options)
    assert [p.points for p in placed.paths] == [placement.apply_points(p.points) for p in source.paths]
    with pytest.raises(PlanningCancelled):
        plan_laser(job(), options, cancelled=lambda: True)
