"""Strict physical drill/slot records and analytic capsule-footprint checks."""
from dataclasses import FrozenInstanceError

import pytest

from mikrocam.core.excellon_tools import ExcellonTool, operation_distance, validate_excellon_tools


def test_frozen_mixed_and_slot_only_tool_records():
    mixed = ExcellonTool(1., ((0., 0.),), (((10., 0.), (15., 0.)),))
    with pytest.raises(FrozenInstanceError):
        mixed.diameter_mm = 2
    assert validate_excellon_tools((mixed,)) is None
    assert validate_excellon_tools((ExcellonTool(1., (), (((0., 0.), (10., 0.)),)),)) is None


@pytest.mark.parametrize(('diameter', 'drills', 'slots'), [
    (True, ((0, 0),), ()), (0, ((0, 0),), ()), (-1, ((0, 0),), ()),
    (float('nan'), ((0, 0),), ()), (float('inf'), ((0, 0),), ()), (1e9+1, ((0, 0),), ()),
    (1, [], ()), (1, (), []), (1, (), ()), (1, ([0, 0],), ()),
    (1, ((0, True),), ()), (1, ((0, float('nan')),), ()), (1, ((0, 1e9+1),), ()),
    (1, (), (((0, 0),),)), (1, (), (([0, 0], (1, 1)),)),
    (1, (), (((0, 0), (0, 0)),)), (1, (), (((0, 0), (1, float('inf'))),)),
    (1, tuple((i * 2, 0) for i in range(1001)), ()),
    (1, tuple((i * 2, 0) for i in range(1000)), (((3000, 0), (3001, 0)),)),
])
def test_invalid_tool_records_reject_mutability_bounds_and_degenerate_slots(diameter, drills, slots):
    with pytest.raises(ValueError):
        ExcellonTool(diameter, drills, slots)


@pytest.mark.parametrize(('first', 'second', 'expected'), [
    (((0, 0), None), ((3, 4), None), 5),
    (((0, 0), (10, 0)), ((3, 4), None), 4),
    (((0, 0), (10, 0)), ((13, 4), None), 5),
    (((0, 0), (10, 0)), ((0, 3), (10, 3)), 3),
    (((0, 0), (10, 0)), ((5, -2), (5, 2)), 0),
    (((0, 0), (10, 0)), ((10, 0), (20, 0)), 0),
    (((0, 0), (10, 0)), ((13, 4), (15, 4)), 5),
])
def test_operation_distance_is_analytic_and_symmetric(first, second, expected):
    assert operation_distance(*first, *second) == pytest.approx(expected)
    assert operation_distance(*second, *first) == pytest.approx(expected)


@pytest.mark.parametrize('args', [
    ([0, 0], None, (1, 1), None), ((0, 0), (0, 0), (1, 1), None),
    ((0, 0), None, (1, True), None), ((0, 0), None, (1, float('nan')), None),
    ((0, 0), None, (1, 1), []),
])
def test_operation_distance_checks_records_before_geometry(args):
    with pytest.raises(ValueError):
        operation_distance(*args)


@pytest.mark.parametrize('tools', [
    (ExcellonTool(1, ((0, 0),), ()), ExcellonTool(2, ((0, 0),), ())),
    (ExcellonTool(1, ((0, .99),), ()), ExcellonTool(1, (), (((-2, 0), (2, 0)),))),
    (ExcellonTool(1, (), (((0, 0), (10, 0)), ((5, -2), (5, 2)))),),
    (ExcellonTool(1, (), (((0, 0), (10, 0)), ((0, .99), (10, .99)))),),
    (ExcellonTool(1, (), (((0, 0), (10, 0)), ((10, 0), (0, 0)))),),
])
def test_final_tool_validation_rejects_overlapping_capsules(tools):
    with pytest.raises(ValueError, match='overlap'):
        validate_excellon_tools(tools)


@pytest.mark.parametrize('tools', [
    (ExcellonTool(1, ((0, 1),), ()), ExcellonTool(1, (), (((-2, 0), (2, 0)),))),
    (ExcellonTool(1, (), (((0, 0), (10, 0)), ((0, 1), (10, 1)))),),
    (ExcellonTool(1, (), (((0, 0), (10, 0)), ((11, 0), (20, 0)))),),
])
def test_exact_tangent_capsules_are_allowed_without_buffer_tessellation(tools):
    assert validate_excellon_tools(tools) is None


@pytest.mark.parametrize('tools', [(), [], (object(),),
    (ExcellonTool(1, tuple((i * 2, 0) for i in range(1000)), ()), ExcellonTool(1, ((3000, 0),), ())),
])
def test_final_validation_requires_exact_bounded_nonempty_inventory(tools):
    with pytest.raises(ValueError):
        validate_excellon_tools(tools)


def test_conflicting_record_can_be_retained_for_review_without_repair():
    tool = ExcellonTool(1, ((0, 0), (0, 0)), ())
    assert tool.drills_mm == ((0, 0), (0, 0))
    with pytest.raises(ValueError):
        validate_excellon_tools((tool,))
