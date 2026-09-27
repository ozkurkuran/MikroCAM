"""One PDF page-to-mm mapping: box origin, clockwise rotation, crop, flip."""
from .pdf_models import PdfPageInfo, PdfOptions
from .placement import Affine2D, Point2D
from .svg_transform import compose_affine


def pdf_page_frame(page: PdfPageInfo, options: PdfOptions) -> tuple[Affine2D, Point2D]:
    """Return the physical transform and the rebased final viewport dimensions."""
    if type(page) is not PdfPageInfo or type(options) is not PdfOptions or page.index != options.page_index:
        raise ValueError('PDF page and options must agree')
    x0, y0, x1, y1 = page.crop_box if options.box_mode == 'crop' else page.media_box
    scale = page.user_unit * 25.4 / 72
    width, height = (x1 - x0) * scale, (y1 - y0) * scale
    matrix = (scale, 0., 0., scale, -x0 * scale, -y0 * scale)
    rotations = {0: (1., 0., 0., 1., 0., 0.),
                 90: (0., 1., -1., 0., 0., width),
                 180: (-1., 0., 0., -1., width, height),
                 270: (0., -1., 1., 0., height, 0.)}
    matrix = compose_affine(rotations[page.rotation], matrix)
    if page.rotation in (90, 270):
        width, height = height, width
    if options.crop_mm is not None:
        x0, y0, x1, y1 = options.crop_mm
        if x1 > width or y1 > height:
            raise ValueError('PDF crop must lie within the oriented physical page')
        matrix = compose_affine((1., 0., 0., 1., -x0, -y0), matrix)
        width, height = x1 - x0, y1 - y0
    if options.flip:
        matrix = compose_affine((1., 0., 0., -1., 0., height), matrix)
    return matrix, (width, height)
