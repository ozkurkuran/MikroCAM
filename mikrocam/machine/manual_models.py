"""Immutable bounded manual requests and provisional GRBL query evidence."""
from dataclasses import dataclass
from math import isfinite

from .models import XYZ, _validate_xyz


WCS_NAMES = ('G54', 'G55', 'G56', 'G57', 'G58', 'G59')
PARAMETER_NAMES = WCS_NAMES + ('G92', 'TLO')
ZERO_AXES = (('X', 'Y'), ('Z',), ('X', 'Y', 'Z'))


def _finite(value: float) -> float:
    if type(value) not in (int, float):
        raise ValueError('Numeric evidence must be finite and not boolean')
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError('Numeric evidence must be finite') from error
    if not isfinite(result):
        raise ValueError('Numeric evidence must be finite')
    return result


@dataclass(frozen=True)
class JogRequest:
    axis: str
    distance_mm: float
    feed_mm_min: float

    def __post_init__(self) -> None:
        if self.axis not in ('X', 'Y', 'Z'):
            raise ValueError('Jog axis must be X, Y or Z')
        distance, feed = _finite(self.distance_mm), _finite(self.feed_mm_min)
        if distance not in (.1, -.1, 1., -1., 10., -10.) or feed not in (100., 300., 600.):
            raise ValueError('Jog requires a supported signed step and feed preset')
        object.__setattr__(self, 'distance_mm', distance)
        object.__setattr__(self, 'feed_mm_min', feed)


@dataclass(frozen=True)
class ZeroRequest:
    axes: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.axes) is not tuple or self.axes not in ZERO_AXES:
            raise ValueError('Zero axes must be exactly XY, Z or XYZ')


@dataclass(frozen=True)
class SelectG54Request:
    """Explicit coordinate-system selection, without changing any stored zero."""


@dataclass(frozen=True)
class ModalState:
    work_system: str
    units: str
    distance: str
    spindle: str
    coolant: tuple[str, ...]

    def __post_init__(self) -> None:
        if (self.work_system not in WCS_NAMES or self.units not in ('G20', 'G21')
                or self.distance not in ('G90', 'G91') or self.spindle not in ('M3', 'M4', 'M5')):
            raise ValueError('Unsupported GRBL modal evidence')
        if (type(self.coolant) is not tuple
                or self.coolant not in (('M9',), ('M7',), ('M8',), ('M7', 'M8'), ('M8', 'M7'))):
            raise ValueError('Coolant evidence must be unique M7/M8 modes or M9 alone')


@dataclass(frozen=True)
class ParameterRecord:
    name: str
    value: XYZ | float

    def __post_init__(self) -> None:
        if self.name not in PARAMETER_NAMES:
            raise ValueError('Unsupported parameter record')
        if self.name == 'TLO':
            object.__setattr__(self, 'value', _finite(self.value))
        else:
            if self.value is None:
                raise ValueError('Parameter coordinate evidence is required')
            _validate_xyz(self.value)
            object.__setattr__(self, 'value', tuple(float(axis) for axis in self.value))


@dataclass(frozen=True)
class StartupRecord:
    index: int
    block: str

    def __post_init__(self) -> None:
        if type(self.index) is not int or self.index not in (0, 1):
            raise ValueError('Startup record index must be 0 or 1')
        if (not isinstance(self.block, str) or len(self.block) > 80
                or any(not 32 <= ord(char) <= 126 for char in self.block)):
            raise ValueError('Startup block must be at most 80 printable ASCII bytes')
