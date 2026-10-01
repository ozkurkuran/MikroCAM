"""Independent work/machine-frame route and immutable partial-map invariants."""
from dataclasses import FrozenInstanceError, replace
import math
import pytest

from mikrocam.core.probe_map import ProbeGrid, ProbePlan, ProbeMap, uniform_grid


def plan(**changes):
    values = dict(grid=uniform_grid(0, 4, 3, 1, 3, 2), safe_z_mm=5, min_z_mm=-2,
                  probe_feed_mm_min=40, travel_feed_mm_min=200,
                  machine_min_mm=(-10, -10, -10), machine_max_mm=(20, 20, 20),
                  initial_machine_mm=(1, 2, 3), g54_offset_mm=(1, 2, 1))
    return ProbePlan(**(values | changes))


def test_uniform_grid_exact_row_major_endpoints_and_count():
    grid = uniform_grid(-1, 3, 3, 4, 6, 2)
    assert grid.x_mm == (-1., 1., 3.) and grid.y_mm == (4., 6.)
    assert grid.points == ((-1., 4.), (1., 4.), (3., 4.), (-1., 6.), (1., 6.), (3., 6.))
    assert grid.count == 6
    assert uniform_grid(-.3, .7, 4, -.2, .8, 3).points[-1] == (.7, .8)
    with pytest.raises(FrozenInstanceError):
        grid.x_mm = (0., 1.)


@pytest.mark.parametrize('axis', [(), (0,), tuple(range(65)), (1, 1), (2, 1),
                                (False, 1), ('0', 1), (0, math.inf), (0, math.nan),
                                (-1000001, 0), (0, 1000001), [0, 1]])
def test_grid_rejects_invalid_axes(axis):
    with pytest.raises(ValueError):
        ProbeGrid(axis, (0, 1))
    with pytest.raises(ValueError):
        ProbeGrid((0, 1), axis)


def test_grid_product_limit_allows_1024_and_rejects_more():
    assert ProbeGrid(tuple(range(32)), tuple(range(32))).count == 1024
    with pytest.raises(ValueError):
        ProbeGrid(tuple(range(64)), tuple(range(17)))


@pytest.mark.parametrize('values', [(0, 1, True, 0, 1, 2), (0, 1, 2.0, 0, 1, 2),
                                  (1, 0, 2, 0, 1, 2), (0, 0, 2, 0, 1, 2),
                                  (0, 1, 1000000, 0, 1, 2), (0, 1, 64, 0, 1, 17),
                                  (0, math.inf, 2, 0, 1, 2)])
def test_uniform_grid_validates_before_constructing_unbounded_points(values):
    with pytest.raises(ValueError):
        uniform_grid(*values)


def test_plan_machine_endpoints_use_offset_once_and_upward_initial_route():
    value = plan()
    assert value.timeout_seconds == 30
    assert value.safe_z_mm + value.g54_offset_mm[2] == 6 >= value.initial_machine_mm[2]
    assert max(x + value.g54_offset_mm[0] for x, _ in value.grid.points) == 5
    assert plan(machine_min_mm=(1, 2, -1), machine_max_mm=(5, 5, 6))
    with pytest.raises(FrozenInstanceError):
        value.safe_z_mm = 7


@pytest.mark.parametrize('changes', [
    {'grid': None}, {'safe_z_mm': True}, {'safe_z_mm': math.inf},
    {'min_z_mm': 5}, {'min_z_mm': -96}, {'min_z_mm': '0'},
    {'safe_z_mm': 1}, {'machine_min_mm': (1, 2)},
    {'machine_min_mm': [0, 0, 0]}, {'machine_min_mm': (20, -10, -10)},
    {'machine_max_mm': (20, 20, False)}, {'machine_max_mm': (20, 20, 1000001)},
    {'initial_machine_mm': (0, 0, 21)}, {'initial_machine_mm': (0, 0, math.nan)},
    {'g54_offset_mm': (20, 0, 0)}, {'g54_offset_mm': (0, 20, 0)},
    {'g54_offset_mm': (0, 0, 19)}, {'g54_offset_mm': (0, 0, -10)},
    {'probe_feed_mm_min': 0}, {'probe_feed_mm_min': .009},
    {'probe_feed_mm_min': 10001}, {'travel_feed_mm_min': False},
    {'travel_feed_mm_min': -1}, {'timeout_seconds': 2.99},
    {'timeout_seconds': 301}, {'timeout_seconds': '30'},
])
def test_plan_refuses_invalid_envelope_or_route(changes):
    with pytest.raises(ValueError):
        plan(**changes)


def test_exact_plan_limits_and_negative_work_z_are_supported():
    assert plan(probe_feed_mm_min=.01, travel_feed_mm_min=10000, timeout_seconds=3)
    assert plan(timeout_seconds=300, min_z_mm=-95, machine_min_mm=(-10, -10, -100))
    assert plan(safe_z_mm=-1, min_z_mm=-2, g54_offset_mm=(1, 2, 5))


def test_partial_and_failed_final_retract_maps_are_truthful():
    grid = ProbeGrid((0, 1), (0, 1))
    partial = ProbeMap(grid, (.125, -.25, None, None), (1, 2, 3), 'failed', 'measured')
    assert partial.completed == 2 and not partial.complete
    complete = replace(partial, heights_mm=(.125, -.25, .3, .7), outcome='complete')
    assert complete.completed == 4 and complete.complete
    final_failure = replace(complete, outcome='failed')
    assert final_failure.completed == 4 and not final_failure.complete
    assert replace(partial, heights_mm=(None,) * 4, outcome='aborted', origin='simulated').completed == 0
    with pytest.raises(FrozenInstanceError):
        partial.outcome = 'complete'


def test_active_incomplete_outcome_remains_preterminal_with_all_heights():
    grid = ProbeGrid((0, 1), (0, 1))
    progress = ProbeMap(grid, (.1, None, None, None), (0, 0, 0), 'incomplete', 'measured')
    assert progress.completed == 1 and not progress.complete
    sampled = replace(progress, heights_mm=(.1, .2, .3, .4))
    assert sampled.completed == 4 and sampled.outcome == 'incomplete' and not sampled.complete
    assert replace(sampled, outcome='complete').complete


@pytest.mark.parametrize('heights,outcome', [((1, None, 2, None), 'failed'),
                                          ((None, None, None, None), 'complete'),
                                          ((1, 2, 3), 'failed'), ([1, 2, 3, 4], 'complete'),
                                          ((True, 2, 3, 4), 'complete'),
                                          (('1', 2, 3, 4), 'complete'),
                                          ((math.nan, 2, 3, 4), 'complete'),
                                          ((math.inf, 2, 3, 4), 'complete'),
                                          ((1000001, 2, 3, 4), 'complete')])
def test_maps_reject_nonprefix_missing_or_invalid_heights(heights, outcome):
    with pytest.raises(ValueError):
        ProbeMap(ProbeGrid((0, 1), (0, 1)), heights, (0, 0, 0), outcome, 'measured')


@pytest.mark.parametrize('field,value', [('grid', None), ('g54_offset_mm', [0, 0, 0]),
                                       ('g54_offset_mm', (0, 0, False)),
                                       ('outcome', 'pending'), ('origin', 'imported')])
def test_map_rejects_unsupported_record_fields(field, value):
    values = dict(grid=ProbeGrid((0, 1), (0, 1)), heights_mm=(1, 2, 3, 4),
                  g54_offset_mm=(0, 0, 0), outcome='complete', origin='simulated')
    with pytest.raises(ValueError):
        ProbeMap(**(values | {field: value}))
