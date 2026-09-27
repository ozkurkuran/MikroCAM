"""Analytic vector programs, no PDF parsing dependency."""
import hashlib
import pytest
from shapely import union_all
from mikrocam.core.pdf_models import PdfPageInfo, PdfDocumentInfo, PdfProgram, PdfCommand, PdfOptions
from mikrocam.importers.pdf_program import render_pdf_program


def program(*commands, rotation=0):
    page = PdfPageInfo(0, (0, 0, 100, 100), (0, 0, 100, 100), rotation, 72 / 25.4)
    document = PdfDocumentInfo('analytic.pdf', hashlib.sha256(b'fixture').hexdigest(), (page,))
    return PdfProgram(document, 0, tuple(PdfCommand(op, tuple(args)) for op, args in commands))


def render(*commands, options=None):
    return render_pdf_program(program(*commands), options or PdfOptions(0))


def test_separate_subpaths_do_not_connect():
    result = render(('re', (1, 2, 3, 4)), ('re', (20, 30, 4, 5)), ('f', ()))
    assert len(result.geometry_mm) == 2
    assert sum(g.area for g in result.geometry_mm) == pytest.approx(32)
    assert result.report.path_count == 2


def test_full_affine_order_and_path_construction_time():
    result = render(('cm', (1, 0, 0, 1, 20, 30)), ('cm', (0, 1, -1, 0, 0, 0)),
                    ('re', (0, 0, 10, 5)), ('cm', (2, 0, 0, 2, 0, 0)), ('f', ()))
    assert result.report.bounds_mm == pytest.approx((15, 30, 20, 40))
    assert result.geometry_mm[0].area == pytest.approx(50)


def test_q_restores_state_but_not_current_path():
    result = render(('q', ()), ('cm', (1, 0, 0, 1, 20, 0)), ('re', (0, 0, 5, 5)),
                    ('Q', ()), ('f', ()))
    assert result.report.bounds_mm == pytest.approx((20, 0, 25, 5))


@pytest.mark.parametrize('op', ['f*', 'B*'])
def test_evenodd_compound_hole(op):
    result = render(('re', (10, 10, 20, 20)), ('re', (15, 15, 10, 10)), (op, ()))
    assert len(result.geometry_mm[0].interiors) == 1
    if op == 'f*':
        assert result.geometry_mm[0].area == pytest.approx(300)


def test_nonzero_same_winding_fills_nested_ring():
    result = render(('re', (10, 10, 20, 20)), ('re', (15, 15, 10, 10)), ('f', ()))
    assert result.geometry_mm[0].area == pytest.approx(400)


def test_white_overpaint_then_black_restores_material():
    result = render(('re', (10, 10, 20, 20)), ('f', ()), ('g', (1,)),
                    ('re', (15, 15, 10, 10)), ('f', ()), ('g', (0,)),
                    ('re', (17, 17, 2, 2)), ('f', ()))
    assert sum(g.area for g in result.geometry_mm) == pytest.approx(304)


def test_pending_clip_applies_after_paint_and_restores_with_q():
    result = render(('q', ()), ('re', (10, 10, 10, 10)), ('W', ()), ('n', ()),
                    ('re', (0, 0, 50, 50)), ('f', ()), ('Q', ()),
                    ('re', (30, 30, 5, 5)), ('f', ()))
    assert sum(g.area for g in result.geometry_mm) == pytest.approx(125)


def test_crop_and_flip_clip_material_and_rebase():
    result = render(('re', (10, 20, 20, 30)), ('f', ()),
                    options=PdfOptions(0, 'crop', (15, 25, 40, 60), True))
    assert result.report.bounds_mm == pytest.approx((0, 10, 15, 35))
    assert result.geometry_mm[0].area == pytest.approx(375)


def test_full_affine_stroke_is_physical_material():
    result = render(('cm', (2, 0, 1, 3, 20, 20)), ('w', (2,)),
                    ('m', (0, 0)), ('l', (10, 0)), ('S', ()))
    assert result.report.bounds_mm == pytest.approx((19, 17, 41, 23))
    assert result.geometry_mm[0].area == pytest.approx(120)


@pytest.mark.parametrize('curve,args', [('c', (10, 20, 20, 20, 20, 10)),
                                      ('v', (20, 20, 20, 10)), ('y', (10, 20, 20, 10))])
