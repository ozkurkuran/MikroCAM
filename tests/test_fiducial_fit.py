"""Fiducial fits recover known transforms and refuse unsafe or undetermined corrections."""
import math

import numpy as np
import pytest

from mikrocam.core.fiducial import (AlignmentPolicy, FiducialPair, default_method, fit_alignment)
from mikrocam.core.placement import Placement


DESIGN = ((0., 0.), (80., 0.), (80., 60.), (0., 60.), (40., 30.))


def pairs(placement, design=DESIGN, noise=None):
    result = []
    for index, point in enumerate(design):
        measured = placement.apply_point(point)
        if noise is not None:
            measured = (measured[0] + noise[index][0], measured[1] + noise[index][1])
        result.append(FiducialPair(f'F{index + 1}', point, measured))
    return tuple(result)


def policy(method, **changes):
    return AlignmentPolicy(method, **changes)


def test_two_point_rigid_recovers_rotation_translation_as_rigid_placement():
    truth = Placement(origin=(0., 0.), translation=(-120.5, -80.25), rotation_deg=1.7)
    fit = fit_alignment(pairs(truth, DESIGN[:2]), policy('rigid'))
    assert fit.accepted and fit.redundancy == 1
    placement = fit.require_placement()
    assert placement.affine is None and placement.mirror_x is False
    assert placement.matrix == pytest.approx(truth.matrix, abs=1e-12)
    assert fit.rotation_deg == pytest.approx(1.7, abs=1e-10)
    assert fit.observed_scale == pytest.approx(1., abs=1e-12)
    assert fit.max_mm == pytest.approx(0., abs=1e-9)
    for residual in fit.residuals:
        assert residual.fitted_mm == pytest.approx(placement.apply_point(residual.design_mm))


def test_two_point_similarity_is_exact_and_warns_without_redundancy():
    truth = Placement(affine=tuple(1.003 * v for v in Placement(rotation_deg=-2.).matrix[:4]) + (5., 6.))
    fit = fit_alignment(pairs(truth, DESIGN[:2]), policy('similarity'))
    assert fit.accepted and fit.redundancy == 0 and fit.warnings
    assert fit.require_placement().affine == pytest.approx(truth.matrix, abs=1e-12)
    assert fit.observed_scale == pytest.approx(1.003, abs=1e-12)


def test_rigid_rejects_scale_mismatch_that_similarity_would_absorb():
    truth = Placement(affine=(1.01, 0., 0., 1.01, 0., 0.))
    rigid = fit_alignment(pairs(truth, DESIGN[:2]), policy('rigid'))
    assert not rigid.accepted
    assert any('scale' in reason for reason in rigid.reasons)
    assert any('residual' in reason for reason in rigid.reasons)
    with pytest.raises(ValueError, match='rejected'):
        rigid.require_placement()
    similar = fit_alignment(pairs(truth, DESIGN[:2]), policy('similarity', max_scale_deviation=.02))
    assert similar.accepted


def test_three_point_affine_is_exact_and_four_point_affine_is_least_squares():
    truth = Placement(affine=(1.002, .004, -.003, .999, 10., -20.))
    exact = fit_alignment(pairs(truth, DESIGN[:3]), policy('affine'))
    assert exact.accepted and exact.redundancy == 0 and exact.warnings
    assert exact.require_placement().matrix == pytest.approx(truth.matrix, abs=1e-10)
    noise = ((.01, -.005), (-.008, .004), (.003, .009), (-.006, -.007), (.002, .001))
    fit = fit_alignment(pairs(truth, noise=noise), policy('affine'))
    assert fit.accepted and fit.redundancy == 4 and not fit.warnings
    design = np.array([[x, y, 1.] for x, y in DESIGN])
    measured = np.array([p.machine_mm for p in pairs(truth, noise=noise)])
    expected, *_ = np.linalg.lstsq(design, measured, rcond=None)
    a, b, d, e, xoff, yoff = fit.require_placement().matrix
    assert (a, b, xoff) == pytest.approx(tuple(expected[:, 0]), abs=1e-9)
    assert (d, e, yoff) == pytest.approx(tuple(expected[:, 1]), abs=1e-9)
    magnitudes = [r.magnitude_mm for r in fit.residuals]
    assert fit.max_mm == pytest.approx(max(magnitudes))
    assert fit.rms_mm == pytest.approx(math.sqrt(sum(m*m for m in magnitudes)/len(magnitudes)))


