"""Immutable physical Excellon operations and analytic capsule-footprint validation."""
from dataclasses import dataclass
import math

from shapely.geometry import LineString, Point

from .placement import Point2D


def _number(value: object, *, positive: bool = False) -> None:
    if type(value) not in (int, float):
        raise ValueError('Excellon dimensions require finite nonboolean numbers')
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError('Excellon dimension exceeds supported magnitude') from error
    if not math.isfinite(number) or abs(number) > 1e9 or (positive and number <= 0):
        raise ValueError('Excellon dimension exceeds supported finite range')


def _point(point: Point2D) -> None:
    if type(point) is not tuple or len(point) != 2:
        raise ValueError('Excellon position requires an immutable XY pair')
    for coordinate in point:
        _number(coordinate)


def _axis(start: Point2D, end: Point2D | None) -> None:
    _point(start)
    if end is not None:
        _point(end)
        if start == end:
            raise ValueError('Excellon slot endpoints must be distinct')


@dataclass(frozen=True)
class ExcellonTool:
    diameter_mm: float
    drills_mm: tuple[Point2D, ...]
    slots_mm: tuple[tuple[Point2D, Point2D], ...]

    def __post_init__(self) -> None:
        _number(self.diameter_mm, positive=True)
        if (type(self.drills_mm) is not tuple or type(self.slots_mm) is not tuple
                or not 1 <= len(self.drills_mm) + len(self.slots_mm) <= 1000):
            raise ValueError('Excellon tool requires 1..1000 immutable drill or slot operations')
        for point in self.drills_mm:
            _point(point)
        for slot in self.slots_mm:
            if type(slot) is not tuple or len(slot) != 2:
                raise ValueError('Excellon slot requires two immutable XY endpoints')
            _axis(*slot)


def operation_distance(start: Point2D, end: Point2D | None,
                       other_start: Point2D, other_end: Point2D | None) -> float:
    """Measure exact centreline separation; None end denotes a drill, not a degenerate slot."""
    _axis(start, end)
    _axis(other_start, other_end)
    if end is None and other_end is None:
        return math.dist(start, other_start)
    first = Point(start) if end is None else LineString((start, end))
    second = Point(other_start) if other_end is None else LineString((other_start, other_end))
    return float(first.distance(second))


def validate_excellon_tools(tools: tuple[ExcellonTool, ...]) -> None:
    """Validate final tools unchanged, rejecting every incompatible capsule overlap."""
    if (type(tools) is not tuple or not 1 <= len(tools) <= 1000
            or any(type(tool) is not ExcellonTool for tool in tools)):
        raise ValueError('Excellon tools require 1..1000 exact immutable records')
    count = 0
    for tool in tools:
        tool.__post_init__()
        count += len(tool.drills_mm) + len(tool.slots_mm)
        if count > 1000:
            raise ValueError('Excellon tools exceed the 1000 operation limit')
    operations = [(point, None, tool.diameter_mm) for tool in tools for point in tool.drills_mm]
    operations.extend((start, end, tool.diameter_mm) for tool in tools for start, end in tool.slots_mm)
    for index, (start, end, diameter) in enumerate(operations):
        for other_start, other_end, other_diameter in operations[index + 1:]:
            if operation_distance(start, end, other_start, other_end) < (diameter + other_diameter) / 2:
                raise ValueError('Excellon operations have overlapping footprints; revise the selection or source')
