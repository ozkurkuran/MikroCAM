"""Explicit current-geometry selection uses shared physical tool grouping."""
import pytest
from shapely.geometry import Point

from mikrocam.core.geometry_drills import group_geometry_selection, review_geometry_sources


def review():
    return review_geometry_sources((('geometry', [Point(0, 0).buffer(.5, quad_segs=32),
        Point(5, 0).buffer(.504, quad_segs=32), Point(0, 0).buffer(1, quad_segs=32)]),), 'board', 'MM')


def test_selection_order_independent_groups_and_mean():
    result = review()
    tools = group_geometry_selection(result, (1, 0))
    assert tools == group_geometry_selection(result, (0, 1))
    assert len(tools) == 1
    assert tools[0].diameter_mm == pytest.approx(1.004)
    assert len(tools[0].centers_mm) == 2


@pytest.mark.parametrize('indices', [(), [], (True,), (-1,), (3,), (0, 0), ('0',)])
def test_invalid_selection(indices):
    with pytest.raises(ValueError):
        group_geometry_selection(review(), indices)


def test_concentric_alternatives_require_explicit_nonoverlapping_choice():
    result = review()
    assert len(result.candidates) == 3
    with pytest.raises(ValueError, match='overlap'):
        group_geometry_selection(result, (0, 2))
    assert len(group_geometry_selection(result, (2,))) == 1