def test_large_residual_rejects_and_names_the_worst_pair():
    truth = Placement(rotation_deg=.5)
    noise = ((0., 0.),) * 4 + ((.3, 0.),)
    fit = fit_alignment(pairs(truth, noise=noise), policy('affine'))
    assert not fit.accepted
    assert any('F5' in reason for reason in fit.reasons)


def test_mirror_is_always_rejected():
    fit = fit_alignment(pairs(Placement(mirror_x=True), DESIGN[:4]), policy('affine'))
    assert not fit.accepted and any('mirror' in reason for reason in fit.reasons)


def test_affine_axis_scale_beyond_policy_is_rejected():
    fit = fit_alignment(pairs(Placement(affine=(1.02, 0., 0., 1., 0., 0.)), DESIGN[:4]),
                        policy('affine'))
    assert not fit.accepted and any('scale' in reason for reason in fit.reasons)
    assert fit.axis_scales == pytest.approx((1.02, 1.))


def test_points_closer_than_minimum_separation_are_rejected():
    design = ((0., 0.), (5., 0.))
    fit = fit_alignment(pairs(Placement(), design), policy('rigid'))
    assert not fit.accepted and any('separation' in reason for reason in fit.reasons)


@pytest.mark.parametrize('method,design', [('rigid', ((1., 1.), (1., 1.))),
                                           ('affine', ((0., 0.), (50., 0.), (100., 0.))),
                                           ('affine', ((0., 0.), (50., 1.), (100., 0.))),
                                           ('affine', ((0., 0.), (50., 50.))),
                                           ('rigid', ((0., 0.),))])
def test_degenerate_geometry_produces_no_fit(method, design):
    with pytest.raises(ValueError):
        fit_alignment(pairs(Placement(), design), policy(method))


def test_disabled_pairs_are_ignored_and_missing_measurements_fail():
    base = pairs(Placement(translation=(1., 2.)), DESIGN[:3])
    disabled = base + (FiducialPair('bad', (10., 10.), (999., 999.), enabled=False),)
    assert fit_alignment(disabled, policy('affine')).accepted
    with pytest.raises(ValueError, match='measured'):
        fit_alignment(base[:2] + (FiducialPair('F3', (80., 60.)),), policy('affine'))


@pytest.mark.parametrize('kwargs', [dict(name=''), dict(name='x' * 65), dict(name='a\nb'),
                                    dict(design_mm=(math.inf, 0.)), dict(machine_mm=(0., math.nan)),
                                    dict(enabled=1), dict(design_mm=(1., 2., 3.))])
def test_invalid_pairs_are_rejected(kwargs):
    values = dict(name='F1', design_mm=(0., 0.), machine_mm=(1., 1.), enabled=True)
    values.update(kwargs)
    with pytest.raises(ValueError):
        FiducialPair(**values)


@pytest.mark.parametrize('kwargs', [dict(method='projective'), dict(max_residual_mm=0.),
                                    dict(max_residual_mm=11.), dict(max_scale_deviation=-.1),
                                    dict(max_scale_deviation=.2), dict(min_separation_mm=0.),
                                    dict(max_residual_mm=True)])
def test_invalid_policy_is_rejected(kwargs):
    values = dict(method='affine')
    values.update(kwargs)
    with pytest.raises(ValueError):
        AlignmentPolicy(**values)


def test_duplicate_names_and_too_many_pairs_are_rejected():
    first = FiducialPair('F', (0., 0.), (0., 0.))
    second = FiducialPair('F', (50., 0.), (50., 0.))
    with pytest.raises(ValueError, match='unique'):
        fit_alignment((first, second), policy('rigid'))
    many = tuple(FiducialPair(f'F{i}', (float(i), float(i * i % 7)), (float(i), 0.)) for i in range(65))
    with pytest.raises(ValueError):
        fit_alignment(many, policy('affine'))


def test_default_method_follows_point_count():
    assert default_method(2) == 'rigid'
    assert default_method(3) == 'affine'
    assert default_method(9) == 'affine'
