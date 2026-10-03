"""Detached immutable raster source, physical grid and canonical firing mask."""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_CEILING
from hashlib import sha256
import math
import struct
import numpy as np

MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_JSON_BYTES = 256 * 1024 * 1024


def finite_positive(value: object, name: str) -> None:
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} requires a positive finite number')


def integer_range(value: object, minimum: int, maximum: int, name: str) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} requires an integer in {minimum}..{maximum}')


def booleans(instance: object, names: tuple[str, ...]) -> None:
    for name in names:
        if type(getattr(instance, name)) is not bool:
            raise ValueError(f'{name} requires bool')


def frozen_array(value: np.ndarray, dtype: object, shape: tuple[int, ...]) -> np.ndarray:
    """Own an immutable byte snapshot, so callers cannot re-enable writes."""
    if not isinstance(value, np.ndarray) or value.dtype != dtype or value.shape != shape:
        raise ValueError(f'Array requires dtype {dtype} and shape {shape}')
    return np.frombuffer(value.tobytes(order='C'), dtype=dtype).reshape(shape)


@dataclass(frozen=True)
class PreparationSettings:
    requested_width_mm: float
    requested_height_mm: float
    requested_dpi: float = 508.0
    threshold: int = 128
    invert: bool = False
    mirror_x: bool = False
    mirror_y: bool = False
    quarter_turns: int = 0
    crop_rect: tuple[float, float, float, float] | None = None
    normalization_version: int = 1

    def __post_init__(self) -> None:
        for name in ('requested_width_mm', 'requested_height_mm', 'requested_dpi'):
            finite_positive(getattr(self, name), name)
        integer_range(self.threshold, 1, 255, 'threshold')
        integer_range(self.quarter_turns, 0, 3, 'quarter_turns')
        booleans(self, ('invert', 'mirror_x', 'mirror_y'))
        if type(self.normalization_version) is not int or self.normalization_version != 1:
            raise ValueError('Unsupported normalization_version')
        if self.crop_rect is not None:
            rect = self.crop_rect
            if type(rect) is not tuple or len(rect) != 4 or any(
                type(v) not in (int, float) or not math.isfinite(v) for v in rect
            ) or min(rect[:2]) < 0 or rect[2] <= rect[0] or rect[3] <= rect[1]:
                raise ValueError('crop_rect requires a positive source-coordinate rectangle')


@dataclass(frozen=True)
class RasterGrid:
    requested_width_mm: float
    requested_height_mm: float
    requested_dpi: float
    width_px: int = field(init=False)
    height_px: int = field(init=False)

    def __post_init__(self) -> None:
        for name in ('requested_width_mm', 'requested_height_mm', 'requested_dpi'):
            finite_positive(getattr(self, name), name)
        pitch = Decimal('25.4') / Decimal(str(self.requested_dpi))
        finite_positive(float(pitch), 'INVALID_GRID: derived pitch')
        sizes = [int((Decimal(str(value)) / pitch).to_integral_value(rounding=ROUND_CEILING))
                 for value in (self.requested_width_mm, self.requested_height_mm)]
        if sizes[0] * sizes[1] > MAX_PIXELS:
            raise ValueError('RASTER_LIMIT_EXCEEDED: output exceeds 40 million pixels')
        for size in sizes: finite_positive(float(pitch * size), 'INVALID_GRID: canvas extent')
        object.__setattr__(self, 'width_px', sizes[0])
        object.__setattr__(self, 'height_px', sizes[1])

    @property
    def pitch_mm(self) -> float:
        return float(Decimal('25.4') / Decimal(str(self.requested_dpi)))

    @property
    def canvas_width_mm(self) -> float:
        return self.width_px * self.pitch_mm

    @property
    def canvas_height_mm(self) -> float:
        return self.height_px * self.pitch_mm

    def valid_area(self) -> np.ndarray:
        """Exclude pixel centres outside the requested viewport, even for inverse jobs."""
        x = (np.arange(self.width_px) + .5) * self.pitch_mm < self.requested_width_mm
        y = (np.arange(self.height_px) + .5) * self.pitch_mm < self.requested_height_mm
        return y[:, None] & x[None, :]

    def pixel_center(self, row: int, column: int) -> tuple[float, float]:
        integer_range(row, 0, self.height_px - 1, 'row')
        integer_range(column, 0, self.width_px - 1, 'column')
        return ((column + .5) * self.pitch_mm, (self.height_px - row - .5) * self.pitch_mm)


