"""Raster scheduling data; shares Placement and LaserRecipe with existing CAM."""
from dataclasses import dataclass
from .visual import BurnMask, PreparationSettings, RasterGrid, SourceAsset, booleans, finite_positive, integer_range
from .laser_job import LaserRecipe
from .placement import Placement


@dataclass(frozen=True)
class InterlaceSettings:
    count: int = 3
    order_mode: str = 'sequential'
    order_algorithm: str = 'bit_reverse_v1'
    round_count: int = 1
    vary_order_each_round: bool = False
    delay_ms: int = 0
    bidirectional: bool = True
    direction_policy: str = 'lightburn_managed'
    spot_diameter_mm: float | None = None

    def __post_init__(self) -> None:
        integer_range(self.count, 1, 8, 'INVALID_INTERLACE_COUNT')
        integer_range(self.round_count, 1, 999, 'round_count')
        integer_range(self.delay_ms, 0, 600000, 'delay_ms')
        booleans(self, ('vary_order_each_round', 'bidirectional'))
        if self.order_mode not in ('sequential', 'mixed'): raise ValueError('Invalid order_mode')
        if self.order_algorithm != 'bit_reverse_v1': raise ValueError('Unknown order_algorithm')
        if self.direction_policy not in ('lightburn_managed', 'source_row_parity'):
            raise ValueError('Unknown direction_policy')
        if self.spot_diameter_mm is not None: finite_positive(self.spot_diameter_mm, 'spot_diameter_mm')


@dataclass(frozen=True)
class InterlacePass:
    round_index: int
    sequence_index: int
    group_index: int
    row_start: int
    row_step: int
    row_stop: int
    active_row_count: int
    black_pixel_count: int
    enabled: bool
    delay_before_ms: int


@dataclass(frozen=True)
class InterlacePlan:
    mask_sha256: str
    grid: RasterGrid
    settings: InterlaceSettings
    revision: int
    effective_orders: tuple[tuple[int, ...], ...]
    passes: tuple[InterlacePass, ...]

    @property
    def active_pass_count(self) -> int:
        return sum(p.enabled for p in self.passes)

    @property
    def total_delay_ms(self) -> int:
        return sum(p.delay_before_ms for p in self.passes)

    @property
    def pitch_below_spot(self) -> bool:
        spot = self.settings.spot_diameter_mm
        return spot is not None and self.grid.pitch_mm < spot


@dataclass(frozen=True)
class VisualInterlaceJob:
    source: SourceAsset
    preparation: PreparationSettings
    mask: BurnMask
    interlace: InterlaceSettings
    placement: Placement = Placement()
    laser_recipe: LaserRecipe | None = None
    revision: int = 1
    renderer_name: str = 'unknown'
    renderer_version: str = 'unknown'

    def __post_init__(self) -> None:
        from .visual import build_grid
        integer_range(self.revision, 1, 2**63 - 1, 'revision')
        if self.mask.grid != build_grid(self.preparation): raise ValueError('INVALID_GRID')
        for name, expected in (('source', SourceAsset), ('interlace', InterlaceSettings), ('placement', Placement)):
            if not isinstance(getattr(self, name), expected): raise ValueError(f'{name} requires {expected.__name__}')
        if self.laser_recipe is not None and not isinstance(self.laser_recipe, LaserRecipe):
            raise ValueError('laser_recipe requires LaserRecipe or None')
