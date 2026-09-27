"""Offline CSS cascade tests use authored XML and actual style validation."""
from dataclasses import FrozenInstanceError
from xml.etree import ElementTree as ET

import pytest

from mikrocam.importers.svg_css import SvgCssRule, cascade_attributes, parse_stylesheets
from mikrocam.importers.svg_style import resolve_style


def stylesheet(text):
    root = ET.Element('{http://www.w3.org/2000/svg}svg')
    ET.SubElement(root, '{http://www.w3.org/2000/svg}style').text = text
    return root


def paint(css, attrs=None, tag='rect'):
    return resolve_style(cascade_attributes(tag, attrs or {}, parse_stylesheets(stylesheet(css))))


def test_comments_comma_rules_and_frozen_source_order():
    root = stylesheet('/* source */ rect, .st0 { fill: red; stroke: blue !IMPORTANT; } #a {fill:none}')
    before = ET.tostring(root)
    rules = parse_stylesheets(root)
    assert [r.selector for r in rules] == ['rect', '.st0', '#a']
    assert [r.specificity for r in rules] == [1, 10, 100]
    assert [r.order for r in rules] == [0, 1, 2]
    assert rules[0].declarations == (('fill', 'red', False), ('stroke', 'blue', True))
    assert ET.tostring(root) == before
    with pytest.raises(FrozenInstanceError):
        rules[0].order = 1


@pytest.mark.parametrize(('css', 'attrs', 'expected'), [
    ('*{fill:red}', {'fill': 'blue'}, 'red'),
    ('rect{fill:red}.a{fill:green}#x{fill:blue}', {'id': 'x', 'class': 'a'}, 'blue'),
    ('.a{fill:red}.b{fill:green}', {'class': 'a b'}, 'green'),
    ('#x{fill:red}', {'id': 'x', 'style': 'fill:blue'}, 'blue'),
    ('*{fill:red!important}', {'style': 'fill:blue'}, 'red'),
    ('#x{fill:red!important}', {'id': 'x', 'style': 'fill:blue!important'}, 'blue'),
    ('.a{fill:red!important}#x{fill:blue}', {'id': 'x', 'class': 'a'}, 'red'),
    ('rect{fill:red!important;fill:blue}', {}, 'red'),
    ('rect{fill:red;fill:blue}', {}, 'blue'),
    ('', {'style': 'fill:red!important;fill:blue'}, 'red'),
    ('.a{fill:red}', {'class': 'ab'}, 'black'),
    ('path{fill:red}', {}, 'black'),
])
def test_cascade_precedence(css, attrs, expected):
    assert paint(css, attrs)['fill'] == expected


def test_new_mapping_preserves_raw_attributes_and_inheritance():
    attrs = {'style': 'stroke:blue', 'class': 'st0', 'd': 'M0 0L1 1', 'id': 'raw'}
    before = dict(attrs)
    output = cascade_attributes('path', attrs, parse_stylesheets(stylesheet('.st0{visibility:hidden}')))
    assert output is not attrs and attrs == before
    assert output['d'] == attrs['d'] and output['class'] == 'st0'
    parent = resolve_style({'fill': 'green'})
    resolved = resolve_style(output, parent)
    assert resolved['fill'] == 'green' and resolved['stroke'] == 'blue'
    assert resolved['visibility'] == 'hidden'


def test_clip_rules_and_local_references_use_shared_style_grammar():
    attrs = cascade_attributes('rect', {'class': 'cut'}, parse_stylesheets(stylesheet(
        '.cut{clip-path:url("#clip0");clip-rule:evenodd;fill-rule:nonzero}')))
    style = resolve_style(attrs)
    assert style['clip-path'] == 'url(#clip0)'
    assert style['clip-rule'] == 'evenodd' and style['fill-rule'] == 'nonzero'
    child = resolve_style(cascade_attributes('path', {}, ()), style)
    assert child['clip-path'] == 'none' and child['clip-rule'] == 'evenodd'


@pytest.mark.parametrize('value', ['url(https://example/a.svg#c)', 'url(other.svg#c)', 'url(#)', 'bad'])
def test_invalid_or_external_clip_values_fail_unused(value):
    with pytest.raises(ValueError):
        parse_stylesheets(stylesheet(f'.unused{{clip-path:{value}}}'))


def test_normalized_property_names_and_important_whitespace():
    assert paint('rect { FILL : red ! important; fill: blue; }')['fill'] == 'red'


def test_inline_comment_and_important_are_resolved_without_stylesheet():
    attrs = {'style': '/* inline */ fill:green !IMPORTANT;fill:blue'}
    assert resolve_style(cascade_attributes('rect', attrs, ()))['fill'] == 'green'
    assert attrs['style'].startswith('/* inline */')


def test_rule_declaration_payload_and_inline_limits_are_bounded():
    with pytest.raises(ValueError, match='limit'):
        SvgCssRule('a' * 65537, (), 1, 0)
    with pytest.raises(ValueError, match='limit'):
        SvgCssRule('rect', (('fill', 'rgb(0,' + ' ' * 16384 + '0,0)', False),), 1, 0)
    with pytest.raises(ValueError, match='limit'):
        cascade_attributes('rect', {'style': ' ' * 16385}, ())


def test_multiple_style_elements_share_order_and_selector_budget():
    root = stylesheet('.a{fill:red}')
    ET.SubElement(root, 'style').text = '.a{fill:blue}'
    assert resolve_style(cascade_attributes('rect', {'class': 'a'}, parse_stylesheets(root)))['fill'] == 'blue'
    root = stylesheet(','.join(f'.a{i}' for i in range(256)) + '{}')
    assert len(parse_stylesheets(root)) == 256
    ET.SubElement(root, 'style').text = 'rect{}'
    with pytest.raises(ValueError, match='selector'):
        parse_stylesheets(root)


