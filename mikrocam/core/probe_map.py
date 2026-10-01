"""Immutable G54 work-mm grids, reviewed machine routes and truthful measurements."""
from dataclasses import dataclass
import math


def _number(value: float, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f'{label} requires a finite nonboolean number')
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f'{label} exceeds the coordinate bound') from error
    if not math.isfinite(result) or abs(result) > 1000000:
        raise ValueError(f'{label} exceeds the finite 1000000mm bound')
    return result


def _axis(values: tuple[float, ...], label: str) -> tuple[float, ...]:
    if type(values) is not tuple or not 2 <= len(values) <= 64:
        raise ValueError(f'{label} requires an immutable tuple of 2..64 coordinates')
    numbers = tuple(_number(value, label) for value in values)
    if any(a >= b for a, b in zip(numbers, numbers[1:])):
        raise ValueError(f'{label} must be strictly increasing')
    return numbers


def _xyz(value: tuple[float, float, float], label: str) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise ValueError(f'{label} requires an immutable XYZ tuple')
    return tuple(_number(number, label) for number in value)


@dataclass(frozen=True)
class ProbeGrid:
    x_mm: tuple[float, ...]
    y_mm: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'x_mm', _axis(self.x_mm, 'Grid X'))
        object.__setattr__(self, 'y_mm', _axis(self.y_mm, 'Grid Y'))
        if self.count > 1024:
            raise ValueError('Probe grid exceeds 1024 points')

    @property
    def points(self) -> tuple[tuple[float, float], ...]:
        return tuple((x, y) for y in self.y_mm for x in self.x_mm)

    @property
    def count(self) -> int:
        return len(self.x_mm) * len(self.y_mm)


def uniform_grid(x_min: float, x_max: float, nx: int,
                 y_min: float, y_max: float, ny: int) -> ProbeGrid:
    """Construct a bounded row-major grid with exact requested axis endpoints."""
    if any(type(n) is not int or not 2 <= n <= 64 for n in (nx, ny)) or nx * ny > 1024:
        raise ValueError('Grid counts require integers 2..64 with at most 1024 points')
    axes = []
    for low, high, count in ((x_min, x_max, nx), (y_min, y_max, ny)):
        low, high = _number(low, 'Grid minimum'), _number(high, 'Grid maximum')
        if low >= high:
            raise ValueError('Grid minimum must be below maximum')
        axes.append((low,) + tuple(low + (high - low) * i / (count - 1)
                                  for i in range(1, count - 1)) + (high,))
    return ProbeGrid(*axes)


@dataclass(frozen=True)
class ProbePlan:
    grid: ProbeGrid
    safe_z_mm: float
    min_z_mm: float
    probe_feed_mm_min: float
    travel_feed_mm_min: float
    machine_min_mm: tuple[float, float, float]
    machine_max_mm: tuple[float, float, float]
    initial_machine_mm: tuple[float, float, float]
    g54_offset_mm: tuple[float, float, float]
    timeout_seconds: float = 30

    def __post_init__(self) -> None:
        if type(self.grid) is not ProbeGrid:
            raise ValueError('Probe plan requires an exact ProbeGrid')
        for field in ('safe_z_mm', 'min_z_mm', 'probe_feed_mm_min',
                      'travel_feed_mm_min', 'timeout_seconds'):
            object.__setattr__(self, field, _number(getattr(self, field), field))
        for field in ('machine_min_mm', 'machine_max_mm', 'initial_machine_mm', 'g54_offset_mm'):
            object.__setattr__(self, field, _xyz(getattr(self, field), field))
        if not 0 < self.safe_z_mm - self.min_z_mm <= 100:
            raise ValueError('Probe downward travel must be positive and at most 100mm')
        if any(not .01 <= feed <= 10000 for feed in (self.probe_feed_mm_min, self.travel_feed_mm_min)):
            raise ValueError('Probe and travel feeds require .01..10000mm/min')
        if not 3 <= self.timeout_seconds <= 300:
            raise ValueError('Probe response deadline requires 3..300 seconds')
        if any(low >= high for low, high in zip(self.machine_min_mm, self.machine_max_mm)):
            raise ValueError('Machine minimum XYZ must be below maximum XYZ')
        if any(not low <= value <= high for low, value, high in
               zip(self.machine_min_mm, self.initial_machine_mm, self.machine_max_mm)):
            raise ValueError('Initial machine position lies outside the envelope')
        for axis, values in enumerate((self.grid.x_mm, self.grid.y_mm, (self.min_z_mm, self.safe_z_mm))):
            if any(not self.machine_min_mm[axis] <= value + self.g54_offset_mm[axis] <= self.machine_max_mm[axis]
                   for value in values):
                raise ValueError('Probe route endpoint lies outside the machine envelope')
        if self.safe_z_mm + self.g54_offset_mm[2] < self.initial_machine_mm[2]:
            raise ValueError('Initial clearance movement must retract upward')


@dataclass(frozen=True)
class ProbeMap:
    grid: ProbeGrid
    heights_mm: tuple[float | None, ...]
    g54_offset_mm: tuple[float, float, float]
    outcome: str
    origin: str

    def __post_init__(self) -> None:
        if type(self.grid) is not ProbeGrid:
            raise ValueError('Probe map requires an exact ProbeGrid')
        if type(self.heights_mm) is not tuple or len(self.heights_mm) != self.grid.count:
            raise ValueError('Probe heights require an immutable tuple matching the grid count')
        missing, heights = False, []
        for value in self.heights_mm:
            if value is None:
                missing = True
                heights.append(None)
            elif missing:
                raise ValueError('Probe measurements must be a row-major prefix')
            else:
                heights.append(_number(value, 'Measured work Z'))
        object.__setattr__(self, 'heights_mm', tuple(heights))
        object.__setattr__(self, 'g54_offset_mm', _xyz(self.g54_offset_mm, 'G54 offset'))
        if type(self.outcome) is not str or self.outcome not in ('incomplete', 'complete', 'failed', 'aborted'):
            raise ValueError('Unsupported probe outcome')
        if type(self.origin) is not str or self.origin not in ('measured', 'simulated'):
            raise ValueError('Unsupported probe origin')
        if self.outcome == 'complete' and missing:
            raise ValueError('Complete probe outcome requires every measurement')

    @property
    def completed(self) -> int:
        return sum(value is not None for value in self.heights_mm)

    @property
    def complete(self) -> bool:
        return self.outcome == 'complete'