def test_curve_endpoints_and_bounded_flattening(curve, args):
    result = render(('m', (10, 10)), (curve, args), ('l', (10, 10)), ('f', ()))
    assert result.geometry_mm[0].area > 0
    assert result.report.point_count > 12


@pytest.mark.parametrize('commands', [
    [('Q', ())], [('q', ())], [('cm', (0, 0, 0, 0, 0, 0))], [('w', (0,))],
    [('d', ((1, 2), 0))], [('J', (3,))], [('j', (-1,))], [('M', (.5,))],
    [('l', (1, 2))], [('h', ())], [('g', (2,))], [('rg', (0, 1, -1))],
    [('Do', ('/X1',))], [('Tj', ('text',))], [('gs', ('/GS',))], [('sh', ('/Sh',))],
    [('BT', ()), ('re', (1, 1, 2, 2)), ('ET', ())], [('BT', ())], [('ET', ())],
    [('BT', ()), ('BT', ()), ('ET', ())], [('re', (1, 1, 2))], [('q', (1,))],
])
def test_unsupported_or_malformed_rejects(commands):
    with pytest.raises(ValueError, match='PDF'):
        render(*commands, ('re', (10, 10, 10, 10)), ('f', ()))


def test_empty_generator_text_setup_accepted():
    result = render(('BT', ()), ('Tf', ('/F1', 12)), ('TL', (14.4,)), ('ET', ()),
                    ('re', (10, 10, 10, 10)), ('f', ()))
    assert result.geometry_mm[0].area == pytest.approx(100)


def test_graphics_stack_limit():
    with pytest.raises(ValueError, match='PDF.*state'):
        render(*([('q', ())] * 65))


def test_empty_or_edge_only_crop_rejects():
    with pytest.raises(ValueError, match='PDF.*empty'):
        render(('re', (0, 0, 10, 10)), ('f', ()), options=PdfOptions(0, crop_mm=(10, 0, 20, 20)))


def test_sample_and_material_share_total_point_budget(monkeypatch):
    import mikrocam.importers.pdf_program as module
    monkeypatch.setattr(module, 'MAX_PDF_POINTS', 9, raising=False)
    with pytest.raises(ValueError, match='PDF.*point budget'):
        render(('re', (10, 10, 20, 20)), ('f', ()))


def test_unpainted_path_and_unfinished_clip_reject():
    for tail in [(('m', (3, 3)),), (('W', ()),)]:
        with pytest.raises(ValueError, match='PDF.*unfinished'):
            render(('re', (10, 10, 20, 20)), ('f', ()), *tail)


@pytest.mark.parametrize('colour,values', [('rg', (1, 1, 1)), ('k', (0, 0, 0, 0))])
def test_rgb_cmyk_white_are_opaque_erasers(colour, values):
    result = render(('re', (10, 10, 20, 20)), ('f', ()), (colour, values),
                    ('re', (15, 15, 10, 10)), ('f', ()))
    assert result.geometry_mm[0].area == pytest.approx(300)


def test_fill_then_white_stroke_order():
    result = render(('w', (2,)), ('G', (1,)), ('re', (10, 10, 20, 20)), ('B', ()))
    assert result.report.bounds_mm == pytest.approx((11, 11, 29, 29))
    assert result.geometry_mm[0].area == pytest.approx(324)


def test_clip_persists_through_transform_and_white_restore():
    result = render(('re', (10, 10, 20, 20)), ('W', ()), ('n', ()),
                    ('q', ()), ('cm', (1, 0, 0, 1, 20, 0)), ('g', (1,)),
                    ('Q', ()), ('re', (0, 0, 50, 50)), ('f', ()))
    assert result.report.bounds_mm == pytest.approx((10, 10, 30, 30))


@pytest.mark.parametrize('cap,bounds', [(0,(10,9,20,11)), (1,(9,9,21,11)), (2,(9,9,21,11))])
def test_line_caps(cap, bounds):
    result = render(('J', (cap,)), ('w', (2,)), ('m', (10, 10)), ('l', (20, 10)), ('S', ()))
    assert result.report.bounds_mm == pytest.approx(bounds, abs=.01)


def test_reverse_winding_nonzero_hole():
    result = render(('re', (10, 10, 20, 20)), ('re', (25, 15, -10, 10)), ('f', ()))
    assert result.geometry_mm[0].area == pytest.approx(300)
