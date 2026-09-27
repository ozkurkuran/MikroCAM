from dataclasses import FrozenInstanceError
from itertools import permutations

import pytest

from mikrocam.core.drill_groups import DrillTool, group_drill_selection
from mikrocam.core.svg_drills import DrillCandidate, DrillReview


def review(*values):
    return DrillReview('board.svg', 'a' * 64, False,
                       tuple(DrillCandidate(center, diameter, f'o{index}', f'p{index}')
                             for index, (diameter, center) in enumerate(values)), ())


@pytest.mark.parametrize('diameter', [True, 0, -1, float('nan'), float('inf'), 1e9 + 1, '1'])
def test_tool_diameter_is_strict_positive_finite(diameter):
    with pytest.raises(ValueError):
        DrillTool(diameter, ((0, 0),))


@pytest.mark.parametrize('centers', [
    [], (), [(0, 0)], ([0, 0],), ((True, 0),), ((0, float('inf')),),
    ((0, 1e9 + 1),), ((0,),), ((0, 0),) * 1001,
])
def test_tool_centers_are_bounded_immutable_finite_pairs(centers):
    with pytest.raises(ValueError):
        DrillTool(1, centers)


def test_tool_is_frozen_and_maximum_valid_count_is_supported():
    tool = DrillTool(1, ((1e9, -1e9),) * 1000)
    with pytest.raises(FrozenInstanceError):
        tool.diameter_mm = 2
    assert len(tool.centers_mm) == 1000


@pytest.mark.parametrize('indices', [(), [], (True,), (0.,), ('0',), (0, 0), (-1,),
                                     (2,), (0,) * 1001])
def test_selection_requires_unique_exact_valid_indices(indices):
    data = review((1, (0, 0)), (2, (1, 1)))
    with pytest.raises(ValueError):
        group_drill_selection(data, indices)


def test_selection_requires_exact_review_record():
    with pytest.raises(ValueError):
        group_drill_selection(None, (0,))


def test_groups_are_independent_of_selection_order_with_sorted_centers_and_means():
    data = review((2, (5, 3)), (1.004, (3, 2)), (1, (-1, 4)), (2.008, (1, 1)))
    expected = (DrillTool(1.002, ((-1, 4), (3, 2))),
                DrillTool(2.004, ((1, 1), (5, 3))))
    for selection in permutations(range(4)):
        assert group_drill_selection(data, selection) == expected


def test_group_spread_is_full_range_not_transitive_neighbor_chaining():
    data = review((1, (0, 0)), (1.009, (10, 0)), (1.018, (20, 0)))
    tools = group_drill_selection(data, (2, 1, 0))
    assert len(tools) == 2
    assert tools[0].diameter_mm == pytest.approx(1.0045)
    assert tools[0].centers_mm == ((0, 0), (10, 0))
    assert tools[1] == DrillTool(1.018, ((20, 0),))


def test_nominal_tolerance_boundary_groups_but_excess_is_separate():
    data = review((1, (0, 0)), (1.01, (10, 0)), (1.010001, (20, 0)))
    tools = group_drill_selection(data, (0, 1, 2))
    assert len(tools) == 2
    assert tools[0].diameter_mm == pytest.approx(1.005)
    assert tools[1].diameter_mm == 1.010001


def test_only_selected_candidates_are_grouped_without_mutating_review():
    data = review((1, (3, 4)), (1.005, (5, 6)), (3, (7, 8)))
    before = data.candidates
    assert group_drill_selection(data, (1,)) == (DrillTool(1.005, ((5, 6),)),)
    assert data.candidates is before


def test_group_mean_cannot_expand_selected_holes_into_an_overlap():
    data = review((1., (0., 0.)), (1., (1.001, 0.)), (1.009, (10., 0.)))
    with pytest.raises(ValueError, match='overlap'):
        group_drill_selection(data, (0, 1, 2))


def test_selection_cannot_publish_duplicate_physical_centres():
    data = review((1., (0., 0.)), (1., (0., 0.)))
    with pytest.raises(ValueError, match='overlap'):
        group_drill_selection(data, (0, 1))
