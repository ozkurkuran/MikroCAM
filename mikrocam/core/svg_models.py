"""Immutable bounded SVG source facts and physical geometry results."""
from dataclasses import dataclass
from itertools import chain
import math
import re
from shapely import get_coordinates, get_num_coordinates
from shapely.geometry.base import BaseGeometry
from .placement import Affine2D, Point2D, _finite_real
MAX_SVG_BYTES = 16777216
MAX_SVG_ELEMENTS = 10000
MAX_SVG_DEPTH = 64
MAX_SVG_REFERENCE_DEPTH = 32
MAX_SVG_POINTS = 500000
MAX_ELEMENT_POINTS = 100000
MAX_SVG_RINGS = 256
CURVE_TOLERANCE_MM = 0.01

def _text(value: str, limit: int, label: str, empty: bool=True) -> None:
    if type(value) is not str or len(value) > limit or (not empty and (not value)):
        raise ValueError(f'{label} must be text within {limit} characters')

def _number(value: float, limit: float, label: str) -> float:
    result = _finite_real(value, label)
    if abs(result) > limit:
        raise ValueError(f'{label} exceeds supported magnitude')
    return result

def validate_affine(matrix: Affine2D) -> None:
    if type(matrix) is not tuple or len(matrix) != 6:
        raise ValueError('Affine matrix must be an immutable six-value tuple')
    values = tuple((_number(value, 1000000000000.0, 'Affine coefficient') for value in matrix))
    determinant = values[0] * values[3] - values[1] * values[2]
    if not math.isfinite(determinant) or determinant == 0:
        raise ValueError('Affine matrix must have a finite nonzero determinant')

def _point(point: Point2D) -> Point2D:
    if type(point) is not tuple or len(point) != 2:
        raise ValueError('SVG point must be an immutable XY tuple')
    return tuple((_number(value, 1000000000.0, 'SVG coordinate') for value in point))

def _notices(notices: tuple['SvgNotice', ...]) -> None:
    if type(notices) is not tuple or len(notices) > 200 or any((type(n) is not SvgNotice for n in notices)):
        raise ValueError('SVG notices must be a bounded immutable notice tuple')

def validate_attributes(attributes: tuple[tuple[str, str], ...]) -> None:
    if type(attributes) is not tuple:
        raise ValueError('SVG attributes must be immutable pairs')
    names, total = (set(), 0)
    for pair in attributes:
        if type(pair) is not tuple or len(pair) != 2:
            raise ValueError('SVG attributes must be immutable string pairs')
        key, value = pair
        _text(key, MAX_SVG_BYTES, 'Attribute name', False)
        _text(value, MAX_SVG_BYTES, 'Attribute value')
        if key in names:
            raise ValueError('Duplicate SVG attribute')
        names.add(key)
        try:
            total += len(key.encode('utf-8')) + len(value.encode('utf-8'))
        except UnicodeEncodeError as error:
            raise ValueError('SVG attributes must encode as strict UTF-8') from error
        if total > MAX_SVG_BYTES:
            raise ValueError('SVG attributes exceed source byte budget')

@dataclass(frozen=True)
class SvgNotice:
    code: str
    message: str
    element_id: str = ''

    def __post_init__(self) -> None:
        _text(self.code, 64, 'Notice code', False)
        _text(self.message, 512, 'Notice message', False)
        _text(self.element_id, 256, 'Element ID')

@dataclass(frozen=True)
class SvgPaint:
    fill: bool = True
    stroke: bool = False
    width: float = 1.0
    linecap: str = 'butt'
    linejoin: str = 'miter'
    miterlimit: float = 4.0
    fill_rule: str = 'nonzero'

    def __post_init__(self) -> None:
        if type(self.fill) is not bool or type(self.stroke) is not bool:
            raise ValueError('SVG paint flags must be boolean')
        width = _number(self.width, 1000000000.0, 'Stroke width')
        miter = _number(self.miterlimit, 1000, 'Miter limit')
        if width < 0 or miter < 0:
            raise ValueError('Stroke width and miter limit must be nonnegative')
        for value, choices in ((self.linecap, ('butt', 'round', 'square')), (self.linejoin, ('miter', 'round', 'bevel')), (self.fill_rule, ('nonzero', 'evenodd'))):
            if type(value) is not str or value not in choices:
                raise ValueError('Unsupported SVG paint policy')
        object.__setattr__(self, 'width', width)
        object.__setattr__(self, 'miterlimit', miter)

@dataclass(frozen=True)
class SvgPath:
    points: tuple[Point2D, ...]
    closed: bool = False

    def __post_init__(self) -> None:
        if type(self.closed) is not bool or type(self.points) is not tuple or (not 2 <= len(self.points) <= MAX_ELEMENT_POINTS):
            raise ValueError('SVG path requires bounded immutable points and explicit boolean closure')
        points = tuple((_point(point) for point in self.points))
        if self.closed and (len(points) < 4 or points[0] != points[-1]):
            raise ValueError('Closed SVG path needs four coordinates and exact endpoint closure')
        object.__setattr__(self, 'points', points)

