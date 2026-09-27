from dataclasses import FrozenInstanceError, replace
import pytest
from mikrocam.core.geometry_drill_models import GeometryDrillCandidate, GeometryDrillReview


def candidate(**changes):
    return replace(GeometryDrillCandidate((1, 2), 0.8, 'solid:0:exterior', 'exterior'), **changes)


def review(**changes):
    return replace(GeometryDrillReview('board', 'MM', 'a' * 64, (candidate(),), ('Review hole intent.',)), **changes)


def test_records_are_frozen_and_normalize_numbers():
    value = candidate()
    assert value.center_mm == (1.0, 2.0) and value.diameter_mm == 0.8
    assert value.duplicate_count == 0
    with pytest.raises(FrozenInstanceError):
        value.role = 'interior'
    assert review().candidates[0] == value


@pytest.mark.parametrize('changes', [
    {'center_mm': [1, 2]}, {'center_mm': (True, 2)}, {'center_mm': (float('nan'), 2)},
    {'center_mm': (1e9 + 1, 0)}, {'center_mm': (1, 2, 3)}, {'diameter_mm': True},
    {'diameter_mm': 0}, {'diameter_mm': float('inf')}, {'diameter_mm': 1e9 + 1},
    {'source_id': ''}, {'source_id': '\ud800'}, {'source_id': 'é' * 129},
    {'role': 'circle'}, {'duplicate_count': True}, {'duplicate_count': -1},
    {'duplicate_count': 10001}, {'duplicate_count': 1.0},
])
def test_candidate_rejects_invalid_fields(changes):
    with pytest.raises(ValueError):
        candidate(**changes)


@pytest.mark.parametrize('changes', [
    {'source_name': ''}, {'source_name': 'é' * 129}, {'source_name': '\ud800'},
    {'source_units': 'mm'}, {'source_units': 'INCH'}, {'geometry_sha256': 'A' * 64},
    {'geometry_sha256': 'a' * 63}, {'candidates': []}, {'candidates': (object(),)},
    {'candidates': (candidate(), candidate())}, {'notices': []}, {'notices': ('',)},
    {'notices': ('x' * 513,)}, {'notices': ('\ud800',)}, {'notices': (1,)},
    {'notices': ('notice',) * 201},
])
def test_review_rejects_invalid_fields(changes):
    with pytest.raises(ValueError):
        review(**changes)


def test_exact_limits_and_empty_review():
    assert candidate(center_mm=(-1e9, 1e9), diameter_mm=1e9, duplicate_count=10000)
    candidates = tuple(candidate(source_id=str(index)) for index in range(1000))
    assert len(review(candidates=candidates, notices=('é' * 512,) * 200).candidates) == 1000
    assert review(candidates=(), notices=(), source_units='IN')
    with pytest.raises(ValueError):
        review(candidates=candidates + (candidate(source_id='extra'),))
