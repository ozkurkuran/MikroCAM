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
