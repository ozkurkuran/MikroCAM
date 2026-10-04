"""Source clip presentation is separate from ordinary material paint."""
import pytest

from mikrocam.importers.svg_style import resolve_style


def test_clip_path_is_not_inherited_but_clip_rule_is():
    parent=resolve_style({'clip-path':'url(#mask)', 'clip-rule':'evenodd'})
    child=resolve_style({},parent)
    assert child['clip-path'] == 'none' and child['clip-rule'] == 'evenodd'
    assert resolve_style({'clip-path':'inherit'},parent)['clip-path'] == 'url(#mask)'


def test_clip_mode_ignores_paint_and_opacity_but_keeps_visibility():
    style=resolve_style({'fill':'url(#gradient)','stroke':'url(#gradient)','opacity':'.5',
                         'stroke-width':'invalid','clip-rule':'evenodd','visibility':'hidden'},clip_mode=True)
    assert style['fill']=='black' and style['stroke']=='none'
    assert style['opacity']=='1' and style['visibility']=='hidden' and style['clip-rule']=='evenodd'


@pytest.mark.parametrize('value',['url(https://example.invalid/x.svg#clip)','url(#a) url(#b)','bogus'])
def test_invalid_clip_reference_rejected(value):
    with pytest.raises(ValueError):
        resolve_style({'clip-path':value})


@pytest.mark.parametrize('value',['url(#a)','url("#a")',"url('#a')",'url( #a )'])
def test_local_clip_reference_spelling_normalized(value):
    assert resolve_style({'clip-path':value})['clip-path']=='url(#a)'


def test_clip_css_paint_is_ignored_after_cascade_including_fractional_opacity():
    from mikrocam.bridge.svg_import import import_svg_bytes
    from shapely import union_all
    source=(b'<svg width="10mm" height="10mm" viewBox="0 0 10 10">'
            b'<style>.clip{opacity:.5;fill:none;stroke-dasharray:2 3}</style>'
            b'<defs><clipPath id="c"><rect class="clip" width="3" height="4"/></clipPath></defs>'
            b'<rect width="10" height="10" clip-path="url(#c)"/></svg>')
    result=import_svg_bytes(source,'a.svg',flip=False)
    assert union_all(result.geometry_mm).area == pytest.approx(12)


_PAGE = b'<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm" viewBox="0 0 10 10"%s>%s<rect width="4" height="5"/></svg>'


@pytest.mark.parametrize('declaration', ['enable-background:new 0 0 576 576;', 'enable-background:new    ',
                                         'ENABLE-BACKGROUND: new 219.5 158.5 562 681', 'enable-background:accumulate',
                                         'enable-background:new 0 0 0 0', 'enable-background:inherit'])
def test_genuine_illustrator_enable_background_is_a_validated_no_op(declaration):
    # Illustrator SVG export writes this filter-only property on the root; filters stay unsupported.
    from mikrocam.bridge.svg_import import import_svg_bytes
    from shapely import union_all
    plain = import_svg_bytes(_PAGE % (b'', b''), 'a.svg', flip=False)
    for attrs, style in ((b' style="%s"' % declaration.encode(), b''),
                         (b' class="page"', b'<style>.page{%s}</style>' % declaration.encode())):
        result = import_svg_bytes(_PAGE % (attrs, style), 'a.svg', flip=False)
        assert union_all(result.geometry_mm).equals(union_all(plain.geometry_mm))
        assert union_all(result.geometry_mm).area == pytest.approx(20)


@pytest.mark.parametrize('declaration', ['enable-background:new 0 0 10', 'enable-background:bogus',
                                         'enable-background:new 0 0 -1 5', 'enable-background:new 0 0 1 nan',
                                         'enable-background:accumulate 0 0 1 1', 'enable-background:'])
def test_malformed_enable_background_is_still_rejected(declaration):
    from mikrocam.bridge.svg_import import import_svg_bytes
    with pytest.raises(ValueError):
        import_svg_bytes(_PAGE % (b' style="%s"' % declaration.encode(), b''), 'a.svg', flip=False)


def test_enable_background_does_not_admit_filters():
    from mikrocam.bridge.svg_import import import_svg_bytes
    source = _PAGE % (b' style="enable-background:new 0 0 10 10"', b'<g style="filter:url(#f)"/>')
    with pytest.raises(ValueError, match='filter'):
        import_svg_bytes(source, 'a.svg', flip=False)
