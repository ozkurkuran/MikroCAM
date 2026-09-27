"""Immutable historical SVG import facts, measured without re-rendering geometry."""
from dataclasses import dataclass
import math
import re

from shapely import get_coordinates, get_num_coordinates
from shapely.geometry.base import BaseGeometry

from .placement import Affine2D
from .svg_models import (CURVE_TOLERANCE_MM, MAX_SVG_POINTS, SvgImportResult,
                         SvgNotice, validate_affine)
from .svg_transform import parse_svg_length, parse_svg_numbers, resolve_svg_viewport

_UNITS = ('absent', 'unitless', 'px', 'mm', 'cm', 'in', 'pt', 'pc')
_ASPECTS = ('none',) + tuple(x + y + ' meet' for x in ('xMin', 'xMid', 'xMax')
                           for y in ('YMin', 'YMid', 'YMax'))


def _text(value: object, limit: int, label: str) -> None:
    if type(value) is not str or not value or len(value) > limit:
        raise ValueError(f'{label} must be nonempty text within {limit} characters')
    try:
        value.encode('utf-8')
    except UnicodeEncodeError as error:
        raise ValueError(f'{label} must be strict UTF-8 text') from error


def _number(value: object, limit: float, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f'{label} must be a finite nonboolean number')
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f'{label} exceeds supported magnitude') from error
    if not math.isfinite(number) or abs(number) > limit:
        raise ValueError(f'{label} exceeds supported finite magnitude')
    return number


def _tuple_numbers(value: object, count: int, label: str) -> None:
    if type(value) is not tuple or len(value) != count:
        raise ValueError(f'{label} must be an immutable {count}-number tuple')
    for number in value:
        _number(number, 1e9, label)


@dataclass(frozen=True)
class ImportCoordinates:
    source_width: str | None
    source_height: str | None
    source_units: tuple[str, str]
    view_box: tuple[float, float, float, float] | None
    aspect_ratio: str
    viewport_mm: tuple[float, float]
    matrix_mm: Affine2D
    flipped: bool

    def __post_init__(self) -> None:
        for value in (self.source_width, self.source_height):
            if value is not None:
                _text(value, 128, 'Source dimension')
                if value != value.strip():
                    raise ValueError('Source dimension tokens must be trimmed')
        if (type(self.source_units) is not tuple or len(self.source_units) != 2
                or any(type(unit) is not str or unit not in _UNITS for unit in self.source_units)):
            raise ValueError('Source units require two supported immutable labels')
        for token, unit in zip((self.source_width, self.source_height), self.source_units):
            if token is not None and parse_svg_length(token) <= 0:
                raise ValueError('Recorded source dimensions must be positive')
            if _dimension(token) != unit:
                raise ValueError('Source dimension token and unit label must agree')
        if self.view_box is not None:
            _tuple_numbers(self.view_box, 4, 'ViewBox')
            if self.view_box[2] <= 0 or self.view_box[3] <= 0:
                raise ValueError('ViewBox dimensions must be positive')
        if type(self.aspect_ratio) is not str or self.aspect_ratio not in _ASPECTS:
            raise ValueError('Aspect ratio must be resolved none or aligned meet')
        _tuple_numbers(self.viewport_mm, 2, 'Viewport')
        if min(self.viewport_mm) <= 0:
            raise ValueError('Viewport dimensions must be positive')
        validate_affine(self.matrix_mm)
        if type(self.flipped) is not bool:
            raise ValueError('Flip must be boolean')


@dataclass(frozen=True)
class ImportQuality:
    bounds_mm: tuple[float, float, float, float] | None
    geometry_count: int
    valid_count: int
    invalid_count: int
    empty_count: int
    open_paths: int
    closed_paths: int
    precision_mm: float | None

    def __post_init__(self) -> None:
        for name in ('geometry_count', 'valid_count', 'invalid_count', 'empty_count',
                     'open_paths', 'closed_paths'):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 500000:
                raise ValueError(f'{name} must be an integer in 0..500000')
        if self.geometry_count != self.valid_count + self.invalid_count + self.empty_count:
            raise ValueError('Geometry count must equal valid, invalid and empty components')
        if (self.bounds_mm is None) != (self.valid_count + self.invalid_count == 0):
            raise ValueError('Bounds must be absent exactly when no nonempty geometry exists')
        if self.bounds_mm is not None:
            _tuple_numbers(self.bounds_mm, 4, 'Material bounds')
            if self.bounds_mm[0] > self.bounds_mm[2] or self.bounds_mm[1] > self.bounds_mm[3]:
                raise ValueError('Material bounds must be ordered')
        if self.precision_mm is not None and _number(self.precision_mm, 1, 'Precision') <= 0:
            raise ValueError('Available precision must be positive')


