"""Finite CAM paint colors and currentColor inheritance without a CSS renderer."""
import pytest

from mikrocam.importers.svg_style import resolve_style, style_paint
from mikrocam.importers.svg_document import parse_svg_document


def test_current_color_uses_current_element_color_and_transparency():
    style = resolve_style({'fill': 'currentColor', 'stroke': 'currentColor', 'color': 'transparent'})
    paint = style_paint(style)
    assert not paint.fill and not paint.stroke


def test_inherited_current_color_defers_until_child_color_override():
    parent = resolve_style({'fill': 'currentColor', 'stroke': 'currentColor', 'color': 'transparent'})
    child = resolve_style({'color': 'red'}, parent)
    assert style_paint(child).fill and style_paint(child).stroke
    assert not style_paint(parent).fill
    assert child['fill'].lower() == 'currentcolor'


def test_color_current_color_is_inherited_color_not_a_recursive_paint():
    parent = resolve_style({'color': 'transparent'})
    child = resolve_style({'color': 'currentColor', 'fill': 'currentColor'}, parent)
    assert child['color'] == 'transparent' and not style_paint(child).fill
    assert style_paint(resolve_style({'color': 'currentColor'})).fill


@pytest.mark.parametrize('attrs', [dict(fill='NONE', stroke='TRANSPARENT'),
    dict(fill='CURRENTCOLOR', stroke='currentcolor', color='TRANSPARENT'),
    dict(style='fill: CuRrEnTcOlOr; stroke: NoNe; color: TrAnSpArEnT')])
def test_css_special_color_keywords_are_case_insensitive(attrs):
    paint = style_paint(resolve_style(attrs))
    assert not paint.fill and not paint.stroke


@pytest.mark.parametrize('color', ['rgb(255, 0, 0)', 'RGB(100%, 0%, 50%)',
    'rgb(-10,300, 2.5)', 'hsl(120, 100%, 50%)', 'HSL(-720, -10%, 200%)',
    '#AbC', '#abcdef', 'BLUE'])
def test_supported_opaque_colors_are_positive_material_even_with_channel_clamping(color):
    style = resolve_style({'color': color, 'fill': 'currentColor'})
    assert style_paint(style).fill


@pytest.mark.parametrize('color', ['url(#paint)', 'rgba(1,2,3,.5)', 'rgb(1)',
    'rgb(1,2)', 'rgb(1,2,3,4)', 'rgb(1,,3)', 'rgb(10%, 2, 3)', 'rgb(nan,2,3)',
    'rgb(1e999,2,3)', 'hsl(120,50,50)', 'hsl(10%,50%,50%)', 'hsl(1,2%,3%,.5)',
    '#1234', '#11223344', 'unknown', 'none'])
def test_invalid_or_alpha_color_value_is_explicit_error_even_when_paint_is_none(color):
    with pytest.raises(ValueError):
        resolve_style({'fill': 'none', 'stroke': 'none', 'color': color})


@pytest.mark.parametrize('paint', ['rgb(1)', 'hsl(1)', 'rgb(1,2,3/.5)', 'hsla(1,2%,3%,1)'])
def test_malformed_rgb_hsl_paint_cannot_create_material(paint):
    with pytest.raises(ValueError):
        resolve_style({'fill': paint})


def test_document_resolves_parent_current_color_using_each_child_color():
    source = b'<svg width="10mm" height="10mm"><g fill="currentColor" color="transparent">' \
             b'<rect width="1" height="1"/><rect x="2" width="1" height="1" color="red"/>' \
             b'</g></svg>'
    document = parse_svg_document(source, 'colors.svg')
    assert tuple(element.paint.fill for element in document.elements) == (False, True)
