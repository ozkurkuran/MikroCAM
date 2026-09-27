"""Exact operation preservation, source maps and analytic physical conflicts."""
from dataclasses import replace

import pytest

from mikrocam.core.excellon_tools import ExcellonTool
from mikrocam.core.excellon_merge_models import MergeSource, MergeSourceTool
from mikrocam.core.excellon_merge import review_excellon_merge


def source(name, *tools, units='MM'):
    return MergeSource(name, units, 'a'*64,
        tuple(MergeSourceTool(f'int:{i}', tool) for i, tool in enumerate(tools, 1)))


def holes(diameter, *centers):
    return ExcellonTool(diameter, tuple(centers), ())


def slots(diameter, *endpoints):
    return ExcellonTool(diameter, (), tuple(endpoints))


def test_exact_diameter_groups_preserve_positions_and_rebuild_source_map():
    a = source('a', holes(2, (0, 0)), holes(1, (5, 0)))
    b = source('b', holes(2, (10, 0)), holes(1.000001, (15, 0)), units='IN')
    result = review_excellon_merge((a, b))
    assert [t.diameter_mm for t in result.tools] == [1, 1.000001, 2]
    assert result.tools[2].drills_mm == ((0, 0), (10, 0))
    assert [(m.source_name,m.source_tool,m.output_tool) for m in result.tool_map] == [
        ('a','int:1',3), ('a','int:2',1), ('b','int:1',3), ('b','int:2',2)]
    assert not result.duplicates and not result.conflicts and result.conflict_count == 0
    assert result == review_excellon_merge((a,b))


def test_exact_duplicate_holes_and_reversed_slots_keep_first_orientation():
    slot = ((10, 0), (5, 0))
    a = source('a', ExcellonTool(1, ((0,0),), (slot,)))
    b = source('b', ExcellonTool(1, ((0,0),), (slot[::-1],)))
    result = review_excellon_merge((a,b))
    assert len(result.tools) == 1
    assert result.tools[0] == a.tools[0].tool
    assert len(result.duplicates) == 2
    assert all(d.retained.source_name == 'a' and d.removed.source_name == 'b' for d in result.duplicates)
    assert [d.removed.kind for d in result.duplicates] == ['drill','slot']
    assert not result.conflicts
    assert len(result.tool_map) == 2


@pytest.mark.parametrize('first,second,reason', [
    (holes(1,(0,0)),holes(2,(0,0)),'same-centre'),
    (holes(1,(0,0)),holes(1,(.000001,0)),'overlap'),
    (holes(1,(0,0)),slots(1,((-2,0),(2,0))),'overlap'),
    (slots(1,((-2,0),(2,0))),slots(1,((0,-2),(0,2))),'overlap'),
    (slots(1,((0,0),(5,0))),slots(1,((0,.9),(5,.9))),'overlap'),
    (slots(1,((0,0),(5,0))),slots(2,((0,0),(5,0))),'overlap'),
])
def test_all_incompatible_capsules_block_without_dropping_operations(first,second,reason):
    result = review_excellon_merge((source('a',first),source('b',second)))
    assert result.conflict_count == 1 and result.conflicts[0].reason == reason
    assert not result.duplicates
    assert sum(len(t.drills_mm)+len(t.slots_mm) for t in result.tools) == 2


@pytest.mark.parametrize('first,second', [
    (holes(1,(0,0)),holes(1,(1,0))),
    (holes(1,(0,0)),slots(1,((1,0),(3,0)))),
    (slots(1,((0,0),(5,0))),slots(1,((0,1),(5,1)))),
    (slots(1,((0,0),(5,0))),slots(1,((6,0),(7,0)))),
    (slots(1,((0,0),(5,0))),slots(1,((0,2),(5,2)))),
])
def test_exact_tangency_and_disjoint_footprints_allowed(first,second):
    assert review_excellon_merge((source('a',first),source('b',second))).conflict_count == 0


def test_conflict_details_are_bounded_but_exact_total_blocks():
    a = source('a', holes(2,*[(i*.001,0) for i in range(30)]))
    b = source('b', holes(2,(10,0)))
    result = review_excellon_merge((a,b))
    assert result.conflict_count == 435
    assert len(result.conflicts) == 200


def test_total_operation_budget_and_distinct_source_names():
    a=source('a',holes(1,*[(i*2,0) for i in range(501)]))
    b=replace(a,source_name='b')
    with pytest.raises(ValueError,match='1000|budget'):
        review_excellon_merge((a,b))
    with pytest.raises(ValueError,match='unique|distinct'):
        review_excellon_merge((a,a))


@pytest.mark.parametrize('sources',[(),[],(None,),tuple(None for _ in range(65))])
def test_invalid_source_collection(sources):
    with pytest.raises(ValueError):
        review_excellon_merge(sources)
