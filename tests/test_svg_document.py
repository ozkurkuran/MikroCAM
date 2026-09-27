"""Bounded SVG source traversal, inherited style and reference semantics."""
import hashlib

import pytest

from mikrocam.importers.svg_document import parse_svg_document
from mikrocam.core.svg_transform import apply_svg_point


def document(body, attrs='width="100mm" height="100mm" viewBox="0 0 100 100"'):
    return parse_svg_document(f'<svg xmlns="http://www.w3.org/2000/svg" {attrs}>{body}</svg>'.encode(), 'board.svg')


def test_exact_source_identity_and_inherited_inline_paint_without_source_mutation():
    source = b'<svg width="10mm" height="20mm" viewBox="0 0 10 20"><g stroke="red" stroke-width="2"><line x2="5" style="stroke-width:3;fill:none"/></g></svg>'
    result = parse_svg_document(source, 'board.svg')
    assert result.source_sha256 == hashlib.sha256(source).hexdigest()
    assert result.source_name == 'board.svg' and len(result.elements) == 1
    assert result.elements[0].paint.width == 3
    assert result.elements[0].paint.stroke and not result.elements[0].paint.fill
    assert dict(result.elements[0].attributes)['style'] == 'stroke-width:3;fill:none'


def test_nested_noncommuting_transform_and_use_offset_order():
    result = document('<defs><rect id="shape" width="1" height="2" transform="scale(2)"/></defs>'
                      '<g transform="translate(10 20)"><use href="#shape" x="3" y="4" transform="rotate(90)"/></g>')
    assert len(result.elements) == 1  # Definition is not an independent drawable.
    assert apply_svg_point(result.elements[0].matrix, (1., 1.)) == pytest.approx((4., 25.))


def test_root_transform_is_outside_viewbox_in_css_pixel_coordinates():
    result = document('<rect width="1" height="1"/>',
                      'width="100mm" height="100mm" viewBox="0 0 100 100" transform="translate(10 0)"')
    assert apply_svg_point(result.elements[0].matrix, (1., 1.)) == pytest.approx((1 + 10*25.4/96, 1.))


def test_use_inherits_instance_paint_and_referenced_element_overrides_it():
    result = document('<defs><g id="part"><line x2="1"/><line x2="2" stroke-width="4"/></g></defs>'
                      '<use href="#part" stroke="black" stroke-width="2"/>')
    assert len(result.elements) == 2
    assert [item.paint.width for item in result.elements] == [2., 4.]
    assert all(item.paint.stroke for item in result.elements)
    assert len({item.element_id for item in result.elements}) == 2


def test_hidden_parent_visibility_can_be_overridden_but_display_none_cannot():
    result = document('<g visibility="hidden"><rect width="1" height="1"/>'
                      '<rect width="2" height="2" visibility="visible"/></g>'
                      '<g display="none"><rect width="3" height="3" display="inline"/></g>')
    assert len(result.elements) == 1
    assert dict(result.elements[0].attributes)['width'] == '2'


def test_opacity_inheritance_does_not_destroy_original_fill_presence():
    result = document('<g fill="black" fill-opacity="0"><rect width="1" height="1"/>'
                      '<rect width="2" height="2" fill-opacity="1"/></g>')
    assert not result.elements[0].paint.fill and result.elements[1].paint.fill


@pytest.mark.parametrize('body', ['<use href="#absent"/>', '<use href="https://invalid/x.svg#part"/>',
                                 '<g id="same"/><path id="same" d="M0 0L1 1"/>',
                                 '<defs><g id="loop"><use href="#loop"/></g></defs><use href="#loop"/>',
                                 '<text x="1" y="2">Unoutlined font</text>',
                                 '<svg width="1" height="1"/>', '<image href="x.png"/>',
                                 '<script>alert(1)</script>', '<style>rect{stroke-width:5}</style>'])
def test_unsupported_or_ambiguous_source_rejected(body):
    with pytest.raises(ValueError):
        document(body)


@pytest.mark.parametrize('style', ['stroke-dasharray:1 2', 'vector-effect:non-scaling-stroke',
                                  'clip-path:url(#clip)', 'fill:url(#gradient)', 'opacity:0.5',
                                  'filter:url(#filter)', 'stroke-width:10%', 'transform:scale(2)',
                                  'stroke-linejoin:arcs', 'stroke-miterlimit:-.1', 'stroke-width:-1',
                                  'overflow:hidden', 'width:10mm', 'stroke-width:bad',
                                  'stroke-width', 'fill:'])
def test_unsupported_or_invalid_paint_is_never_silently_guessed(style):
    with pytest.raises(ValueError):
        document(f'<line x2="1" style="{style}"/>')


@pytest.mark.parametrize('style', ['VECTOR-EFFECT:non-scaling-stroke', 'STROKE-DASHARRAY:2 3',
                                  '/* comment */ vector-effect:non-scaling-stroke',
                                  r'vector-\65 ffect:non-scaling-stroke', 'stroke-alignment:inner'])
def test_css_spelling_cannot_bypass_unsupported_appearance(style):
    with pytest.raises(ValueError):
        document(f'<line x2="1" stroke="red" style="{style}"/>')


def test_css_case_and_comments_preserve_supported_inline_override():
    result = document('<line x2="1" stroke-width="1" style="/* width */ STROKE-WIDTH: 3"/>')
    assert result.elements[0].paint.width == 3


def test_external_stylesheet_processing_instruction_is_not_silently_ignored():
    with pytest.raises(ValueError, match='stylesheet'):
        parse_svg_document(b'<?xml-stylesheet href="external.css"?><svg width="1" height="1"/>', 'external.svg')


@pytest.mark.parametrize('source', [b'<!DOCTYPE svg [<!ENTITY x "abc">]><svg width="1" height="1"/>',
                                   b'<svg width="1" height="1">', b'<html/>', b'\xff',
                                   b'<?xml version="1.0" encoding="UTF-16"?><svg/>'])
def test_malformed_or_unsupported_xml_encoding_and_entities_fail(source):
    with pytest.raises(ValueError):
        parse_svg_document(source, 'bad.svg')


def test_unused_definitions_and_metadata_do_not_force_unsupported_rendering():
    result = document('<defs><text id="label">unused</text><linearGradient id="unused"/></defs>'
                      '<metadata><anything>ignored</anything></metadata><rect width="1" height="1"/>')
    assert len(result.elements) == 1


def test_depth_and_reference_expansion_limits_are_enforced(monkeypatch):
    import mikrocam.importers.svg_document as parser
    monkeypatch.setattr(parser, 'MAX_SVG_DEPTH', 5)
    with pytest.raises(ValueError, match='depth|limit'):
        document('<g>' * 10 + '<line x2="1"/>' + '</g>' * 10)
    monkeypatch.setattr(parser, 'MAX_SVG_ELEMENTS', 10)
    with pytest.raises(ValueError, match='element|limit|budget'):
        document('<line x2="1"/>' * 12)


def test_source_size_limit_is_checked_before_xml_parse(monkeypatch):
    import mikrocam.importers.svg_document as parser
    monkeypatch.setattr(parser, 'MAX_SVG_BYTES', 20)
    with pytest.raises(ValueError, match='byte|size|limit'):
        document('<line x2="1"/>')
