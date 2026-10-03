"""Detached source orchestration; codecs and host objects never enter core models."""
from collections.abc import Callable
from importlib.metadata import version
from mikrocam.core.visual import PreparationSettings, RasterFrame, SourceAsset, build_grid
from mikrocam.core.visual_normalize import make_burn_mask
from mikrocam.core.interlace_job import InterlaceSettings, VisualInterlaceJob
from mikrocam.core.placement import Placement
from mikrocam.core.laser_job import LaserRecipe
from mikrocam.core.laser_paths import check_cancelled
from .visual_bitmap import render_bitmap


def prepare_visual_job(source: SourceAsset, preparation: PreparationSettings,
                       interlace: InterlaceSettings, placement: Placement,
                       laser_recipe: LaserRecipe | None, revision: int,
                       cancelled: Callable[[], bool] | None = None,
                       rendered_frame: RasterFrame | None = None,
                       renderer: tuple[str, str] | None = None,
                       frame_ready: Callable[[RasterFrame], None] | None = None) -> VisualInterlaceJob:
    check_cancelled(cancelled)
    grid = build_grid(preparation)
    if rendered_frame is not None:
        frame = rendered_frame
        if renderer is None: raise ValueError('Explicit renderer provenance required')
    elif source.info.kind == 'bitmap':
        frame = render_bitmap(source, preparation, grid)
        renderer = ('Pillow', version('Pillow'))
    elif source.info.kind in ('svg', 'geometry_snapshot'):
        from .visual_svg import render_svg
        frame = render_svg(source, preparation, grid)
        renderer = ('resvg_py', version('resvg_py'))
    else:
        raise ValueError('PDF_UNAVAILABLE: PDF renderer must run in the UI worker')
    check_cancelled(cancelled)
    if frame_ready is not None: frame_ready(frame)
    mask = make_burn_mask(frame, preparation, cancelled=cancelled)
    check_cancelled(cancelled)
    return VisualInterlaceJob(source, preparation, mask, interlace, placement, laser_recipe,
                             revision, renderer[0], renderer[1])
