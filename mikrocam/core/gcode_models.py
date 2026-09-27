"""Immutable bounded offline preflight inputs/results; never machine authorization."""
from dataclasses import dataclass, field
import hashlib
import re

from .placement import Placement, _finite_real


XYZ = tuple[float, float, float]
Bounds3D = tuple[XYZ, XYZ]
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_LINES = 250_000
MAX_LINE_LENGTH = 4096
MAX_NUMBER_LENGTH = 64
MAX_MAGNITUDE = 1e9
MAX_FINDINGS = 200


class PreflightCancelled(Exception):
    """Cooperative cancellation is not a successful or completed analysis."""


def _text(value: str, label: str, limit: int) -> None:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError(f'{label} must be nonempty text of at most {limit} characters')


def _number(value: float, label: str, bounded: bool = True) -> float:
    result = _finite_real(value, label)
    if bounded and abs(result) > MAX_MAGNITUDE:
        raise ValueError(f'{label} magnitude exceeds {MAX_MAGNITUDE:g}')
    return result


def _xyz(value: XYZ, label: str, bounded: bool = True) -> XYZ:
    if type(value) is not tuple or len(value) != 3:
        raise ValueError(f'{label} must be an immutable XYZ tuple')
    return tuple(_number(axis, f'{label}[{index}]', bounded) for index, axis in enumerate(value))


def _count(value: int, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f'{label} must be a nonnegative integer, not boolean')


@dataclass(frozen=True)
class SourceSnapshot:
    """Exact immutable text identity; executable syntax remains the lexer's responsibility."""
    name: str
    text: str
    sha256: str = field(init=False)

    def __post_init__(self) -> None:
        _text(self.name, 'Source name', 256)
        _text(self.text, 'Source text', MAX_SOURCE_BYTES)
        try:
            data = self.text.encode('utf-8')
        except UnicodeEncodeError as error:
            raise ValueError('Source text must encode as strict UTF-8') from error
        if len(data) > MAX_SOURCE_BYTES:
            raise ValueError(f'Source text exceeds {MAX_SOURCE_BYTES} UTF-8 bytes')
        object.__setattr__(self, 'sha256', hashlib.sha256(data).hexdigest())


@dataclass(frozen=True)
class PreflightSetup:
    """Explicit assumed work position, Placement, Z translation and machine envelope."""
    initial_position_mm: XYZ
    placement: Placement
    z_offset_mm: float
    machine_min_mm: XYZ
    machine_max_mm: XYZ
    safe_z_mm: float
    rapid_rates_mm_min: XYZ | None = None

    def __post_init__(self) -> None:
        for name in ('initial_position_mm', 'machine_min_mm', 'machine_max_mm'):
            object.__setattr__(self, name, _xyz(getattr(self, name), name))
        if not isinstance(self.placement, Placement):
            raise ValueError('An explicit Placement is required')
        for name in ('origin', 'translation'):
            for axis in getattr(self.placement, name):
                _number(axis, f'placement.{name}')
        self.placement.matrix  # Reject nonfinite derived coefficients, using the existing authority.
        for name in ('z_offset_mm', 'safe_z_mm'):
            object.__setattr__(self, name, _number(getattr(self, name), name))
        if any(low >= high for low, high in zip(self.machine_min_mm, self.machine_max_mm)):
            raise ValueError('Machine minimum must be strictly below maximum on every axis')
        if not self.machine_min_mm[2] <= self.safe_z_mm <= self.machine_max_mm[2]:
            raise ValueError('Safe Z must be inside the declared machine Z envelope')
        if self.rapid_rates_mm_min is not None:
            rates = _xyz(self.rapid_rates_mm_min, 'rapid_rates_mm_min')
            if any(rate <= 0 for rate in rates):
                raise ValueError('All explicit rapid rates must be positive')
            object.__setattr__(self, 'rapid_rates_mm_min', rates)


@dataclass(frozen=True)
class Finding:
    line: int
    code: str
    message: str
    severity: str = 'error'

    def __post_init__(self) -> None:
        _count(self.line, 'Finding line')
        _text(self.code, 'Finding code', 64)
        _text(self.message, 'Finding message', 256)
        if self.severity not in ('error', 'warning'):
            raise ValueError('Finding severity must be error or warning')


@dataclass(frozen=True)
class PreflightReport:
    source_name: str
    source_sha256: str
    setup: PreflightSetup
    complete: bool
    bounds_mm: Bounds3D | None
    executable_blocks: int
    rapid_count: int
    linear_count: int
    arc_count: int
    distance_mm: float
    duration_seconds: float | None
    units_seen: tuple[str, ...]
    distance_modes_seen: tuple[str, ...]
    findings: tuple[Finding, ...]
    finding_count: int
    error_count: int

    def __post_init__(self) -> None:
        _text(self.source_name, 'Source name', 256)
        if not isinstance(self.source_sha256, str) or re.fullmatch('[0-9a-f]{64}', self.source_sha256) is None:
            raise ValueError('Source digest must be 64 lowercase hexadecimal characters')
        if not isinstance(self.setup, PreflightSetup) or type(self.complete) is not bool:
            raise ValueError('Report requires an immutable setup and boolean completeness')
        if self.bounds_mm is not None:
            if type(self.bounds_mm) is not tuple or len(self.bounds_mm) != 2:
                raise ValueError('Bounds must be an immutable minimum/maximum XYZ pair')
            bounds = tuple(_xyz(vector, 'bounds_mm', False) for vector in self.bounds_mm)
            if any(low > high for low, high in zip(*bounds)):
                raise ValueError('Report bounds must be ordered')
            object.__setattr__(self, 'bounds_mm', bounds)
        for name in ('executable_blocks', 'rapid_count', 'linear_count', 'arc_count', 'finding_count', 'error_count'):
            _count(getattr(self, name), name)
        if self.rapid_count + self.linear_count + self.arc_count > self.executable_blocks:
            raise ValueError('Movement count cannot exceed executable blocks')
        distance = _number(self.distance_mm, 'distance_mm', False)
        if distance < 0:
            raise ValueError('Report distance must be nonnegative')
        object.__setattr__(self, 'distance_mm', distance)
        if self.duration_seconds is not None:
            duration = _number(self.duration_seconds, 'duration_seconds', False)
            if duration < 0 or not self.complete:
                raise ValueError('Duration must be nonnegative and unavailable on incomplete interpretation')
            object.__setattr__(self, 'duration_seconds', duration)
        self._validate_modes()
        self._validate_findings()

    def _validate_modes(self) -> None:
        for name, choices in (('units_seen', ('mm', 'inch')),
                              ('distance_modes_seen', ('absolute', 'incremental'))):
            values = getattr(self, name)
            if (type(values) is not tuple or any(value not in choices for value in values)
                    or len(set(values)) != len(values)):
                raise ValueError(f'{name} must contain unique immutable supported modes')

    def _validate_findings(self) -> None:
        if (type(self.findings) is not tuple or len(self.findings) != min(self.finding_count, MAX_FINDINGS)
                or any(not isinstance(finding, Finding) for finding in self.findings)):
            raise ValueError('Findings must retain the first bounded typed diagnostic sample')
        errors = sum(finding.severity == 'error' for finding in self.findings)
        warnings = len(self.findings) - errors
        if not errors <= self.error_count <= self.finding_count or warnings > self.finding_count - self.error_count:
            raise ValueError('Diagnostic totals must be consistent with retained findings')

    @property
    def allowed(self) -> bool:
        """Geometry checks passed for the declared assumptions, never permission to run."""
        return self.complete and self.error_count == 0
