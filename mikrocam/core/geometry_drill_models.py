"""Immutable physical evidence from current Geometry contours."""
from dataclasses import dataclass
import math
import re


def _text(value: str, limit: int, label: str, *, byte_limit: bool = True) -> None:
    if type(value) is not str or not value:
        raise ValueError(f'{label} must be nonempty text')
    try:
        size = len(value.encode('utf-8')) if byte_limit else len(value)
        value.encode('utf-8')
    except UnicodeEncodeError as error:
        raise ValueError(f'{label} requires strict UTF-8') from error
    if size > limit:
        raise ValueError(f'{label} exceeds {limit}')


def _number(value: float, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f'{label} must be a finite number')
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f'{label} exceeds physical bounds') from error
    if not math.isfinite(result) or abs(result) > 1e9:
        raise ValueError(f'{label} exceeds finite physical bounds')
    return result


@dataclass(frozen=True)
class GeometryDrillCandidate:
    center_mm: tuple[float, float]
    diameter_mm: float
    source_id: str
    role: str
    duplicate_count: int = 0

    def __post_init__(self) -> None:
        if type(self.center_mm) is not tuple or len(self.center_mm) != 2:
            raise ValueError('Centre requires an immutable XY pair')
        object.__setattr__(self, 'center_mm', tuple(_number(v, 'Centre') for v in self.center_mm))
        diameter = _number(self.diameter_mm, 'Diameter')
        if diameter <= 0:
            raise ValueError('Diameter must be positive')
        object.__setattr__(self, 'diameter_mm', diameter)
        _text(self.source_id, 256, 'Source ID')
        if type(self.role) is not str or self.role not in ('exterior', 'interior', 'closed-line'):
            raise ValueError('Unsupported contour role')
        if type(self.duplicate_count) is not int or not 0 <= self.duplicate_count <= 10000:
            raise ValueError('Duplicate count must be an integer from 0 to 10000')


@dataclass(frozen=True)
class GeometryDrillReview:
    source_name: str
    source_units: str
    geometry_sha256: str
    candidates: tuple[GeometryDrillCandidate, ...]
    notices: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.source_name, 256, 'Source name')
        if type(self.source_units) is not str or self.source_units not in ('MM', 'IN'):
            raise ValueError('Source units must be explicit MM or IN')
        if type(self.geometry_sha256) is not str or re.fullmatch('[0-9a-f]{64}', self.geometry_sha256) is None:
            raise ValueError('Geometry fingerprint requires lowercase SHA256')
        if type(self.candidates) is not tuple or len(self.candidates) > 1000 or any(
                type(item) is not GeometryDrillCandidate for item in self.candidates):
            raise ValueError('Review requires at most 1000 immutable candidates')
        if len({item.source_id for item in self.candidates}) != len(self.candidates):
            raise ValueError('Candidate source IDs must be unique')
        if type(self.notices) is not tuple or len(self.notices) > 200:
            raise ValueError('Notices require an immutable tuple of at most 200 strings')
        for notice in self.notices:
            _text(notice, 512, 'Notice', byte_limit=False)
