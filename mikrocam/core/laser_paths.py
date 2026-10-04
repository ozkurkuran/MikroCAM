"""Immutable source features and placed exposure paths, without device commands."""
from collections.abc import Callable
from dataclasses import dataclass

from .laser_job import LaserJob, LaserPass, PlanarRegion
from .placement import Point2D, _finite_real, _point


CancelCheck = Callable[[], bool] | None
MAX_SCAN_LINES = 50_000
MAX_PATHS = 200_000
CONTOUR_MODES = ('none', 'outer', 'inner', 'trace', 'pad', 'board')
ISLAND_ORDERS = ('checkerboard', 'raster')


class PlanningCancelled(Exception):
    """A cancelled request must not publish its partial result."""


def check_cancelled(cancelled: CancelCheck) -> None:
    """Cooperatively stop between geometry operations."""
    if cancelled is not None and cancelled():
        raise PlanningCancelled('Laser planning cancelled')


def check_path_count(count: int) -> None:
    """Bound output allocation without silently dropping paths."""
    if count > MAX_PATHS:
        raise ValueError(f'Laser plan exceeds {MAX_PATHS} paths; increase hatch spacing or simplify input')


def validate_interlace_n(n: int) -> None:
    """Keep ordering and planning options on the same strict interlace range."""
    if type(n) is not int or not 1 <= n <= 1_000_000:
        raise ValueError('Interlace N must be an integer from 1 to 1000000')


@dataclass(frozen=True)
class CopperFeatures:
    """Source-mm copper with optional usable trace, pad and explicit board areas."""
    copper: PlanarRegion
    traces: PlanarRegion | None = None
    pads: PlanarRegion | None = None
    board: PlanarRegion | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.copper, PlanarRegion):
            raise ValueError('Feature copper must be a PlanarRegion')
        for name in ('traces', 'pads', 'board'):
            value = getattr(self, name)
            if value is not None and not isinstance(value, PlanarRegion):
                raise ValueError(f'Feature {name} must be a PlanarRegion or None')


@dataclass(frozen=True)
class IslandSettings:
    """Origin-anchored square hatch tiles; odd-parity tiles add ``angle_step_deg``.

    ``overlap_mm`` is the total overlap between two neighbouring tiles. ``checkerboard``
    scans even-parity tiles before odd-parity ones; ``raster`` scans row by row.
    """
    tile_size_mm: float
    overlap_mm: float = 0.0
    angle_step_deg: float = 90.0
    order: str = 'checkerboard'

    def __post_init__(self) -> None:
        tile = _finite_real(self.tile_size_mm, 'tile_size_mm')
        overlap = _finite_real(self.overlap_mm, 'overlap_mm')
        if tile <= 0:
            raise ValueError('Island tile size must be positive')
        if not 0 <= overlap < tile:
            raise ValueError('Island overlap must be at least zero and smaller than the tile size')
        if type(self.order) is not str or self.order not in ISLAND_ORDERS:
            raise ValueError('Island order must be checkerboard or raster')
        object.__setattr__(self, 'tile_size_mm', tile)
        object.__setattr__(self, 'overlap_mm', overlap)
        object.__setattr__(self, 'angle_step_deg', _finite_real(self.angle_step_deg, 'angle_step_deg'))


@dataclass(frozen=True)
class PlanOptions:
    """Explicit geometric options; no material/device recipe defaults."""
    contour_mode: str = 'outer'
    hatch: bool = False
    spacing_mm: float = 0.1
    angle_deg: float = 0.0
    cross_hatch: bool = False
    region_mode: str = 'copper'
    interlace_n: int = 1
    island: IslandSettings | None = None

    def __post_init__(self) -> None:
        validate_interlace_n(self.interlace_n)
        if self.contour_mode not in CONTOUR_MODES:
            raise ValueError('Unsupported contour mode')
        if self.region_mode not in ('copper', 'clearance'):
            raise ValueError('Area must be copper or clearance')
        if type(self.hatch) is not bool or type(self.cross_hatch) is not bool:
            raise ValueError('Hatch and cross_hatch must be boolean')
        if self.cross_hatch and not self.hatch:
            raise ValueError('Cross hatch requires hatch')
        if self.contour_mode == 'none' and not self.hatch:
            raise ValueError('Select a contour or hatch')
        spacing = _finite_real(self.spacing_mm, 'spacing_mm')
        if spacing <= 0:
            raise ValueError('Hatch spacing must be positive')
        object.__setattr__(self, 'spacing_mm', spacing)
        object.__setattr__(self, 'angle_deg', _finite_real(self.angle_deg, 'angle_deg'))
        if self.island is not None:
            if not isinstance(self.island, IslandSettings):
                raise ValueError('Island tiling requires IslandSettings or None')
            if not self.hatch:
                raise ValueError('Island tiling requires hatch')
            if self.island.tile_size_mm < spacing:
                raise ValueError('Island tile size must be at least the hatch spacing')


@dataclass(frozen=True)
class LaserPath:
    """One exposure polyline, with original hatch scan identity when applicable."""
    points: tuple[Point2D, ...]
    role: str
    scan_index: int | None = None
    hatch_family: int | None = None

    def __post_init__(self) -> None:
        try:
            points = tuple(_point(value, 'path point') for value in self.points)
        except TypeError as error:
            raise ValueError('Path points must be finite XY pairs') from error
        if len(points) < 2 or len(set(points)) < 2:
            raise ValueError('Path requires at least two distinct points')
        if self.role not in ('contour', 'hatch'):
            raise ValueError('Path role must be contour or hatch')
        if self.role == 'hatch':
            if type(self.scan_index) is not int or type(self.hatch_family) is not int or self.hatch_family not in (0, 1):
                raise ValueError('Hatch requires an integer scan index and family 0 or 1')
        elif self.scan_index is not None or self.hatch_family is not None:
            raise ValueError('Contour paths cannot have hatch scan metadata')
        object.__setattr__(self, 'points', points)


@dataclass(frozen=True)
class LaserPassPlan:
    """One explicit recipe pass referencing the shared already-placed paths."""
    settings: LaserPass
    paths: tuple[LaserPath, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.settings, LaserPass):
            raise ValueError('Pass plan settings must be a LaserPass')
        if not isinstance(self.paths, tuple) or not self.paths:
            raise ValueError('Pass plan requires nonempty tuple paths')
        if not all(isinstance(path, LaserPath) for path in self.paths):
            raise ValueError('Pass plan paths must be LaserPath values')
        check_path_count(len(self.paths))


@dataclass(frozen=True)
class LaserPlan:
    """Original job and ordered already-placed mm paths; ephemeral, not a file format."""
    job: LaserJob
    options: PlanOptions
    paths: tuple[LaserPath, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.job, LaserJob) or not isinstance(self.options, PlanOptions):
            raise ValueError('Plan requires LaserJob and PlanOptions')
        if not isinstance(self.paths, tuple) or not self.paths:
            raise ValueError('No paths generated for the selected geometry and options')
        if not all(isinstance(path, LaserPath) for path in self.paths):
            raise ValueError('Plan paths must be LaserPath values')
        check_path_count(len(self.paths))

    @property
    def pass_plans(self) -> tuple[LaserPassPlan, ...]:
        """Expose recipe order without copying or transforming exposure paths."""
        return tuple(LaserPassPlan(settings, self.paths) for settings in self.job.recipe.passes)
