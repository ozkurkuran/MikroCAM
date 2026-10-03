"""Schedule complementary raster groups without allocating their bitmap copies."""
from mikrocam.core.interlace_job import InterlacePass, InterlacePlan, InterlaceSettings
from mikrocam.core.visual import BurnMask, integer_range
from mikrocam.core.visual_interlace import base_order, group_statistics


def build_plan(mask: BurnMask, settings: InterlaceSettings, revision: int) -> InterlacePlan:
    integer_range(revision, 1, 2**63 - 1, 'revision')
    order = base_order(settings.count, settings.order_mode)
    statistics = group_statistics(mask, settings.count)
    orders, passes, have_active = [], [], False
    for turn in range(settings.round_count):
        shift = turn if settings.vary_order_each_round else 0
        effective = tuple((k + shift) % settings.count for k in order)
        orders.append(effective)
        for sequence, group in enumerate(effective):
            rows, pixels = statistics[group]
            enabled = pixels > 0
            delay = settings.delay_ms if enabled and have_active else 0
            passes.append(InterlacePass(turn, sequence, group, group, settings.count,
                                        mask.grid.height_px, rows, pixels, enabled, delay))
            have_active = have_active or enabled
    return InterlacePlan(mask.sha256, mask.grid, settings, revision, tuple(orders), tuple(passes))


def validate_plan(mask: BurnMask, plan: InterlacePlan, revision: int) -> None:
    if plan.mask_sha256 != mask.sha256 or plan.grid != mask.grid or plan.revision != revision:
        raise ValueError('PLAN_STALE')
    if build_plan(mask, plan.settings, revision) != plan:
        raise ValueError('PLAN_STALE: corrupted schedule')
