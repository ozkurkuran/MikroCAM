"""Deterministic grouping of explicitly selected millimetre drill candidates."""
from dataclasses import dataclass
import math

from .svg_drills import DrillReview


def _number(value: object, *, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise ValueError('Drill dimensions must be finite nonboolean numbers')
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError('Drill dimension exceeds supported magnitude') from error
    if not math.isfinite(number) or abs(number) > 1e9 or (positive and number <= 0):
        raise ValueError('Drill dimension exceeds supported finite range')
    return number


@dataclass(frozen=True)
class DrillTool:
    diameter_mm: float
    centers_mm: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        _number(self.diameter_mm, positive=True)
        if type(self.centers_mm) is not tuple or not 1 <= len(self.centers_mm) <= 1000:
            raise ValueError('Drill tool requires 1..1000 immutable centres')
        for center in self.centers_mm:
            if type(center) is not tuple or len(center) != 2:
                raise ValueError('Drill centre must be an immutable XY pair')
            for coordinate in center:
                _number(coordinate)


def group_drill_selection(review: DrillReview, indices: tuple[int, ...]) -> tuple[DrillTool, ...]:
    """Group selected evidence by total diameter spread, independent of selection order."""
    if type(review) is not DrillReview:
        raise ValueError('Drill grouping requires an exact DrillReview')
    if type(indices) is not tuple or not 1 <= len(indices) <= 1000:
        raise ValueError('Select 1..1000 immutable candidate indices')
    if any(type(index) is not int or not 0 <= index < len(review.candidates) for index in indices):
        raise ValueError('Selected candidate indices must be exact integers within the review')
    if len(set(indices)) != len(indices):
        raise ValueError('Selected candidate indices must be unique')
    selected = sorted((review.candidates[index] for index in indices),
                      key=lambda candidate: (candidate.diameter_mm, candidate.center_mm))
    groups = []
    current = []
    for candidate in selected:
        spread = candidate.diameter_mm - current[0].diameter_mm if current else 0
        # Preserve the inclusive nominal boundary despite decimal subtraction roundoff.
        if current and spread > 0.01 and not math.isclose(spread, 0.01, rel_tol=0, abs_tol=1e-12):
            groups.append(current)
            current = []
        current.append(candidate)
    groups.append(current)
    tools = tuple(DrillTool(math.fsum(item.diameter_mm for item in group) / len(group),
                            tuple(sorted(item.center_mm for item in group))) for group in groups)
    holes = [(center, tool.diameter_mm / 2) for tool in tools for center in tool.centers_mm]
    for index, (center, radius) in enumerate(holes):
        if any(math.dist(center, other) < radius + other_radius
               for other, other_radius in holes[index + 1:]):
            raise ValueError('Proposed tool diameters produce overlapping holes; revise the selection or source')
    return tools
