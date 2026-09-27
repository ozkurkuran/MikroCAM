"""Independent physical length, viewport and source-coordinate affine examples."""
import math
import pytest
from mikrocam.core.svg_transform import parse_svg_length, parse_svg_numbers, validate_affine, compose_affine, apply_svg_point, affine_scale_bound, parse_svg_transform, resolve_svg_viewport
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

@pytest.mark.parametrize('text,expected', [('4in', 384), ('25.4mm', 96), ('2.54cm', 96), ('72pt', 96), ('6pc', 96), ('96px', 96), ('-.5e2', -50), (' +.5 ', 0.5)])
def test_lengths_normalize_absolute_units_before_viewbox(text, expected):
    assert parse_svg_length(text) == pytest.approx(expected)

@pytest.mark.parametrize('text', ['', '1%', '2em', '2ex', '1m', '1 mm', 'NaN', 'inf', '1e999', 'garbage1mm', '1mm junk', '1.2.3', '1' * 65, None, True])
def test_length_rejects_incomplete_unresolved_and_nonfinite_text(text):
    with pytest.raises(ValueError):
        parse_svg_length(text)

@pytest.mark.parametrize('text', ['0,0,100,50', '0 0 100 50', '0, 0\t100\n50'])
def test_complete_number_lists(text):
    assert parse_svg_numbers(text) == (0.0, 0.0, 100.0, 50.0)

@pytest.mark.parametrize('text', [',1', '1,', '1,,2', '1 x 2', '1e999', '1' * 65])
def test_list_rejects_garbage_and_missing_numbers(text):
    with pytest.raises(ValueError):
        parse_svg_numbers(text)

def test_transform_order_svg_matrix_layout_and_rotation_centre():
    assert apply_svg_point(parse_svg_transform('translate(10,20) scale(2,3)'), (1.0, 2.0)) == (12.0, 26.0)
    assert apply_svg_point(parse_svg_transform('matrix(1,2,3,4,5,6)'), (7.0, 8.0)) == (36.0, 52.0)
    assert apply_svg_point(parse_svg_transform('rotate(90 2 3)'), (3.0, 3.0)) == pytest.approx((2.0, 4.0))
    assert apply_svg_point(parse_svg_transform('skewX(45)'), (1.0, 2.0)) == pytest.approx((3.0, 2.0))
    assert parse_svg_transform(None) == parse_svg_transform('') == IDENTITY

def test_composition_outer_inner_and_frobenius_bound():
    outer = (2.0, 0.0, 0.0, 3.0, 10.0, 20.0)
    inner = (1.0, 0.0, 0.0, 1.0, 5.0, 6.0)
    assert apply_svg_point(compose_affine(outer, inner), (1.0, 2.0)) == (22.0, 44.0)
    assert affine_scale_bound((2.0, 0.0, 0.0, 3.0, 100.0, 200.0)) == math.sqrt(13)

@pytest.mark.parametrize('text', ['scale(0)', 'matrix(1 2 2 4 0 0)', 'rotate(1 2)', 'translate(1) garbage', 'foo(1)', 'translate(1),', 'scale(NaN)', 'skewX(90)', 'translate(1e13)', 'scale(1e-999)', 'translate(1)' * 129, 'x' * 4097])
def test_transform_failures_are_bounded_not_partial(text):
    with pytest.raises(ValueError):
        parse_svg_transform(text)

@pytest.mark.parametrize('matrix', [[1, 0, 0, 1, 0, 0], (1, 0, 0, 0, 0, 0), (True, 0, 0, 1, 0, 0), (1, 0, 0, 1, float('nan'), 0), (10000000000000.0, 0, 0, 1, 0, 0)])
def test_affine_validates_immutable_finite_nonsingular_coefficients(matrix):
    with pytest.raises(ValueError):
        validate_affine(matrix)

def test_point_budget_applies_after_mapping():
    with pytest.raises(ValueError):
        apply_svg_point((2.0, 0.0, 0.0, 1.0, 0.0, 0.0), (1000000000.0, 0.0))

def test_viewbox_nonzero_origin_none_and_default_meet():
    attrs = (('width', '100mm'), ('height', '50mm'), ('viewBox', '10,20,200,100'))
    viewport = resolve_svg_viewport(attrs)
    assert (viewport.width_mm, viewport.height_mm) == pytest.approx((100, 50))
    assert apply_svg_point(viewport.matrix, (10.0, 20.0)) == pytest.approx((0, 0))
    assert apply_svg_point(viewport.matrix, (210.0, 120.0)) == pytest.approx((100, 50))
    attrs = (('width', '100mm'), ('height', '100mm'), ('viewBox', '0 0 200 100'))
    assert apply_svg_point(resolve_svg_viewport(attrs).matrix, (0.0, 0.0)) == pytest.approx((0, 25))
    assert apply_svg_point(resolve_svg_viewport(attrs + (('preserveAspectRatio', 'none'),)).matrix, (200.0, 100.0)) == pytest.approx((100, 100))

@pytest.mark.parametrize('align,x,y', [(a + b, x, y) for a, x in [('xMin', 0), ('xMid', 25), ('xMax', 50)] for b, y in [('YMin', 0), ('YMid', 0), ('YMax', 0)]])
def test_all_nine_meet_alignments(align, x, y):
    viewport = resolve_svg_viewport((('width', '100mm'), ('height', '50mm'), ('viewBox', '0 0 100 100'), ('preserveAspectRatio', align + ' meet')))
    assert apply_svg_point(viewport.matrix, (0.0, 0.0)) == pytest.approx((x, y))

def test_root_physical_px_and_missing_dimensions_inference():
    viewport = resolve_svg_viewport((('width', '96'), ('height', '96px')))
    assert viewport.width_mm == viewport.height_mm == 25.4
    assert apply_svg_point(viewport.matrix, (96.0, 96.0)) == (25.4, 25.4)
    for attrs, dimensions in [((('viewBox', '0 0 96 48'),), (25.4, 12.7)), ((('width', '50mm'), ('viewBox', '0 0 2 1')), (50, 25)), ((('height', '25mm'), ('viewBox', '0 0 2 1')), (50, 25))]:
        result = resolve_svg_viewport(attrs)
        assert (result.width_mm, result.height_mm) == pytest.approx(dimensions)
        assert result.notices

@pytest.mark.parametrize('attrs', [(('width', '100'),), (('width', '0'), ('height', '100')), (('width', '10%'), ('height', '10')), (('viewBox', '0 0 0 10'),), (('width', '100'), ('height', '100'), ('preserveAspectRatio', 'xMidYMid slice')), (('width', '100'), ('height', '100'), ('preserveAspectRatio', 'defer xMidYMid')), (('width', '10'), ('width', '20'), ('height', '10'))])
def test_viewport_rejects_ambiguous_unsupported_or_invalid_attributes(attrs):
    with pytest.raises(ValueError):
        resolve_svg_viewport(attrs)


def test_number_list_rejects_before_allocating_past_element_point_budget(monkeypatch):
    import mikrocam.core.svg_transform as module
    monkeypatch.setattr(module, 'MAX_ELEMENT_POINTS', 3, raising=False)
    calls = []
    original = module._numeric
    def observe(text):
        calls.append(text)
        return original(text)
    monkeypatch.setattr(module, '_numeric', observe)
    assert module.parse_svg_numbers('1, 2, 3, 4, 5, 6') == (1., 2., 3., 4., 5., 6.)
    calls.clear()
    with pytest.raises(ValueError, match='budget|limit'):
        module.parse_svg_numbers('1 2 3 4 5 6 7')
    assert calls == ['1', '2', '3', '4', '5', '6']
