"""One planar millimetre placement for preview, CAM paths and machine coordinates."""

from collections.abc import Iterable
from dataclasses import dataclass
import math
from numbers import Real

from shapely import get_coordinates
from shapely.affinity import affine_transform
from shapely.geometry.base import BaseGeometry


Point2D = tuple[float, float]
Affine2D = tuple[float, float, float, float, float, float]


def _finite_real(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f'{label} must be a finite real number, not {value!r}')
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f'{label} must be finite') from error
    if not math.isfinite(result):
        raise ValueError(f'{label} must be finite')
    return result


def _point(value: Iterable[float], label: str) -> Point2D:
    try:
        values = tuple(value)
    except TypeError as error:
        raise ValueError(f'{label} must contain exactly two finite coordinates') from error
    if len(values) != 2:
        raise ValueError(f'{label} must contain exactly two finite coordinates')
    return (_finite_real(values[0], f'{label}.x'), _finite_real(values[1], f'{label}.y'))


def _validate_geometry(geometry: BaseGeometry) -> None:
    if not isinstance(geometry, BaseGeometry):
        raise TypeError('Expected planar Shapely geometry')
    if geometry.has_z or geometry.has_m:
        raise ValueError('Placement requires planar XY geometry; Z/M coordinates are unsupported')
    if not geometry.is_valid:
        raise ValueError('Placement requires valid geometry with finite coordinates')
    if any(not math.isfinite(value) for point in get_coordinates(geometry) for value in point):
        raise ValueError('Geometry coordinates must be finite')


@dataclass(frozen=True)
class Placement:
    """Apply translation + rotation * mirror * (point - origin), all distances in mm.

    Positive angles rotate counterclockwise. ``mirror_x`` negates the local X coordinate,
    reflecting about the local Y axis before rotation. The source origin always maps to
    the destination translation. No unit conversion or hardware operation occurs here.
    """

    origin: Point2D = (0.0, 0.0)
    translation: Point2D = (0.0, 0.0)
    rotation_deg: float = 0.0
    mirror_x: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, 'origin', _point(self.origin, 'origin'))
        object.__setattr__(self, 'translation', _point(self.translation, 'translation'))
        object.__setattr__(self, 'rotation_deg', _finite_real(self.rotation_deg, 'rotation_deg'))
        if type(self.mirror_x) is not bool:
            raise ValueError('mirror_x must be a boolean')

    @property
    def matrix(self) -> Affine2D:
        """Return Shapely-compatible coefficients (a, b, d, e, xoff, yoff)."""
        degrees = self.rotation_deg % 360.0
        if degrees in (0.0, 90.0, 180.0, 270.0):
            cosine, sine = ((1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0))[int(degrees / 90)]
        else:
            angle = math.radians(degrees)
            cosine, sine = math.cos(angle), math.sin(angle)
        mirror = -1.0 if self.mirror_x else 1.0
        a, b, d, e = cosine * mirror, -sine, sine * mirror, cosine
        x, y = self.origin
        xoff = self.translation[0] - a * x - b * y
        yoff = self.translation[1] - d * x - e * y
        values = (a, b, d, e, xoff, yoff)
        if not all(math.isfinite(value) for value in values):
            raise ValueError('Placement coefficients must remain finite')
        return values

    def apply_point(self, point: Iterable[float]) -> Point2D:
        """Place a finite XY pair without modifying it."""
        x, y = _point(point, 'point')
        a, b, d, e, xoff, yoff = self.matrix
        return _point((a * x + b * y + xoff, d * x + e * y + yoff), 'placed point')

    def apply_points(self, points: Iterable[Iterable[float]]) -> tuple[Point2D, ...]:
        """Place a point sequence in order, returning immutable pairs."""
        try:
            iterator = iter(points)
        except TypeError as error:
            raise ValueError('points must be an iterable of finite XY pairs') from error
        return tuple(self.apply_point(point) for point in iterator)

    def apply_geometry(self, geometry: BaseGeometry) -> BaseGeometry:
        """Place valid planar geometry using the same coefficients as individual points."""
        _validate_geometry(geometry)
        placed = affine_transform(geometry, self.matrix)
        _validate_geometry(placed)
        if placed.is_empty != geometry.is_empty:
            raise ValueError('Placement lost nonempty geometry')
        return placed

    def inverse(self) -> 'Placement':
        """Return the placement from destination coordinates back to source coordinates."""
        angle = self.rotation_deg if self.mirror_x else -self.rotation_deg
        return Placement(origin=self.translation, translation=self.origin,
                         rotation_deg=angle, mirror_x=self.mirror_x)