def test_aggregate_text_limit_including_comments():
    assert parse_stylesheets(stylesheet('/*' + 'a' * 65532 + '*/')) == ()
    root = stylesheet('/*' + 'a' * 65532 + '*/')
    ET.SubElement(root, 'style').text = ' '
    with pytest.raises(ValueError, match='limit'):
        parse_stylesheets(root)


@pytest.mark.parametrize('css', [
    'rect', 'rect{fill:red', 'rect{fill:red}}', '{fill:red}', 'rect{{fill:red}}',
    'rect, {fill:red}', '@import url(foo);', '@media all{rect{fill:red}}',
    'rect path{fill:red}', 'rect>path{fill:red}', 'rect.a{fill:red}', '[id=a]{fill:red}',
    ':root{fill:red}', '.a\\31{fill:red}', '/* unfinished', '*/ rect{}',
    'rect{fill}', 'rect{:red}', 'rect{fill:}', 'rect{fill:red!urgent}',
    'rect{width:1}', 'rect{transform:scale(2)}', 'rect{font-family:sans}',
])
def test_malformed_or_unsupported_styles_fail_even_unused(css):
    with pytest.raises(ValueError):
        parse_stylesheets(stylesheet(css))


@pytest.mark.parametrize('attrs', [{'href': 'a.css'}, {'src': 'a.css'}, {'type': 'text/javascript'}, {'media': 'print'}])
def test_external_or_conditional_styles_rejected(attrs):
    root = stylesheet('rect{}')
    root[0].attrib.update(attrs)
    with pytest.raises(ValueError):
        parse_stylesheets(root)


@pytest.mark.parametrize('declaration', ['fill:url(http://example/x)', 'opacity:.5',
                                       'stroke-dasharray:1 2', 'fill:bad'])
def test_unsupported_paint_is_validated_in_winning_material_context(declaration):
    rules = parse_stylesheets(stylesheet(f'.unused{{{declaration}}}'))
    assert resolve_style(cascade_attributes('rect', {}, rules))['fill'] == 'black'
    with pytest.raises(ValueError):
        resolve_style(cascade_attributes('rect', {'class': 'unused'}, rules))


def test_overridden_paint_does_not_change_winning_material():
    assert paint('rect{fill:bad;fill:red}')['fill'] == 'red'


@pytest.mark.parametrize('args', [
    ('rect', (), True, 0), ('rect', (), 10, 0), ('rect', (), 1, -1),
    ('rect', (), 1, 256), ('rect', [], 1, 0), ('rect.a', (), 1, 0),
    ('rect', (('fill', 'red', 1),), 1, 0), ('rect', (('unknown', 'bad', False),), 1, 0),
])
def test_rule_record_is_strict(args):
    with pytest.raises(ValueError):
        SvgCssRule(*args)


@pytest.mark.parametrize('args', [(None, {}, ()), ('rect', [], ()), ('rect', {'style': 1}, ()),
                                  ('rect', {}, []), ('rect', {}, (object(),))])
def test_cascade_rejects_wrong_types(args):
    with pytest.raises(ValueError):
        cascade_attributes(*args)


@pytest.mark.parametrize('namespace', ['urn:foreign', 'http://www.w3.org/2000/svg', ''])
def test_styles_inside_metadata_are_inert_for_cascade_and_actual_geometry(namespace):
    from mikrocam.bridge.svg_import import import_svg_bytes
    root = ET.fromstring('<svg width="10mm" height="10mm" viewBox="0 0 10 10">'
                         '<metadata/><rect x="2" y="2" width="2" height="2"/></svg>')
    tag = f'{{{namespace}}}style' if namespace else 'style'
    style = ET.SubElement(root[0], tag)
    style.text = 'rect{stroke:black;stroke-width:2}'
    assert parse_stylesheets(root) == ()
    result = import_svg_bytes(ET.tostring(root), 'metadata.svg', flip=False)
    assert result.geometry_mm[0].bounds == pytest.approx((2, 2, 4, 4))
    assert result.geometry_mm[0].area == pytest.approx(4)


def test_foreign_styles_are_not_svg_css_even_outside_metadata():
    root = ET.fromstring('<svg xmlns:x="urn:foreign"><x:style media="print">'
                         '@import url(https://untrusted.invalid/);</x:style></svg>')
    assert parse_stylesheets(root) == ()


def test_metadata_subtree_is_pruned_before_stylesheet_validation_and_budget():
    root = ET.fromstring('<svg><metadata><wrapper><style media="print"/></wrapper></metadata></svg>')
    root.find('.//style').text = '@import ' + 'x' * 65537
    assert parse_stylesheets(root) == ()


@pytest.mark.parametrize('namespace', ['http://www.w3.org/2000/svg', ''])
def test_legitimate_styles_in_defs_still_apply_in_source_order(namespace):
    root = ET.Element('svg')
    defs = ET.SubElement(root, 'defs')
    tag = f'{{{namespace}}}style' if namespace else 'style'
    ET.SubElement(defs, tag).text = 'rect{fill:red}'
    ET.SubElement(root, tag).text = 'rect{fill:blue}'
    rules = parse_stylesheets(root)
    assert len(rules) == 2 and [rule.order for rule in rules] == [0, 1]
    assert resolve_style(cascade_attributes('rect', {}, rules))['fill'] == 'blue'
