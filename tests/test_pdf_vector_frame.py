"""Analytic page coordinates, with rotation before crop before explicit flip."""
import pytest
from mikrocam.core.pdf_models import PdfPageInfo, PdfOptions
from mikrocam.core.pdf_frame import pdf_page_frame
from mikrocam.core.svg_transform import apply_svg_point


@pytest.mark.parametrize('rotation,origin,corner,size', [
    (0, (0, 0), (20, 10), (20, 10)),
    (90, (0, 20), (10, 0), (10, 20)),
    (180, (20, 10), (0, 0), (20, 10)),
    (270, (10, 0), (0, 20), (10, 20)),
])
def test_page_origin_units_rotation(rotation, origin, corner, size):
    page = PdfPageInfo(0, (-10, -20, 30, 40), (5, 6, 25, 16), rotation, 72 / 25.4)
    matrix, viewport = pdf_page_frame(page, PdfOptions(0))
    assert viewport == pytest.approx(size)
    assert apply_svg_point(matrix, (5, 6)) == pytest.approx(origin)
    assert apply_svg_point(matrix, (25, 16)) == pytest.approx(corner)


def test_oriented_crop_rebase_and_flip_once():
    page = PdfPageInfo(0, (0, 0, 20, 10), (0, 0, 20, 10), 90, 72 / 25.4)
    matrix, viewport = pdf_page_frame(page, PdfOptions(0, 'media', (2, 3, 8, 15), True))
    assert viewport == pytest.approx((6, 12))
    assert apply_svg_point(matrix, (17, 2)) == pytest.approx((0, 12))
    assert apply_svg_point(matrix, (5, 8)) == pytest.approx((6, 0))


@pytest.mark.parametrize('options', [PdfOptions(1), PdfOptions(0, crop_mm=(0, 0, 100, 100))])
def test_wrong_page_or_outside_crop_rejects(options):
    page = PdfPageInfo(0, (0, 0, 20, 10), (0, 0, 20, 10), 0, 1)
    with pytest.raises(ValueError, match='PDF'):
        pdf_page_frame(page, options)
