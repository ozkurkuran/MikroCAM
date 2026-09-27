from dataclasses import replace

import pytest

from mikrocam.core.svg_models import SvgElement, SvgPaint
from mikrocam.core.svg_transform import IDENTITY
from mikrocam.importers.svg_document import parse_svg_document
from mikrocam.importers.svg_style import resolve_style, style_fill_is_white, style_paint


@pytest.mark.parametrize('color', [
    'white', 'WHITE', '#fff', '#FFFfff', 'rgb(255,255,255)',
    'rgb(300,255,999)', 'rgb(100%,100%,100%)', 'rgb(200%,100%,101%)',
    'hsl(0,0%,100%)', 'hsl(360,100%,100%)', 'hsl(-720,-10%,150%)',
])
def test_supported_white_equivalence_is_retained_without_changing_paint(color):
    style = resolve_style({'fill': color})
    assert style_fill_is_white(style) is True
    assert style_paint(style).fill is True


@pytest.mark.parametrize('color', [
    'black', 'red', '#ffe', '#fffffe', 'rgb(254,255,255)', 'rgb(99%,100%,100%)',
    'rgb(-1,255,255)', 'hsl(0,0%,99%)', 'hsl(0,100%,50%)',
])
def test_positive_nonwhite_fill_is_distinct_from_no_fill(color):
    style = resolve_style({'fill': color})
    assert style_fill_is_white(style) is False
    assert style_paint(style).fill is True


@pytest.mark.parametrize('attributes', [
    {'fill': 'none'}, {'fill': 'transparent'}, {'fill': 'white', 'fill-opacity': '0'},
    {'fill': 'white', 'opacity': '0'}, {'fill': 'white', 'display': 'none'},
    {'fill': 'white', 'visibility': 'hidden'}, {'fill': 'white', 'visibility': 'collapse'},
    {'fill': 'currentColor', 'color': 'transparent'},
])
def test_inactive_fill_has_no_color_evidence(attributes):
    assert style_fill_is_white(resolve_style(attributes)) is None


def test_current_color_uses_child_color_even_when_fill_is_inherited():
    parent = resolve_style({'fill': 'currentColor', 'color': 'black'})
    assert style_fill_is_white(parent) is False
    assert style_fill_is_white(resolve_style({'color': 'white'}, parent)) is True
    assert style_fill_is_white(resolve_style({'color': 'currentColor'}, parent)) is False


def test_element_optional_color_fact_is_strict_and_preserves_positional_prefix():
    element = SvgElement('e', 'circle', (), IDENTITY, SvgPaint())
    assert element.fill_is_white is None
    assert replace(element, fill_is_white=True).fill_is_white is True
    assert replace(element, fill_is_white=False).fill_is_white is False
    for invalid in (0, 1, 'white', [], {}):
        with pytest.raises(ValueError):
            replace(element, fill_is_white=invalid)


def test_traversal_retains_resolved_fact_including_use_inheritance():
    source = (b'<svg width="10mm" height="10mm" viewBox="0 0 10 10">'
              b'<defs><circle id="template" cx="1" cy="1" r=".5" fill="currentColor"/></defs>'
              b'<g fill="currentColor" color="white"><circle id="a" cx="3" cy="3" r="1"/>'
              b'<circle id="b" cx="6" cy="3" r="1" color="black"/></g>'
              b'<use href="#template" color="white"/></svg>')
    document = parse_svg_document(source, 'white.svg')
    assert tuple(element.fill_is_white for element in document.elements) == (True, False, True)
    assert all(element.paint.fill for element in document.elements)


def test_color_evidence_does_not_subtract_white_material():
    from mikrocam.bridge.svg_import import import_svg_bytes
    source = (b'<svg width="10mm" height="10mm" viewBox="0 0 10 10">'
              b'<circle cx="5" cy="5" r="2" fill="black"/>'
              b'<circle cx="5" cy="5" r="1" fill="white"/></svg>')
    result = import_svg_bytes(source, 'material.svg', flip=False)
    assert tuple(element.fill_is_white for element in result.document.elements) == (False, True)
    assert all(geometry.area > 0 for geometry in result.geometry_mm)
    assert result.geometry_mm[0].contains(result.geometry_mm[1])