@dataclass(frozen=True)
class SvgViewport:
    width_mm: float
    height_mm: float
    matrix: Affine2D
    notices: tuple[SvgNotice, ...] = ()

    def __post_init__(self) -> None:
        for name in ('width_mm', 'height_mm'):
            value = _number(getattr(self, name), 1000000000.0, name)
            if value <= 0:
                raise ValueError('Viewport dimensions must be positive')
            object.__setattr__(self, name, value)
        validate_affine(self.matrix)
        _notices(self.notices)

@dataclass(frozen=True)
class SvgElement:
    element_id: str
    kind: str
    attributes: tuple[tuple[str, str], ...]
    matrix: Affine2D
    paint: SvgPaint
    fill_is_white: bool | None = None

    def __post_init__(self) -> None:
        _text(self.element_id, 256, 'Element ID')
        if type(self.kind) is not str or self.kind not in ('path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon'):
            raise ValueError('Unsupported SVG element kind')
        validate_attributes(self.attributes)
        validate_affine(self.matrix)
        if type(self.paint) is not SvgPaint:
            raise ValueError('SVG element requires immutable paint')
        if self.fill_is_white is not None and type(self.fill_is_white) is not bool:
            raise ValueError('SVG white-fill fact must be boolean or unavailable')

@dataclass(frozen=True)
class SvgDocument:
    source_name: str
    source_sha256: str
    viewport: SvgViewport
    elements: tuple[SvgElement, ...]
    notices: tuple[SvgNotice, ...] = ()
    root_attributes: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _text(self.source_name, 256, 'Source name', False)
        if type(self.source_sha256) is not str or re.fullmatch('[0-9a-f]{64}', self.source_sha256) is None:
            raise ValueError('SVG source requires exact lowercase SHA256')
        if type(self.viewport) is not SvgViewport or type(self.elements) is not tuple or len(self.elements) > MAX_SVG_ELEMENTS:
            raise ValueError('SVG document requires bounded immutable viewport/elements')
        if any((type(element) is not SvgElement for element in self.elements)):
            raise ValueError('SVG document contains invalid elements')
        _notices(self.notices)
        validate_attributes(self.root_attributes)

@dataclass(frozen=True)
class SvgRendered:
    paths_mm: tuple[SvgPath, ...]
    geometry_mm: tuple[BaseGeometry, ...]
    notices: tuple[SvgNotice, ...] = ()

    def __post_init__(self) -> None:
        if type(self.paths_mm) is not tuple or any((type(path) is not SvgPath for path in self.paths_mm)):
            raise ValueError('Rendered paths must be an immutable SVG path tuple')
        if type(self.geometry_mm) is not tuple or any((not isinstance(g, BaseGeometry) for g in self.geometry_mm)):
            raise ValueError('Rendered geometry must be an immutable Shapely tuple')
        if _coordinate_count(self) > MAX_ELEMENT_POINTS or sum((path.closed for path in self.paths_mm)) > MAX_SVG_RINGS:
            raise ValueError('Rendered SVG element exceeds coordinate/ring budget')
        for geometry in self.geometry_mm:
            if geometry.has_z or geometry.has_m or (not geometry.is_valid):
                raise ValueError('SVG geometry must be valid planar geometry')
            if any((not math.isfinite(v) or abs(v) > 1000000000.0 for point in get_coordinates(geometry) for v in point)):
                raise ValueError('SVG geometry coordinates exceed supported finite range')
        _notices(self.notices)

def _coordinate_count(rendered: SvgRendered) -> int:
    return sum((len(path.points) for path in rendered.paths_mm)) + sum((int(get_num_coordinates(g)) for g in rendered.geometry_mm))

@dataclass(frozen=True)
class SvgImportResult:
    document: SvgDocument
    rendered: tuple[SvgRendered, ...]
    flipped: bool = False

    def __post_init__(self) -> None:
        if type(self.flipped) is not bool:
            raise ValueError('SVG import flip fact must be boolean')
        if type(self.document) is not SvgDocument or type(self.rendered) is not tuple or len(self.rendered) != len(self.document.elements) or any((type(value) is not SvgRendered for value in self.rendered)):
            raise ValueError('SVG import requires exactly one immutable result per element')
        if sum((_coordinate_count(value) for value in self.rendered)) > MAX_SVG_POINTS:
            raise ValueError('SVG document exceeds generated coordinate budget')

    @property
    def geometry_mm(self) -> tuple[BaseGeometry, ...]:
        return tuple((g for value in self.rendered for g in value.geometry_mm))

    @property
    def notices(self) -> tuple[SvgNotice, ...]:
        retained, total = ([], 0)
        for notices in chain((self.document.viewport.notices, self.document.notices),
                             (value.notices for value in self.rendered)):
            total += len(notices)
            if len(retained) < 200:
                retained.extend(notices[:200 - len(retained)])
        if total > 200:
            retained[199] = SvgNotice('notices-truncated', f'{total - 199} further notices omitted')
        return tuple(retained)