def build_grid(preparation: PreparationSettings) -> RasterGrid:
    return RasterGrid(preparation.requested_width_mm, preparation.requested_height_mm,
                      preparation.requested_dpi)


@dataclass(frozen=True, eq=False)
class RasterFrame:
    rgba: np.ndarray
    grid: RasterGrid
    valid_area: np.ndarray

    def __post_init__(self) -> None:
        shape = (self.grid.height_px, self.grid.width_px)
        object.__setattr__(self, 'rgba', frozen_array(self.rgba, np.uint8, (*shape, 4)))
        object.__setattr__(self, 'valid_area', frozen_array(self.valid_area, np.bool_, shape))


@dataclass(frozen=True, eq=False)
class BurnMask:
    burn: np.ndarray
    grid: RasterGrid
    sha256: str = field(init=False)
    black_pixel_count: int = field(init=False)

    def __post_init__(self) -> None:
        shape = (self.grid.height_px, self.grid.width_px)
        data = frozen_array(self.burn, np.bool_, shape)
        payload = b'MCAM-MASK-1\0' + struct.pack('>II', self.grid.width_px, self.grid.height_px)
        digest = sha256(payload + np.packbits(data, axis=None, bitorder='big').tobytes()).hexdigest()
        object.__setattr__(self, 'burn', data)
        object.__setattr__(self, 'sha256', digest)
        object.__setattr__(self, 'black_pixel_count', int(np.count_nonzero(data)))


@dataclass(frozen=True)
class SourceInfo:
    kind: str
    media_type: str
    page_count: int = 1
    native_size_px: tuple[int, int] | None = None
    suggested_size_mm: tuple[float, float] | None = None
    size_origin: str = 'default_508dpi'
    import_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in ('bitmap', 'svg', 'pdf', 'geometry_snapshot'):
            raise ValueError('UNSUPPORTED_SOURCE_FORMAT')
        integer_range(self.page_count, 1, 10000, 'page_count')
        if self.native_size_px is not None:
            if type(self.native_size_px) is not tuple or len(self.native_size_px) != 2:
                raise ValueError('native_size_px requires a pair')
            for value in self.native_size_px: integer_range(value, 1, MAX_PIXELS, 'native_size_px')
            if math.prod(self.native_size_px) > MAX_PIXELS: raise ValueError('RASTER_LIMIT_EXCEEDED')
        if self.suggested_size_mm is not None:
            if type(self.suggested_size_mm) is not tuple or len(self.suggested_size_mm) != 2:
                raise ValueError('suggested_size_mm requires a pair')
            for value in self.suggested_size_mm: finite_positive(value, 'suggested_size_mm')
        if type(self.import_notes) is not tuple or any(type(n) is not str for n in self.import_notes):
            raise ValueError('import_notes requires a tuple of strings')


@dataclass(frozen=True)
class SourceAsset:
    name: str
    data: bytes
    info: SourceInfo
    page_index: int = 0
    sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.data) is not bytes or not 1 <= len(self.data) <= MAX_SOURCE_BYTES:
            raise ValueError('SOURCE_TOO_LARGE: source requires 1..64MiB of bytes')
        if type(self.name) is not str or not self.name or len(self.name.encode('utf-8')) > 1024:
            raise ValueError('source requires a bounded nonempty display name')
        if not isinstance(self.info, SourceInfo): raise ValueError('source.info requires SourceInfo')
        integer_range(self.page_index, 0, self.info.page_count - 1, 'PAGE_OUT_OF_RANGE')
        object.__setattr__(self, 'sha256', sha256(self.data).hexdigest())
