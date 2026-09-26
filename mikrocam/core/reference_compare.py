"""Explicit absolute metrics for reference geometry and ordered CAM paths in mm."""
from collections.abc import Sequence
from dataclasses import dataclass
import math

from shapely import from_wkb, get_num_coordinates, to_wkb, union_all
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

from .placement import Point2D, _finite_real, _point, _validate_geometry


MAX_WKB_BYTES = 64 * 1024 * 1024
MAX_PATHS = 200_000
MAX_VERTICES = 2_000_000
MAX_BATCH_VERTICES = 4_000_000


def _tolerance(value: float, label: str) -> float:
    result = _finite_real(value, label)
    if result < 0:
        raise ValueError(f'{label} must be nonnegative')
    return result


def _decode(value: str) -> BaseGeometry:
    if not isinstance(value, str) or not value or len(value) % 2:
        raise ValueError('WKB must be a nonempty hex string')
    if len(value) > MAX_WKB_BYTES * 2:
        raise ValueError('WKB size exceeds the resource limit')
    if any(character not in '0123456789abcdefABCDEF' for character in value):
        raise ValueError('WKB must contain only hex digits')
    try:
        geometry = from_wkb(value)
        _validate_geometry(geometry)
        if geometry.is_empty:
            raise ValueError('Reference geometry must be nonempty')
        encoded = to_wkb(geometry, hex=True, byte_order=1, output_dimension=2, flavor='iso')
        if encoded != value.upper():
            raise ValueError('WKB requires exact 2D little-endian ISO encoding without trailing data')
    except (GEOSException, TypeError) as error:
        raise ValueError(f'Invalid reference WKB: {error}') from error
    return geometry


def _topology(geometry: BaseGeometry) -> tuple:
    if geometry.geom_type == 'Polygon':
        return ('Polygon', len(geometry.interiors))
    if hasattr(geometry, 'geoms'):
        return (geometry.geom_type, tuple(sorted(_topology(part) for part in geometry.geoms)))
    return (geometry.geom_type,)


def _metric(value: float) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError('Reference metric overflowed or is undefined')
    return result


@dataclass(frozen=True)
class GeometryComparison:
    """GEOS discrete vertex Hausdorff and symmetric-difference area, in mm/mm²."""
    matches: bool
    topology_equal: bool
    hausdorff_mm: float | None
    symmetric_difference_mm2: float
    bounds_delta_mm: tuple[float, float, float, float]


def compare_geometry(expected_wkb: str, actual_wkb: str, *, distance_mm: float,
                     area_mm2: float) -> GeometryComparison:
    """Compare sets without treating orientation/order as geometric change.

    Topology, absolute distance and absolute area must all pass. Distance is the
    GEOS discrete vertex metric; this is not a continuous maximum-distance proof.
    Bounds deltas are diagnostic evidence, not an additional implicit tolerance.
    Distance is omitted (None) when topology/area already proves a difference.
    """
    distance = _tolerance(distance_mm, 'distance_mm')
    area = _tolerance(area_mm2, 'area_mm2')
    expected, actual = _decode(expected_wkb), _decode(actual_wkb)
    return _compare_sets(expected, actual, distance, area)


def _compare_sets(expected: BaseGeometry, actual: BaseGeometry,
                  distance: float, area: float) -> GeometryComparison:
    topology = _topology(expected) == _topology(actual)
    bounds = tuple(_metric(abs(first - second)) for first, second in zip(expected.bounds, actual.bounds))
    try:
        if expected.equals(actual):
            hausdorff, difference = 0.0, 0.0
        else:
            difference = _metric(expected.symmetric_difference(actual).area)
            hausdorff = (_metric(expected.hausdorff_distance(actual))
                         if topology and difference <= area else None)
    except GEOSException as error:
        raise ValueError(f'Reference geometry comparison failed: {error}') from error
    return GeometryComparison(topology and hausdorff is not None
                              and hausdorff <= distance and difference <= area,
                              topology, hausdorff, difference, bounds)


def _geometry_union(values: Sequence[str]) -> BaseGeometry:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or not values:
        raise ValueError('Geometry batch requires a nonempty sequence of WKB values')
    geometries, vertices = [], 0
    for value in values:
        geometry = _decode(value)
        vertices += int(get_num_coordinates(geometry))
        if vertices > MAX_BATCH_VERTICES:
            raise ValueError('Geometry batch vertex count exceeds the resource limit')
        geometries.append(geometry)
    try:
        result = union_all(geometries)
        _validate_geometry(result)
        return result
    except GEOSException as error:
        raise ValueError(f'Reference geometry union failed: {error}') from error


def compare_geometry_sets(expected: Sequence[str], actual: Sequence[str], *,
                          distance_mm: float, area_mm2: float) -> GeometryComparison:
    """Compare physical sets independently of an engine's geometry batch partition.

    Keep raw batches in captures. Union removes internal partition edges before
    measuring material topology, distance and area; CNC/tool ordering is separate.
    """
    distance = _tolerance(distance_mm, 'distance_mm')
    area = _tolerance(area_mm2, 'area_mm2')
    return _compare_sets(_geometry_union(expected), _geometry_union(actual), distance, area)


