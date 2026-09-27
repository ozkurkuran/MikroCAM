"""Shared physical drill records and selected-footprint grouping."""
from dataclasses import FrozenInstanceError

import pytest

from mikrocam.core.drill_groups import DrillHole, DrillTool, group_drill_holes, validate_drill_tools


def test_frozen_hole_and_existing_tool_records():
    hole = DrillHole((1., 2.), .8)
    with pytest.raises(FrozenInstanceError):
        hole.diameter_mm = 1
    assert validate_drill_tools((DrillTool(.8, ((1., 2.),)),)) is None


@pytest.mark.parametrize(('center', 'diameter'), [
    ([1, 2], 1), ((1,), 1), ((True, 2), 1), ((float('nan'), 2), 1),
    ((1e9 + 1, 2), 1), ((1, 2), True), ((1, 2), 0), ((1, 2), -1),
    ((1, 2), float('inf')), ((1, 2), 1e9 + 1), ((1, 2), '1'),
])
def test_hole_rejects_mutable_nonfinite_nonphysical_records(center, diameter):
    with pytest.raises(ValueError):
        DrillHole(center, diameter)


def test_grouping_total_spread_boundary_mean_and_sorted_centers():
    holes = (DrillHole((20., 1.), 1.011), DrillHole((10., 2.), 1.01), DrillHole((0., 3.), 1.))
    tools = group_drill_holes(holes)
    assert tools == (DrillTool(1.005, ((0., 3.), (10., 2.))), DrillTool(1.011, ((20., 1.),)))
    assert group_drill_holes(tuple(reversed(holes))) == tools
    assert holes[0].diameter_mm == 1.011


@pytest.mark.parametrize('holes', [(), [], (object(),), (DrillHole((0., 0.), 1),) * 1001])
def test_grouping_requires_exact_bounded_nonempty_holes(holes):
    with pytest.raises(ValueError):
        group_drill_holes(holes)


@pytest.mark.parametrize('holes', [
    (DrillHole((0., 0.), 1), DrillHole((0., 0.), 2)),
    (DrillHole((0., 0.), 1), DrillHole((.5, 0.), 1)),
    # Original .99 diameter footprints do not overlap, but the grouped mean >.991 does.
    (DrillHole((0., 0.), .99), DrillHole((.991, 0.), .99),
     DrillHole((10., 0.), 1.)),
])
def test_grouped_footprints_reject_coincident_and_overlapping_selection(holes):
    with pytest.raises(ValueError, match='overlap'):
        group_drill_holes(holes)


def test_tangent_footprints_and_inclusive_1000_hole_cap_are_valid():
    tools = group_drill_holes(tuple(DrillHole((float(i), 0.), 1.) for i in range(1000)))
    assert len(tools) == 1 and len(tools[0].centers_mm) == 1000
    assert validate_drill_tools(tools) is None


@pytest.mark.parametrize('tools', [(), [], (object(),),
    (DrillTool(1, ((0, 0),)), DrillTool(2, ((0, 0),))),
    (DrillTool(1, tuple((i * 2, 0) for i in range(1000))), DrillTool(1, ((3000, 0),))),
])
def test_shared_tool_validation_rejects_bad_records_and_total_center_count(tools):
    with pytest.raises(ValueError):
        validate_drill_tools(tools)


def test_validation_preserves_supplied_tool_order_diameters_and_center_order():
    tools = (DrillTool(2., ((20., 0.), (10., 0.))), DrillTool(1., ((0., 0.),)))
    before = repr(tools)
    validate_drill_tools(tools)
    assert repr(tools) == before
