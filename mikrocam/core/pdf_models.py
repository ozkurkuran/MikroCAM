"""Strict immutable source, page and physical material records for PDF vectors."""

from dataclasses import dataclass
from hashlib import sha256
import math
import re
from shapely import get_coordinates, get_coordinate_dimension
from shapely.geometry import Polygon
from .placement import Point2D, Affine2D

MAX_PDF_BYTES = 16777216
MAX_PDF_STREAM_BYTES = 8388608
MAX_PDF_PAGES = 128
MAX_PDF_OPERATORS = 50000
MAX_PDF_POINTS = 500000
PDF_TOLERANCE_MM = 0.01
Bounds = tuple[float, float, float, float]


def _number(value: float, label: str, limit: float = 1e9) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} requires a finite nonboolean number")
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f"{label} exceeds bounds") from error
    if not math.isfinite(result) or abs(result) > limit:
        raise ValueError(f"{label} exceeds finite bounds")
    return result


def _integer(value: int, low: int, high: int, label: str) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} requires an integer from {low} to {high}")


def _text(value: str, limit: int, label: str, *, allow_empty: bool = False) -> None:
    if type(value) is not str or not value and not allow_empty:
        raise ValueError(f"{label} requires nonempty text")
    try:
        valid = len(value.encode("utf-8")) <= limit
    except UnicodeError as error:
        raise ValueError(f"{label} requires strict UTF-8") from error
    if not valid:
        raise ValueError(f"{label} exceeds {limit} UTF-8 bytes")


def _hash(value: str) -> None:
    if type(value) is not str or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ValueError("Identity requires lowercase SHA256")


def _tuple_numbers(value: tuple, count: int, label: str) -> tuple[float, ...]:
    if type(value) is not tuple or len(value) != count:
        raise ValueError(f"{label} requires an immutable tuple of {count} numbers")
    return tuple(_number(item, label) for item in value)


def _bounds(value: Bounds) -> Bounds:
    result = _tuple_numbers(value, 4, "Bounds")
    if not 0 < result[2] - result[0] <= 1e9 or not 0 < result[3] - result[1] <= 1e9:
        raise ValueError("Bounds require positive bounded width and height")
    return result


@dataclass(frozen=True)
class PdfPageInfo:
    index: int
    media_box: Bounds
    crop_box: Bounds
    rotation: int
    user_unit: float

    def __post_init__(self) -> None:
        _integer(self.index, 0, 127, "Page index")
        object.__setattr__(self, "media_box", _bounds(self.media_box))
        object.__setattr__(self, "crop_box", _bounds(self.crop_box))
        if not (
            self.media_box[0]
            <= self.crop_box[0]
            < self.crop_box[2]
            <= self.media_box[2]
            and self.media_box[1]
            <= self.crop_box[1]
            < self.crop_box[3]
            <= self.media_box[3]
        ):
            raise ValueError("Crop box must lie within media box")
        if type(self.rotation) is not int or self.rotation not in (0, 90, 180, 270):
            raise ValueError("Page rotation requires a quarter turn")
        unit = _number(self.user_unit, "UserUnit", 75000)
        if unit <= 0:
            raise ValueError("UserUnit must be positive")
        object.__setattr__(self, "user_unit", unit)
        factor = unit * 25.4 / 72
        if any(abs(v * factor) > 1e9 for v in self.media_box) or any(
            (self.media_box[i + 2] - self.media_box[i]) * factor > 1e9 for i in (0, 1)
        ):
            raise ValueError("Physical page exceeds 1e9 mm")


@dataclass(frozen=True)
class PdfDocumentInfo:
    source_name: str
    source_sha256: str
    pages: tuple[PdfPageInfo, ...]

    def __post_init__(self) -> None:
        _text(self.source_name, 256, "Source name")
        _hash(self.source_sha256)
        if (
            type(self.pages) is not tuple
            or not 1 <= len(self.pages) <= MAX_PDF_PAGES
            or any(
                type(page) is not PdfPageInfo or page.index != index
                for index, page in enumerate(self.pages)
            )
        ):
            raise ValueError(
                "Document requires 1..128 consecutively indexed immutable pages"
            )


@dataclass(frozen=True)
class PdfOptions:
    page_index: int
    box_mode: str = "crop"
    crop_mm: Bounds | None = None
    flip: bool = False

    def __post_init__(self) -> None:
        _integer(self.page_index, 0, 127, "Page index")
        if type(self.box_mode) is not str or self.box_mode not in ("crop", "media"):
            raise ValueError("Box mode must be crop or media")
        if type(self.flip) is not bool:
            raise ValueError("Flip must be boolean")
        if self.crop_mm is not None:
            value = _bounds(self.crop_mm)
            if value[0] < 0 or value[1] < 0:
                raise ValueError("Physical crop requires nonnegative origin")
            object.__setattr__(self, "crop_mm", value)


def _operand(value: object) -> None:
    if type(value) in (int, float):
        _number(value, "Operand")
    elif type(value) is str:
        _text(value, 128, "Operand text", allow_empty=True)
    elif type(value) is tuple and len(value) <= 64:
        for number in value:
            _number(number, "Array operand")
    else:
        raise ValueError("Unsupported immutable PDF operand")


@dataclass(frozen=True)
class PdfCommand:
    operator: str
    operands: tuple

    def __post_init__(self) -> None:
        _text(self.operator, 16, "Operator")
        if not self.operator.isascii():
            raise ValueError("Operator requires ASCII")
        if type(self.operands) is not tuple or len(self.operands) > 8:
            raise ValueError("Command requires at most eight immutable operands")
        for value in self.operands:
            _operand(value)


