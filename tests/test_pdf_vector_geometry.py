"""Preflight limits and nontrivial path paint order."""
import pytest
from shapely.geometry import box
from mikrocam.core.pdf_geometry import PdfCanvas
from mikrocam.core.pdf_paths import PdfPaths
from test_pdf_vector_program import render


def test_clip_is_applied_after_same_path_paint():
    result = render(('re', (10, 10, 20, 20)), ('f', ()), ('w', (4,)),
                    ('re', (15, 15, 10, 10)), ('W', ()), ('S', ()),
                    ('g', (1,)), ('re', (0, 0, 100, 100)), ('f', ()))
    assert sum(g.area for g in result.geometry_mm) == pytest.approx(300)


def test_close_only_current_subpath_before_stroke():
    result = render(('w', (2,)), ('m', (10, 10)), ('l', (20, 10)),
                    ('m', (40, 40)), ('l', (50, 40)), ('l', (50, 50)), ('s', ()))
    first = min(result.geometry_mm, key=lambda g: g.bounds[0])
    assert first.bounds == pytest.approx((10, 9, 20, 11))


def test_clip_evenodd_retains_hole_and_current_path_not_clip_state():
    result = render(('re', (10, 10, 40, 40)), ('re', (20, 20, 20, 20)),
                    ('W*', ()), ('n', ()), ('re', (0, 0, 100, 100)), ('f', ()))
    assert result.geometry_mm[0].area == pytest.approx(1200)


@pytest.mark.parametrize('kind', ['sample', 'contour', 'subpath'])
def test_path_bounds_check_before_extension(kind):
    paths = PdfPaths()
    paths.move((1., 1.))
    if kind == 'sample':
        paths.point_count = 500000
    elif kind == 'contour':
        paths.points = [(1., 1.)] * 100000
    else:
        paths.path_count = 10000
    with pytest.raises(ValueError, match='PDF.*budget'):
        paths.move((2., 2.)) if kind == 'subpath' else paths.line((2., 2.))


def test_overlay_cumulative_work_rejects_before_geos():
    canvas = PdfCanvas((100., 100.))
    canvas.edge_work = 1999995
    with pytest.raises(ValueError, match='PDF.*edge-work'):
        canvas.overlay(box(0, 0, 10, 10), box(1, 1, 2, 2), 'union')


def test_empty_clip_cannot_reenable_material():
    with pytest.raises(ValueError, match='PDF.*empty'):
        render(('re', (200, 200, 10, 10)), ('W', ()), ('n', ()),
               ('re', (0, 0, 100, 100)), ('f', ()))


def test_open_self_crossing_stroke_rejects():
    with pytest.raises(ValueError, match='PDF.*[Ss]elf'):
        render(('m', (10, 10)), ('l', (30, 30)), ('l', (10, 30)), ('l', (30, 10)), ('S', ()))


def test_stroke_point_budget_accumulates_across_subpaths(monkeypatch):
    from mikrocam.core import pdf_geometry as module
    from mikrocam.core.svg_models import SvgPath, SvgRendered
    path = SvgPath(((1., 1.), (2., 2.)))
    polygon = box(0, 0, 10, 10)
    monkeypatch.setattr(module, 'MAX_PDF_POINTS', 9)
    monkeypatch.setattr(module, 'render_svg_paths', lambda *args: SvgRendered((), (polygon,), ()))
    state = module.PdfGraphicsState((1., 0., 0., 1., 0., 0.), polygon)
    with pytest.raises(ValueError, match='PDF.*stroke.*budget'):
        module.pdf_strokes((path, path), state)


def test_crosshatch_overlay_rejects_before_explosive_face_construction():
    from shapely.geometry import MultiPolygon
    first = MultiPolygon([box(0, index * 2, 200, index * 2 + 1) for index in range(100)])
    second = MultiPolygon([box(index * 2, 0, index * 2 + 1, 200) for index in range(100)])
    with pytest.raises(ValueError, match='PDF.*intersection candidate budget'):
        PdfCanvas((200., 200.)).overlay(first, second, 'intersection')
