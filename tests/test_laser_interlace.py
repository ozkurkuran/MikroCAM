"""Ordering preserves exposure geometry and shares placed paths across recipe passes."""
from dataclasses import FrozenInstanceError, replace

import pytest
from shapely.geometry import Polygon

from mikrocam.core.laser_job import LaserJob, LaserPass, LaserRecipe, PlanarRegion
from mikrocam.core.laser_paths import LaserPassPlan, LaserPath, PlanOptions, PlanningCancelled
from mikrocam.core.placement import Placement
from mikrocam.laser.interlace import interlace_paths
from mikrocam.laser.planner import plan_laser


def hatch(index, family=0, offset=0):
    return LaserPath(((offset, index), (offset + 1, index)), 'hatch', index, family)


@pytest.mark.parametrize('n, expected', [
    (1, list(range(9))), (2, [0, 2, 4, 6, 8, 1, 3, 5, 7]),
    (3, [0, 3, 6, 1, 4, 7, 2, 5, 8]),
])
def test_analytic_scan_order_and_geometry_identity(n, expected):
    paths = tuple(hatch(index) for index in range(9))
    ordered = interlace_paths(paths, n)
    assert [path.scan_index for path in ordered] == expected
    assert all(path is paths[index] for path, index in zip(ordered, expected))
    if n == 1:
        assert ordered is paths


def test_contours_negative_indices_clipped_segments_and_cross_families():
    contour_a = LaserPath(((0, 0), (1, 1)), 'contour')
    contour_b = LaserPath(((2, 2), (3, 3)), 'contour')
    paths = (hatch(-1, 1), hatch(-1), contour_a, hatch(-3), hatch(0, 1),
             hatch(-1, offset=4), hatch(-2), contour_b, hatch(2, 1))
    ordered = interlace_paths(paths, 3)
    assert ordered == tuple(paths[i] for i in (2, 7, 3, 6, 1, 5, 4, 0, 8))
    assert all(any(path is original for original in paths) for path in ordered)
    assert interlace_paths(paths, 1) is paths


def test_large_n_orders_only_occupied_residues():
    paths = (hatch(-1), hatch(1_000_000), hatch(2), hatch(0))
    assert interlace_paths(paths, 1_000_000) == tuple(paths[i] for i in (3, 1, 2, 0))


@pytest.mark.parametrize('n', [True, False, 0, -1, 1.0, '2', None, 1_000_001])
def test_strict_interlace_validation_in_options_and_domain(n):
    with pytest.raises(ValueError, match='[Ii]nterlace'):
        PlanOptions(interlace_n=n)
    with pytest.raises(ValueError, match='[Ii]nterlace'):
        interlace_paths((hatch(0),), n)


@pytest.mark.parametrize('n', [1, 1_000_000])
def test_interlace_boundaries_and_old_positional_options(n):
    assert PlanOptions(interlace_n=n).interlace_n == n
    assert PlanOptions('none', True, .02, -450, True, 'clearance').interlace_n == 1


@pytest.mark.parametrize('stop_at', [1, 3, 7])
def test_cancellation_before_during_and_after_collecting(stop_at):
    calls = 0

    def cancelled():
        nonlocal calls
        calls += 1
        return calls >= stop_at

    with pytest.raises(PlanningCancelled):
        interlace_paths(tuple(hatch(i) for i in range(5)), 3, cancelled)


def test_n1_also_honors_cancellation():
    with pytest.raises(PlanningCancelled):
        interlace_paths((hatch(0),), 1, lambda: True)


@pytest.mark.parametrize('paths', [[hatch(0)], ('bad',)])
def test_ordering_rejects_non_tuple_or_untyped_paths(paths):
    with pytest.raises(ValueError):
        interlace_paths(paths, 2)


def source_job():
    polygon = Polygon([(0, 0), (6, 0), (6, 6), (0, 6)],
                      holes=[[(2, 2), (4, 2), (4, 4), (2, 4)]])
    passes = (LaserPass('rough', 30, 100, 20, 80), LaserPass('finish', 15, 250, 40, 60))
    return LaserJob('hole', PlanarRegion.from_geometry(polygon), LaserRecipe('two', passes))


def test_hole_clipped_planner_order_before_single_placement_and_shared_passes():
    original = source_job()
    options = PlanOptions(hatch=True, cross_hatch=True, spacing_mm=1)
    source = plan_laser(original, options)
    expected = interlace_paths(source.paths, 3)
    placement = Placement(origin=(1, 2), translation=(100, 200), rotation_deg=37, mirror_x=True)
    placed = plan_laser(replace(original, placement=placement), replace(options, interlace_n=3))
    assert [(p.role, p.scan_index, p.hatch_family) for p in placed.paths] == [
        (p.role, p.scan_index, p.hatch_family) for p in expected]
    assert [p.points for p in placed.paths] == [placement.apply_points(p.points) for p in expected]
    assert placed.job.region == original.region
    pass_plans = placed.pass_plans
    assert len(pass_plans) == 2
    for pass_plan, settings in zip(pass_plans, original.recipe.passes):
        assert pass_plan.settings is settings
        assert pass_plan.paths is placed.paths
    assert pass_plans[0].paths is pass_plans[1].paths
    assert [(p.settings.power_percent, p.settings.speed_mm_s,
             p.settings.frequency_khz, p.settings.pulse_width_ns) for p in pass_plans] == [
        (30, 100, 20, 80), (15, 250, 40, 60)]
    with pytest.raises(FrozenInstanceError):
        pass_plans[0].settings = original.recipe.passes[1]


def test_planner_interlaces_once_for_multiple_passes_before_placement(monkeypatch):
    import mikrocam.laser.planner as planner

    original = source_job()
    placement = Placement(translation=(100, 200))
    calls = []

    def observed(paths, n, cancelled):
        calls.append((paths, n))
        assert max(point[0] for path in paths for point in path.points) <= 6
        return interlace_paths(paths, n, cancelled)

    monkeypatch.setattr(planner, 'interlace_paths', observed)
    result = planner.plan_laser(replace(original, placement=placement),
                               PlanOptions(hatch=True, interlace_n=3))
    assert len(calls) == 1 and calls[0][1] == 3
    assert min(point[0] for path in result.paths for point in path.points) >= 100
    assert len(result.pass_plans) == 2


@pytest.mark.parametrize('settings, paths', [
    (None, (hatch(0),)), ('bad', (hatch(0),)),
    (LaserPass('one', 30, 100, 20, 80), []),
    (LaserPass('one', 30, 100, 20, 80), ()),
    (LaserPass('one', 30, 100, 20, 80), ('bad',)),
])
def test_pass_plan_requires_valid_settings_and_nonempty_typed_tuple(settings, paths):
    with pytest.raises(ValueError):
        LaserPassPlan(settings, paths)