@dataclass(frozen=True)
class PdfProgram:
    document: PdfDocumentInfo
    page_index: int
    commands: tuple[PdfCommand, ...]

    def __post_init__(self) -> None:
        if type(self.document) is not PdfDocumentInfo:
            raise ValueError("Program requires immutable document facts")
        _integer(self.page_index, 0, len(self.document.pages) - 1, "Selected page")
        if (
            type(self.commands) is not tuple
            or len(self.commands) > MAX_PDF_OPERATORS
            or any(type(command) is not PdfCommand for command in self.commands)
        ):
            raise ValueError("Program requires at most 50000 immutable commands")


@dataclass(frozen=True)
class PdfImportReport:
    source_name: str
    source_sha256: str
    page_count: int
    page: PdfPageInfo
    options: PdfOptions
    viewport_mm: Point2D
    matrix_mm: Affine2D
    bounds_mm: Bounds
    geometry_count: int
    path_count: int
    point_count: int
    geometry_sha256: str
    precision_mm: float = PDF_TOLERANCE_MM
    notices: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.source_name, 256, "Source name")
        _hash(self.source_sha256)
        _hash(self.geometry_sha256)
        _integer(self.page_count, 1, 128, "Page count")
        if (
            type(self.page) is not PdfPageInfo
            or type(self.options) is not PdfOptions
            or not (self.page.index == self.options.page_index < self.page_count)
        ):
            raise ValueError("Report page and options must agree")
        viewport = _tuple_numbers(self.viewport_mm, 2, "Viewport")
        if min(viewport) <= 0:
            raise ValueError("Viewport requires positive dimensions")
        object.__setattr__(self, "viewport_mm", viewport)
        matrix = _tuple_numbers(self.matrix_mm, 6, "Affine")
        determinant = matrix[0] * matrix[3] - matrix[1] * matrix[2]
        if not math.isfinite(determinant) or determinant == 0:
            raise ValueError("Affine must be nonsingular and finite")
        object.__setattr__(self, "matrix_mm", matrix)
        object.__setattr__(self, "bounds_mm", _bounds(self.bounds_mm))
        _integer(self.geometry_count, 1, MAX_PDF_POINTS, "Geometry count")
        _integer(self.path_count, 1, 10000, "Path count")
        _integer(self.point_count, 1, MAX_PDF_POINTS, "Point count")
        if _number(self.precision_mm, "Precision") != PDF_TOLERANCE_MM:
            raise ValueError("PDF precision must be exactly 0.01 mm")
        if type(self.notices) is not tuple or len(self.notices) > 200:
            raise ValueError("Notices require an immutable tuple within 200 items")
        for notice in self.notices:
            _text(notice, 512, "Notice")


def geometry_facts(geometry: tuple[Polygon, ...]) -> tuple[Bounds, int]:
    """Validate bounded polygon material and return aggregate bounds and coordinate count."""
    if type(geometry) is not tuple or not 1 <= len(geometry) <= MAX_PDF_POINTS:
        raise ValueError(
            "PDF material requires a nonempty bounded immutable polygon tuple"
        )
    bounds = None
    count = 0
    for polygon in geometry:
        if (
            type(polygon) is not Polygon
            or polygon.is_empty
            or get_coordinate_dimension(polygon) != 2
        ):
            raise ValueError("PDF material requires valid nonempty planar Polygons")
        size = len(polygon.exterior.coords) + sum(
            len(ring.coords) for ring in polygon.interiors
        )
        count += size
        if count > MAX_PDF_POINTS:
            raise ValueError("PDF material exceeds 500000 coordinates")
        if not polygon.is_valid:
            raise ValueError("PDF material requires valid Polygons")
        if any(
            not math.isfinite(float(v)) or abs(v) > 1e9
            for pair in get_coordinates(polygon)
            for v in pair
        ):
            raise ValueError("PDF material has nonfinite or out-of-bounds coordinates")
        box = polygon.bounds
        bounds = (
            box
            if bounds is None
            else (
                min(bounds[0], box[0]),
                min(bounds[1], box[1]),
                max(bounds[2], box[2]),
                max(bounds[3], box[3]),
            )
        )
    return _bounds(bounds), count


def geometry_sha256(geometry: tuple[Polygon, ...]) -> str:
    """Hash original WKB with unambiguous lengths in deterministic tuple order."""
    geometry_facts(geometry)
    digest = sha256()
    for polygon in geometry:
        data = polygon.wkb
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


@dataclass(frozen=True)
class PdfGeometryResult:
    report: PdfImportReport
    geometry_mm: tuple[Polygon, ...]

    def __post_init__(self) -> None:
        if type(self.report) is not PdfImportReport:
            raise ValueError("PDF material requires an immutable import report")
        bounds, count = geometry_facts(self.geometry_mm)
        if (
            bounds != self.report.bounds_mm
            or count != self.report.point_count
            or len(self.geometry_mm) != self.report.geometry_count
            or geometry_sha256(self.geometry_mm) != self.report.geometry_sha256
        ):
            raise ValueError("PDF material and report facts disagree")


@dataclass(frozen=True)
class PdfImportReview:
    source_bytes: bytes
    result: PdfGeometryResult

    def __post_init__(self) -> None:
        if (
            type(self.source_bytes) is not bytes
            or not 1 <= len(self.source_bytes) <= MAX_PDF_BYTES
        ):
            raise ValueError("PDF review requires 1..16MiB immutable source bytes")
        if (
            type(self.result) is not PdfGeometryResult
            or sha256(self.source_bytes).hexdigest() != self.result.report.source_sha256
        ):
            raise ValueError("PDF source bytes and result identity disagree")
