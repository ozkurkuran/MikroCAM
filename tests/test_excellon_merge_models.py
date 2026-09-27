"""Strict shape validation keeps ephemeral merge evidence immutable."""
from dataclasses import FrozenInstanceError, replace
import pytest
from mikrocam.core.excellon_tools import ExcellonTool
from mikrocam.core.excellon_merge_models import (MergeSourceTool, MergeSource, OperationRef, MergeToolMap,
    MergeDuplicate, MergeConflict, ExcellonMergeReview)


def tool():
    return ExcellonTool(1, ((0, 0),), ())


def source(name='one'):
    return MergeSource(name, 'MM', 'a' * 64, (MergeSourceTool('int:1', tool()),))


def ref(name='one'):
    return OperationRef(name, 'int:1', 'drill', 0)


def review():
    return ExcellonMergeReview((source(), source('two')), (tool(),),
        (MergeToolMap('one', 'int:1', 1), MergeToolMap('two', 'int:1', 1)),
        (MergeDuplicate(ref(), ref('two')),), (), 0)


def test_valid_records_frozen_and_keep_identity():
    result = review()
    assert result.sources[0].tools[0].tool.diameter_mm == 1
    assert result.duplicates[0].retained == ref()
    with pytest.raises(FrozenInstanceError):
        result.conflict_count = 1


@pytest.mark.parametrize('record,changes', [
    (MergeSourceTool('id', tool()), {'tool_id': ''}),
    (MergeSourceTool('id', tool()), {'tool_id': 'é' * 129}),
    (MergeSourceTool('id', tool()), {'tool': object()}),
    (source(), {'source_name': ' one'}), (source(), {'source_name': 'one\n'}),
    (source(), {'source_name': 'é' * 129}), (source(), {'source_name': '\ud800'}),
    (source(), {'source_units': 'mm'}), (source(), {'source_sha256': 'A' * 64}),
    (source(), {'tools': []}), (source(), {'tools': ()}),
    (source(), {'tools': (source().tools[0],) * 2}),
    (ref(), {'kind': 'arc'}), (ref(), {'index': True}), (ref(), {'index': -1}),
    (ref(), {'index': 1000}), (ref(), {'index': 1.0}),
    (MergeToolMap('one', 'id', 1), {'output_tool': True}),
    (MergeToolMap('one', 'id', 1), {'output_tool': 0}),
    (MergeToolMap('one', 'id', 1), {'output_tool': 1001}),
    (MergeDuplicate(ref(), ref('two')), {'retained': None}),
    (MergeConflict(ref(), ref('two'), 'overlap'), {'reason': 'tangent'}),
    (MergeConflict(ref(), ref('two'), 'overlap'), {'second': object()}),
])
def test_records_reject_invalid_shape(record, changes):
    with pytest.raises(ValueError):
        replace(record, **changes)


@pytest.mark.parametrize('changes', [
    {'sources': []}, {'sources': (source(),)}, {'sources': (source(), source())},
    {'sources': (object(), source())}, {'tools': []}, {'tools': ()}, {'tools': (object(),)},
    {'tool_map': []}, {'tool_map': (object(),)}, {'duplicates': []}, {'duplicates': (object(),)},
    {'conflicts': []}, {'conflicts': (object(),)}, {'conflict_count': True},
    {'conflict_count': -1}, {'conflict_count': 499501}, {'conflict_count': 1},
    {'conflicts': (MergeConflict(ref(), ref('two'), 'same-centre'),)},
])
def test_review_rejects_invalid_shape(changes):
    with pytest.raises(ValueError):
        replace(review(), **changes)


def test_bounded_counts_and_conflict_shape_not_geometry_validation():
    conflict = MergeConflict(ref(), ref('two'), 'same-centre')
    result = replace(review(), conflicts=(conflict,) * 200, conflict_count=499500)
    assert result.conflict_count == 499500
    assert replace(review(), conflicts=(conflict,), conflict_count=1)
    for changes in ({'conflicts': (conflict,) * 201, 'conflict_count': 201},
                    {'tool_map': (MergeToolMap('one', 'id', 1),) * 1001},
                    {'duplicates': (MergeDuplicate(ref(), ref('two')),) * 1001},
                    {'sources': tuple(source(str(i)) for i in range(65))},
                    {'tools': (tool(),) * 1001}):
        with pytest.raises(ValueError):
            replace(review(), **changes)


def test_source_and_review_total_operation_caps():
    many = ExcellonTool(1, tuple((float(i), 0) for i in range(600)), ())
    first = MergeSourceTool('first', many)
    second = MergeSourceTool('second', many)
    with pytest.raises(ValueError):
        MergeSource('one', 'MM', 'a' * 64, (first, second))
    heavy = MergeSource('one', 'MM', 'a' * 64, (first,))
    with pytest.raises(ValueError):
        replace(review(), sources=(heavy, replace(heavy, source_name='two')))
    with pytest.raises(ValueError):
        replace(review(), tools=(many, many))


def test_boundary_text_ids_and_indices():
    assert MergeSourceTool('é' * 128, tool())
    assert OperationRef('board', 'id', 'slot', 999)
    assert MergeToolMap('board', 'id', 1000)
    assert MergeSource('é' * 128, 'IN', 'f' * 64, (MergeSourceTool('id', tool()),))