@dataclass(frozen=True)
class ReferencePath:
    """One engine-parsed Point/LineString with its original kind and vertex order."""
    kind: tuple[str, ...]
    wkb_hex: str

    def __post_init__(self) -> None:
        if (not isinstance(self.kind, tuple) or not self.kind
                or not all(isinstance(value, str) and value.strip() for value in self.kind)):
            raise ValueError('Path kind must be a nonempty tuple of nonempty strings')
        geometry = _decode(self.wkb_hex)
        if geometry.geom_type not in {'Point', 'LineString'}:
            raise ValueError('Reference paths require Point or LineString geometry')
        object.__setattr__(self, 'wkb_hex', self.wkb_hex.upper())


@dataclass(frozen=True)
class PathComparison:
    """Zero-based differing indices, including unmatched tail paths."""
    matches: bool
    differing_indices: tuple[int, ...]
    expected_count: int
    actual_count: int


def _path_coordinates(paths: Sequence[ReferencePath]) -> list[tuple]:
    if not isinstance(paths, Sequence) or isinstance(paths, (str, bytes)) or not paths:
        raise ValueError('Paths must be a nonempty sequence of ReferencePath values')
    if len(paths) > MAX_PATHS:
        raise ValueError('Path count exceeds the resource limit')
    result, count = [], 0
    for path in paths:
        if not isinstance(path, ReferencePath):
            raise ValueError('Paths must contain only ReferencePath values')
        coordinates = tuple(_decode(path.wkb_hex).coords)
        count += len(coordinates)
        if count > MAX_VERTICES:
            raise ValueError('Path vertex count exceeds the resource limit')
        result.append(coordinates)
    return result


def compare_paths(expected: Sequence[ReferencePath], actual: Sequence[ReferencePath], *,
                  distance_mm: float) -> PathComparison:
    """Keep path kind/count/order, vertex count, direction and repeated coordinates."""
    tolerance = _tolerance(distance_mm, 'distance_mm')
    first, second = _path_coordinates(expected), _path_coordinates(actual)
    differences = []
    for index in range(max(len(first), len(second))):
        if index >= len(first) or index >= len(second):
            differences.append(index)
            continue
        if expected[index].kind != actual[index].kind or len(first[index]) != len(second[index]):
            differences.append(index)
            continue
        if any(_metric(math.dist(a, b)) > tolerance for a, b in zip(first[index], second[index])):
            differences.append(index)
    return PathComparison(not differences, tuple(differences), len(first), len(second))


@dataclass(frozen=True)
class ReferenceTool:
    """Explicit drill diameter and original ordered hit/slot multiplicity, all in mm."""
    id: str
    diameter_mm: float
    drills: tuple[Point2D, ...]
    slots: tuple[tuple[Point2D, Point2D], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError('Tool id must be a nonempty string')
        diameter = _finite_real(self.diameter_mm, 'diameter_mm')
        if diameter <= 0:
            raise ValueError('Tool diameter must be positive')
        if not isinstance(self.drills, tuple) or not isinstance(self.slots, tuple):
            raise ValueError('Drills and slots must be immutable tuples')
        if len(self.drills) + 2 * len(self.slots) > MAX_VERTICES:
            raise ValueError('Drill/slot vertex count exceeds the resource limit')
        drills = tuple(_point(point, 'drill') for point in self.drills)
        slots = []
        for slot in self.slots:
            if not isinstance(slot, tuple) or len(slot) != 2:
                raise ValueError('Slot requires exactly two XY endpoints')
            slots.append((_point(slot[0], 'slot start'), _point(slot[1], 'slot end')))
        object.__setattr__(self, 'diameter_mm', diameter)
        object.__setattr__(self, 'drills', drills)
        object.__setattr__(self, 'slots', tuple(slots))


@dataclass(frozen=True)
class ToolComparison:
    """Zero-based differing tool indices, preserving original tool order."""
    matches: bool
    differing_indices: tuple[int, ...]
    expected_count: int
    actual_count: int


def _tools(values: Sequence[ReferenceTool]) -> None:
    if (not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or not values
            or not all(isinstance(value, ReferenceTool) for value in values)):
        raise ValueError('Tools require a nonempty sequence of ReferenceTool values')
    if len(values) > MAX_PATHS:
        raise ValueError('Tool count exceeds the resource limit')
    if len({value.id for value in values}) != len(values):
        raise ValueError('Tool ids must be unique')
    if sum(len(value.drills) + 2 * len(value.slots) for value in values) > MAX_VERTICES:
        raise ValueError('Drill/slot vertex count exceeds the resource limit')


def _tool_differs(first: ReferenceTool, second: ReferenceTool, tolerance: float) -> bool:
    if (first.id != second.id or abs(first.diameter_mm - second.diameter_mm) > tolerance
            or len(first.drills) != len(second.drills) or len(first.slots) != len(second.slots)):
        return True
    if any(_metric(math.dist(a, b)) > tolerance for a, b in zip(first.drills, second.drills)):
        return True
    return any(_metric(math.dist(a, b)) > tolerance for one, two in zip(first.slots, second.slots)
               for a, b in zip(one, two))


def compare_tools(expected: Sequence[ReferenceTool], actual: Sequence[ReferenceTool], *,
                  distance_mm: float) -> ToolComparison:
    """Compare tool ids/order, explicit diameters and every repeated drill/slot endpoint."""
    tolerance = _tolerance(distance_mm, 'distance_mm')
    _tools(expected)
    _tools(actual)
    differences = tuple(index for index in range(max(len(expected), len(actual)))
                        if index >= len(expected) or index >= len(actual)
                        or _tool_differs(expected[index], actual[index], tolerance))
    return ToolComparison(not differences, differences, len(expected), len(actual))
