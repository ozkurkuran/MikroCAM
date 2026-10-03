"""Immutable laser recipe/job data in mm, separate from CNC and device settings."""
from dataclasses import dataclass

from shapely import from_wkb, normalize, to_wkb, union_all
from shapely.affinity import scale
from shapely.errors import GEOSException
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from .placement import Placement, _finite_real, _validate_geometry
from .laser_device import LaserDeviceProfile, PARAMETER_FIELDS


def _name(value: object, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{context}.name must be a nonempty string')


def _polygon_geometry(geometry: BaseGeometry) -> None:
    _validate_geometry(geometry)
    if not isinstance(geometry, (Polygon, MultiPolygon)) or geometry.is_empty:
        raise ValueError('Region requires nonempty valid planar Polygon/MultiPolygon copper')


def _canonical_wkb(geometry: BaseGeometry) -> str:
    return to_wkb(normalize(geometry), hex=True, output_dimension=2,
                  byte_order=1, flavor='iso', include_srid=False)


@dataclass(frozen=True)
class LaserPass:
    """Named scalar settings; the recipe profile determines applicable parameters."""
    name: str
    power_percent: float | None
    speed_mm_s: float
    frequency_khz: float | None = None
    pulse_width_ns: float | None = None
    min_power_percent: float | None = None
    pwm_frequency_khz: float | None = None

    def __post_init__(self) -> None:
        _name(self.name, 'pass')
        for field in PARAMETER_FIELDS:
            if getattr(self, field) is None and field != 'speed_mm_s': continue
            value = _finite_real(getattr(self, field), field)
            if value < 0 or (value == 0 and field != 'min_power_percent') or (
                field in ('power_percent', 'min_power_percent') and value > 100
            ): raise ValueError(f'{field} must be finite and in its valid range')
            object.__setattr__(self, field, value)
        if self.min_power_percent is not None and self.power_percent is not None and self.min_power_percent > self.power_percent:
            raise ValueError('min_power_percent cannot exceed power_percent')


@dataclass(frozen=True)
class LaserRecipe:
    """An ordered nonempty tuple of uniquely named laser passes."""
    name: str
    passes: tuple[LaserPass, ...]
    device: LaserDeviceProfile | None = None

    def __post_init__(self) -> None:
        _name(self.name, 'recipe')
        if not isinstance(self.passes, tuple) or not self.passes:
            raise ValueError('recipe.passes must be a nonempty tuple of LaserPass values')
        if not all(isinstance(value, LaserPass) for value in self.passes):
            raise ValueError('recipe.passes must contain only LaserPass values')
        names = [value.name for value in self.passes]
        if len(set(names)) != len(names):
            raise ValueError('recipe.passes contains duplicate pass names')
        if self.device is not None and not isinstance(self.device, LaserDeviceProfile):
            raise ValueError('recipe.device requires LaserDeviceProfile or None')
        for value in self.passes:
            if self.device is not None:
                self.device.validate_pass(value)
            else:
                for field in ('power_percent', 'frequency_khz', 'pulse_width_ns'):
                    if getattr(value, field) is None: raise ValueError(f'{field} is required for a legacy recipe')
                if value.min_power_percent is not None or value.pwm_frequency_khz is not None:
                    raise ValueError('New laser parameters require an explicit device profile')


@dataclass(frozen=True)
class PlanarRegion:
    """Detached canonical 2D WKB hex of nonempty valid mm copper, including holes."""
    wkb_hex: str

    def __post_init__(self) -> None:
        if (not isinstance(self.wkb_hex, str) or not self.wkb_hex or len(self.wkb_hex) % 2
                or any(char not in '0123456789abcdefABCDEF' for char in self.wkb_hex)):
            raise ValueError('Region WKB must be a canonical nonempty hex string')
        try:
            geometry = from_wkb(self.wkb_hex)
            _polygon_geometry(geometry)
        except (GEOSException, ValueError) as error:
            raise ValueError(f'Invalid region WKB: {error}') from error
        canonical = _canonical_wkb(geometry)
        if self.wkb_hex.upper() != canonical:
            raise ValueError('Region WKB must use canonical normalized 2D little-endian encoding')
        object.__setattr__(self, 'wkb_hex', canonical)

    @classmethod
    def from_geometry(cls, geometry: BaseGeometry) -> 'PlanarRegion':
        """Validate source copper and encode a canonical snapshot without mutating it."""
        _polygon_geometry(geometry)
        return cls(_canonical_wkb(geometry))

    def to_geometry(self) -> BaseGeometry:
        """Decode a new Shapely value; no live host or geometry object is retained."""
        return from_wkb(self.wkb_hex)


@dataclass(frozen=True)
class LaserJob:
    """Explicit source copper, recipe and the shared placement; no manufacturing commands."""
    name: str
    region: PlanarRegion
    recipe: LaserRecipe
    placement: Placement = Placement()

    def __post_init__(self) -> None:
        _name(self.name, 'job')
        for field, expected in (('region', PlanarRegion), ('recipe', LaserRecipe), ('placement', Placement)):
            if not isinstance(getattr(self, field), expected):
                raise ValueError(f'job.{field} must be a {expected.__name__}')

    def placed_geometry(self) -> BaseGeometry:
        """Apply the one existing placement once, leaving source mm copper unchanged."""
        return self.placement.apply_geometry(self.region.to_geometry())


def _collect_polygons(value: object) -> list[Polygon]:
    if isinstance(value, (Polygon, MultiPolygon)):
        _polygon_geometry(value)
        return [value] if isinstance(value, Polygon) else list(value.geoms)
    if isinstance(value, GeometryCollection):
        if value.is_empty:
            raise ValueError('Copper geometry collection must be nonempty')
        children = value.geoms
    elif isinstance(value, (list, tuple)):
        if not value:
            raise ValueError('Copper polygon sequence must be nonempty')
        children = value
    else:
        raise ValueError('Copper must contain only polygons or polygon collections')
    polygons = []
    for child in children:
        polygons.extend(_collect_polygons(child))
    return polygons


def region_from_polygons(geometries: object, units: str) -> PlanarRegion:
    """Union current polygon copper and convert its declared MM/IN geometry unit once."""
    if not isinstance(units, str) or units.strip().upper() not in {'MM', 'IN'}:
        raise ValueError('Copper units must be explicitly MM or IN')
    copper = union_all(_collect_polygons(geometries))
    if units.strip().upper() == 'IN':
        copper = scale(copper, 25.4, 25.4, origin=(0, 0))
    return PlanarRegion.from_geometry(copper)