@dataclass(frozen=True)
class ImportReport:
    source_name: str
    source_sha256: str
    coordinates: ImportCoordinates
    quality: ImportQuality
    notices: tuple[SvgNotice, ...] = ()

    def __post_init__(self) -> None:
        _text(self.source_name, 256, 'Source name')
        if type(self.source_sha256) is not str or re.fullmatch('[0-9a-f]{64}', self.source_sha256) is None:
            raise ValueError('Source SHA256 must be lowercase 64-digit hexadecimal')
        if type(self.coordinates) is not ImportCoordinates or type(self.quality) is not ImportQuality:
            raise ValueError('Report requires exact immutable coordinate and quality records')
        if (type(self.notices) is not tuple or len(self.notices) > 200
                or any(type(notice) is not SvgNotice for notice in self.notices)):
            raise ValueError('Report notices must be a bounded immutable SvgNotice tuple')
        for notice in self.notices:
            for value in (notice.code, notice.message, notice.element_id):
                try:
                    value.encode('utf-8')
                except UnicodeEncodeError as error:
                    raise ValueError('Notice text must be strict UTF-8') from error


def _dimension(token: str | None) -> str:
    if token is None:
        return 'absent'
    parse_svg_length(token)
    match = re.search('(px|mm|cm|in|pt|pc)$', token)
    return match[0] if match else 'unitless'


def _coordinates(result: SvgImportResult) -> ImportCoordinates:
    attributes = result.document.root_attributes
    # Validate that recorded facts actually support a viewport; never infer from material bounds.
    resolve_svg_viewport(attributes)
    attrs = dict(attributes)
    width = attrs['width'].strip() if 'width' in attrs else None
    height = attrs['height'].strip() if 'height' in attrs else None
    view_box = parse_svg_numbers(attrs['viewBox']) if 'viewBox' in attrs else None
    aspect = attrs.get('preserveAspectRatio', 'xMidYMid meet').split()
    canonical = 'none' if aspect == ['none'] else aspect[0] + ' meet'
    viewport = result.document.viewport
    return ImportCoordinates(width, height, (_dimension(width), _dimension(height)),
                             view_box, canonical, (viewport.width_mm, viewport.height_mm),
                             viewport.matrix, result.flipped)


def _quality(result: SvgImportResult) -> ImportQuality:
    counts = [0, 0, 0]  # Valid, invalid, empty atomic material components.
    bounds = None
    coordinates = 0
    pending = iter(result.geometry_mm)
    stack = [pending]
    while stack:
        geometry = next(stack[-1], None)
        if geometry is None:
            stack.pop()
            continue
        if not isinstance(geometry, BaseGeometry):
            raise ValueError('Report material must be Shapely geometry')
        if geometry.is_empty:
            counts[2] += 1
        elif geometry.geom_type.startswith('Multi') or geometry.geom_type == 'GeometryCollection':
            stack.append(iter(geometry.geoms))
            continue
        elif geometry.geom_type in ('Polygon', 'LineString', 'Point', 'LinearRing'):
            coordinates += int(get_num_coordinates(geometry))
            if coordinates > MAX_SVG_POINTS:
                raise ValueError('Report material exceeds SVG coordinate budget')
            if geometry.has_z or geometry.has_m:
                raise ValueError('Report material must be planar')
            for point in get_coordinates(geometry):
                for value in point:
                    _number(float(value), 1e9, 'Material coordinate')
            counts[0 if geometry.is_valid else 1] += 1
            current = tuple(float(value) for value in geometry.bounds)
            bounds = current if bounds is None else (
                min(bounds[0], current[0]), min(bounds[1], current[1]),
                max(bounds[2], current[2]), max(bounds[3], current[3]))
        else:
            raise ValueError('Unsupported atomic report geometry')
        if sum(counts) > 500000:
            raise ValueError('Report component count exceeds supported limit')
    paths = tuple(path for rendered in result.rendered for path in rendered.paths_mm)
    closed = sum(path.closed for path in paths)
    return ImportQuality(bounds, sum(counts), *counts, len(paths) - closed, closed,
                         CURVE_TOLERANCE_MM)


def build_import_report(result: SvgImportResult) -> ImportReport:
    """Summarize recorded source facts and existing material, without geometry mutation."""
    if type(result) is not SvgImportResult:
        raise ValueError('Import report requires an exact SVG import result')
    return ImportReport(result.document.source_name, result.document.source_sha256,
                        _coordinates(result), _quality(result), result.notices)
