"""Offline SVG CSS inheritance and collection fonts remain renderable."""
from pathlib import Path
import pytest
from mikrocam.bridge import visual_fonts
from mikrocam.bridge.visual_svg import inspect_svg, render_svg
from mikrocam.core.visual import SourceAsset, PreparationSettings, build_grid
from mikrocam.core.visual_normalize import make_burn_mask


def mask(content):
    data = ('<svg xmlns="http://www.w3.org/2000/svg" width="30mm" height="18mm" '
            'viewBox="0 0 30 18">' + content + '</svg>').encode()
    prep = PreparationSettings(30, 18)
    return make_burn_mask(render_svg(SourceAsset('fonts.svg', data, inspect_svg(data)),
                                    prep, build_grid(prep)), prep)


@pytest.mark.parametrize('content', [
    '<g font-family="DejaVu Sans"><text x="2" y="10" font-size="6" font-family="inherit">ABC</text></g>',
    '<text x="2" y="10" font-size="6" style="font-family: DejaVu Sans !important">ABC</text>',
    '<style>text {font-family: DejaVu Sans !IMPORTANT;}</style><text x="2" y="10" font-size="6">ABC</text>',
])
def test_svg_css_font_forms_keep_explicit_font_pixels(content):
    expected = mask('<text x="2" y="10" font-size="6" font-family="DejaVu Sans">ABC</text>')
    assert mask(content).sha256 == expected.sha256


@pytest.mark.parametrize('suffix', ['.ttc', '.otc'])
def test_installed_collection_faces_are_discovered_and_rendered(tmp_path, monkeypatch, suffix):
    import matplotlib
    from fontTools.ttLib import TTFont, TTCollection
    source = Path(matplotlib.__file__).parent / 'mpl-data/fonts/ttf'
    with TTCollection() as collection:
        collection.fonts = [TTFont(source / 'DejaVuSans.ttf'), TTFont(source / 'DejaVuSerif.ttf')]
        path = tmp_path / ('synthetic' + suffix); collection.save(path)
    monkeypatch.setenv('WINDIR', str(tmp_path))
    (tmp_path / 'Fonts').mkdir(); installed = tmp_path / 'Fonts' / path.name; path.rename(installed)
    assert installed in visual_fonts._font_paths()
    monkeypatch.setattr(visual_fonts, '_font_paths', lambda: [installed])
    inventory = visual_fonts._font_inventory()
    assert {'dejavu sans', 'dejavu serif'} <= inventory.keys()
    assert ord('A') in inventory['dejavu serif'][0][1]
    # Include the bundled default mono family alongside the installed collection.
    monkeypatch.setattr(visual_fonts, '_font_paths', lambda: [installed, source / 'DejaVuSansMono.ttf'])
    assert mask('<text x="2" y="10" font-size="6" font-family="DejaVu Serif">ABC</text>').black_pixel_count > 500
