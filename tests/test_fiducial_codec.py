"""Versioned strict fiducial-set files; the committed v1 fixture must keep opening."""
import json
from pathlib import Path

import pytest

from mikrocam.core.fiducial import AlignmentPolicy, FiducialPair, fit_alignment
from mikrocam.core.fiducial_codec import (FiducialSet, SCHEMA_VERSION, dumps_fiducial_set,
                                          loads_fiducial_set)


FIXTURE = Path(__file__).parent / 'test_files' / 'fiducial_set_v1.json'


def sample():
    return FiducialSet('Panel', AlignmentPolicy('rigid', max_residual_mm=.1),
                       (FiducialPair('F1', (0., 0.), (10.5, 20.25)),
                        FiducialPair('F2', (50., 0.), None, enabled=False)))


def test_roundtrip_is_exact_and_deterministic():
    value = sample()
    text = dumps_fiducial_set(value)
    assert loads_fiducial_set(text) == value
    assert dumps_fiducial_set(loads_fiducial_set(text)) == text
    data = json.loads(text)
    assert data['kind'] == 'mikrocam.fiducial-set' and data['schema_version'] == SCHEMA_VERSION == 1
    assert data['units'] == 'mm' and data['pairs'][1]['machine_mm'] is None


def test_committed_version_one_file_opens_and_fits():
    value = loads_fiducial_set(FIXTURE.read_text(encoding='utf-8'))
    assert value.name == 'Board A top fixture' and value.policy.method == 'affine'
    assert [pair.name for pair in value.pairs] == ['F1', 'F2', 'F3', 'F4']
    assert value.pairs[3].machine_mm is None and not value.pairs[3].enabled
    fit = fit_alignment(value.pairs, value.policy)
    assert fit.redundancy == 0


def mutate(change):
    data = json.loads(dumps_fiducial_set(sample()))
    change(data)
    return json.dumps(data)


@pytest.mark.parametrize('change', [
    lambda d: d.update(schema_version=2), lambda d: d.update(schema_version=0),
    lambda d: d.update(schema_version=True), lambda d: d.update(kind='mikrocam.laser-job'),
    lambda d: d.update(units='inch'), lambda d: d.update(extra=1), lambda d: d.pop('name'),
    lambda d: d.update(method='projective'), lambda d: d['policy'].update(extra=1),
    lambda d: d['policy'].pop('max_residual_mm'), lambda d: d['pairs'][0].update(extra=1),
    lambda d: d['pairs'][0].update(design_mm=[0, 0, 0]), lambda d: d['pairs'][0].update(design_mm='0,0'),
    lambda d: d['pairs'][0].update(enabled=1), lambda d: d.update(pairs=[]),
    lambda d: d.update(pairs={}), lambda d: d['pairs'][1].update(name='F1'),
    lambda d: d['pairs'][0].update(machine_mm=[1e999, 0])])
def test_invalid_documents_are_rejected(change):
    with pytest.raises(ValueError):
        loads_fiducial_set(mutate(change))


@pytest.mark.parametrize('text', ['', 'null', '[]', '{', '{"a": NaN}', 'oversized'])
def test_malformed_or_oversized_text_is_rejected(text):
    if text == 'oversized':
        text = ' ' * (2 * 1024 * 1024) + dumps_fiducial_set(sample())
    with pytest.raises(ValueError):
        loads_fiducial_set(text)


def test_constructor_validates_types():
    with pytest.raises(ValueError):
        FiducialSet('', AlignmentPolicy('rigid'), sample().pairs)
    with pytest.raises(ValueError):
        FiducialSet('x', 'rigid', sample().pairs)
    with pytest.raises(ValueError):
        FiducialSet('x', AlignmentPolicy('rigid'), list(sample().pairs))
