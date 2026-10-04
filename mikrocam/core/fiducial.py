"""Fiducial pairs to one reviewed CAM-to-machine Placement, with residual-based rejection.

Design points are CAM/G-code source millimetres; measured points are machine (MPos)
millimetres. Fits never touch hardware; acceptance only says the declared thresholds
held for the supplied measurements.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations
import math

import numpy as np

from .placement import Placement, Point2D, _finite_real, _point


METHODS = ('rigid', 'similarity', 'affine')
MIN_POINTS = {'rigid': 2, 'similarity': 2, 'affine': 3}
UNKNOWNS = {'rigid': 3, 'similarity': 4, 'affine': 6}
MAX_PAIRS = 64
COLLINEAR_RATIO = 0.05
COINCIDENT_MM = 1e-6


def default_method(count: int) -> str:
    """Two points give translation+rotation; three or more give an affine correction."""
    return 'rigid' if count < 3 else 'affine'


def _name(value: object) -> str:
    if type(value) is not str or not 1 <= len(value) <= 64 or not value.isprintable() or value != value.strip():
        raise ValueError('Fiducial name requires 1..64 trimmed printable characters')
    return value


@dataclass(frozen=True)
class FiducialPair:
    """A design (source mm) point and its measured machine (MPos mm) point, if measured."""
    name: str
    design_mm: Point2D
    machine_mm: Point2D | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        _name(self.name)
        object.__setattr__(self, 'design_mm', _point(self.design_mm, 'design_mm'))
        if self.machine_mm is not None:
            object.__setattr__(self, 'machine_mm', _point(self.machine_mm, 'machine_mm'))
        if type(self.enabled) is not bool:
            raise ValueError('Fiducial enabled flag must be a boolean')


def _bounded(value: object, label: str, low: float, high: float, *, open_low: bool) -> float:
    result = _finite_real(value, label)
    if (result <= low if open_low else result < low) or result > high:
        raise ValueError(f'{label} is outside its allowed range')
    return result


@dataclass(frozen=True)
class AlignmentPolicy:
    """Explicit method and rejection thresholds shown to the operator."""
    method: str
    max_residual_mm: float = 0.05
    max_scale_deviation: float = 0.005
    min_separation_mm: float = 10.0

    def __post_init__(self) -> None:
        if self.method not in METHODS:
            raise ValueError(f'Alignment method must be one of {", ".join(METHODS)}')
        object.__setattr__(self, 'max_residual_mm',
                           _bounded(self.max_residual_mm, 'max_residual_mm', 0., 10., open_low=True))
        object.__setattr__(self, 'max_scale_deviation',
                           _bounded(self.max_scale_deviation, 'max_scale_deviation', 0., .1, open_low=False))
        object.__setattr__(self, 'min_separation_mm',
                           _bounded(self.min_separation_mm, 'min_separation_mm', 0., 1e4, open_low=True))


@dataclass(frozen=True)
class PairResidual:
    name: str
    design_mm: Point2D
    machine_mm: Point2D
    fitted_mm: Point2D
    error_mm: Point2D
    magnitude_mm: float


@dataclass(frozen=True)
class AlignmentFit:
    """Complete fit report; only an accepted fit releases its Placement."""
    method: str
    policy: AlignmentPolicy
    placement: Placement
    residuals: tuple[PairResidual, ...]
    rms_mm: float
    max_mm: float
    rotation_deg: float
    observed_scale: float
    axis_scales: tuple[float, float]
    determinant: float
    redundancy: int
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return not self.reasons

    def require_placement(self) -> Placement:
        if self.reasons:
            raise ValueError('Alignment rejected: ' + '; '.join(self.reasons))
        return self.placement


def _measured(pairs: Iterable[FiducialPair], policy: AlignmentPolicy) -> tuple[FiducialPair, ...]:
    if not isinstance(policy, AlignmentPolicy):
        raise ValueError('An explicit AlignmentPolicy is required')
    if isinstance(pairs, (str, bytes)):
        raise ValueError('Fiducial pairs must be a sequence of FiducialPair values')
    values = tuple(pairs)
    if len(values) > MAX_PAIRS or any(type(pair) is not FiducialPair for pair in values):
        raise ValueError(f'At most {MAX_PAIRS} FiducialPair values are supported')
    if len({pair.name for pair in values}) != len(values):
        raise ValueError('Fiducial names must be unique')
    used = tuple(pair for pair in values if pair.enabled)
    missing = [pair.name for pair in used if pair.machine_mm is None]
    if missing:
        raise ValueError('Enabled fiducials must be measured: ' + ', '.join(missing))
    if len(used) < MIN_POINTS[policy.method]:
        raise ValueError(f'{policy.method} alignment needs at least {MIN_POINTS[policy.method]} enabled fiducials')
    return used


def _check_geometry(design: np.ndarray, method: str) -> None:
    for first, second in combinations(design, 2):
        if math.dist(first, second) < COINCIDENT_MM:
            raise ValueError('Design fiducials coincide; alignment is undetermined')
    if method == 'affine':
        singular = np.linalg.svd(design - design.mean(axis=0), compute_uv=False)
        if singular[0] <= 0 or singular[1] / singular[0] < COLLINEAR_RATIO:
            raise ValueError('Design fiducials are (nearly) collinear; affine alignment is undetermined')


def _procrustes(design: np.ndarray, machine: np.ndarray) -> tuple[float, float]:
    """Return the proper rotation angle and least-squares similarity scale."""
    d, m = design - design.mean(axis=0), machine - machine.mean(axis=0)
    dot = float(np.sum(d[:, 0] * m[:, 0] + d[:, 1] * m[:, 1]))
    cross = float(np.sum(d[:, 0] * m[:, 1] - d[:, 1] * m[:, 0]))
    return math.atan2(cross, dot), math.hypot(dot, cross) / float(np.sum(d * d))


def _placement(design: np.ndarray, machine: np.ndarray, method: str, angle: float,
               scale: float) -> Placement:
    centre_d, centre_m = design.mean(axis=0), machine.mean(axis=0)
    if method == 'rigid':
        return Placement(origin=tuple(centre_d), translation=tuple(centre_m), rotation_deg=math.degrees(angle))
    if method == 'similarity':
        c, s = scale * math.cos(angle), scale * math.sin(angle)
        linear = np.array([[c, -s], [s, c]])
    else:
        solution, *_ = np.linalg.lstsq(design - centre_d, machine - centre_m, rcond=None)
        linear = solution.T
    offset = centre_m - linear @ centre_d
    return Placement(affine=(float(linear[0, 0]), float(linear[0, 1]), float(linear[1, 0]),
                             float(linear[1, 1]), float(offset[0]), float(offset[1])))


def _residuals(used: tuple[FiducialPair, ...], placement: Placement) -> tuple[PairResidual, ...]:
    result = []
    for pair in used:
        fitted = placement.apply_point(pair.design_mm)
        error = (pair.machine_mm[0] - fitted[0], pair.machine_mm[1] - fitted[1])
        result.append(PairResidual(pair.name, pair.design_mm, pair.machine_mm, fitted, error, math.hypot(*error)))
    return tuple(result)


def _reasons(fit: dict, policy: AlignmentPolicy, design: np.ndarray) -> list[str]:
    reasons = []
    worst = max(fit['residuals'], key=lambda item: item.magnitude_mm)
    if worst.magnitude_mm > policy.max_residual_mm:
        reasons.append(f'max residual {worst.magnitude_mm:.4f} mm at {worst.name} exceeds '
                       f'{policy.max_residual_mm:g} mm')
    limit = policy.max_scale_deviation
    if abs(fit['observed_scale'] - 1.) > limit + 1e-12:
        reasons.append(f'observed scale {fit["observed_scale"]:.6f} deviates more than {limit:g} from 1')
    if any(abs(value - 1.) > limit + 1e-12 for value in fit['axis_scales']):
        reasons.append('axis scale {:.6f}/{:.6f} deviates more than {:g} from 1'.format(*fit['axis_scales'], limit))
    if fit['determinant'] < 0:
        reasons.append('measured fiducials imply a mirror; check pair order')
    separation = min(math.dist(a, b) for a, b in combinations(design, 2))
    if separation < policy.min_separation_mm:
        reasons.append(f'closest fiducial separation {separation:.3f} mm is below {policy.min_separation_mm:g} mm')
    return reasons


def fit_alignment(pairs: Iterable[FiducialPair], policy: AlignmentPolicy) -> AlignmentFit:
    """Fit enabled measured pairs; degenerate input raises, threshold failures are reported."""
    used = _measured(pairs, policy)
    design = np.array([pair.design_mm for pair in used], dtype=float)
    machine = np.array([pair.machine_mm for pair in used], dtype=float)
    _check_geometry(design, policy.method)
    angle, scale = _procrustes(design, machine)
    placement = _placement(design, machine, policy.method, angle, scale)
    a, b, d, e = placement.matrix[:4]
    singular = np.linalg.svd(np.array([[a, b], [d, e]]), compute_uv=False)
    residuals = _residuals(used, placement)
    magnitudes = [item.magnitude_mm for item in residuals]
    values = dict(residuals=residuals, observed_scale=scale, determinant=a * e - b * d,
                  axis_scales=(float(singular[0]), float(singular[1])))
    redundancy = 2 * len(used) - UNKNOWNS[policy.method]
    warnings = () if redundancy else (
        'exact fit: residuals cannot reveal a measurement error; add a fiducial to verify',)
    return AlignmentFit(policy.method, policy, placement, residuals,
                        math.sqrt(sum(m * m for m in magnitudes) / len(magnitudes)), max(magnitudes),
                        math.degrees(math.atan2(d - b, a + e)), scale, values['axis_scales'],
                        values['determinant'], redundancy, tuple(_reasons(values, policy, design)), warnings)
