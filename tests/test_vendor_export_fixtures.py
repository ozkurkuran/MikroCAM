"""Genuine third-party vendor exports, kept byte-identical with recorded provenance and licenses."""
import hashlib
import json
import math
from pathlib import Path

import pytest

from mikrocam.bridge.svg_import import import_svg_bytes
from mikrocam.importers.cad_source import detect_cad_source, validate_cad_assessment


ROOT = Path(__file__).parent / 'reference/cad-source'
PROTEUS = ROOT / 'proteus-breath-analyzer'


def _provenance(folder: Path) -> dict:
    return json.loads((folder / 'provenance.json').read_text(encoding='utf-8'))


def _assert_retained_bytes(folder: Path) -> dict:
    provenance = _provenance(folder)
    for name, record in provenance['files'].items():
        data = (folder / name).read_bytes()
        assert len(data) == record['bytes'], name
        assert hashlib.sha256(data).hexdigest() == record['sha256'], name
        blob = hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()
        assert record.get('git_blob_sha1', blob) == blob, name
    return provenance


def test_proteus_export_is_unmodified_apache_licensed_upstream_bytes():
    provenance = _assert_retained_bytes(PROTEUS)
    assert provenance['license'] == 'Apache-2.0'
    assert provenance['upstream_revision'] == '5872bbe211318a74ec51ccff3bf4ef2fc1d371b7'
    license_text = (PROTEUS / 'LICENSE').read_text(encoding='utf-8')
    assert 'Apache License' in license_text and 'Version 2.0, January 2004' in license_text
    source = (PROTEUS / 'B_A_.svg').read_bytes()
    assert source.count(b'\r\n') == source.count(b'\n') > 0  # Upstream CRLF bytes, never normalized.
    assert b'<desc>Created by Proteus Design Suite</desc>' in source


def test_genuine_proteus_svg_desc_marker_identifies_proteus():
    source = (PROTEUS / 'B_A_.svg').read_bytes()
    assessment = detect_cad_source(source, 'renamed-kicad.svg', 'SVG')
    assert assessment.application == 'Proteus' and assessment.status == 'identified'
    assert [(item.field, item.application, item.value) for item in assessment.evidence] == [
        ('svg.desc', 'Proteus', 'Created by Proteus Design Suite')]
    assert assessment.source_sha256 == _provenance(PROTEUS)['files']['B_A_.svg']['sha256']
    validate_cad_assessment(assessment)  # The retained claim survives the bridge validator.


@pytest.mark.parametrize('object_type', ['geometry', 'gerber'])
@pytest.mark.parametrize('flip', [False, True])
def test_genuine_proteus_geometry_imports_with_unpainted_non_scaling_stroke(object_type, flip):
    # Spec 041: all 209 vector-effect="non-scaling-stroke" uses sit on filled, unstroked paths,
    # where the effect cannot change material; 142 further elements say vector-effect="none".
    from shapely import union_all
    source = (PROTEUS / 'B_A_.svg').read_bytes()
    assert source.count(b'vector-effect="non-scaling-stroke"') == 209
    result = import_svg_bytes(source, 'B_A_.svg', flip=flip, object_type=object_type)
    assert len(result.document.elements) == 351
    assert (result.document.viewport.width_mm, result.document.viewport.height_mm) == pytest.approx((54.11, 44.28))
    notices = {item.code: item.message for item in result.notices}
    assert notices['non-scaling-stroke-unpainted'].startswith('209 ')
    assert 'non-scaling-stroke' not in notices  # No painted stroke uses the effect.
    # The white board rectangle is positive material too (016 colour policy).
    assert union_all(result.geometry_mm).bounds == pytest.approx((0, 0, 54.11, 44.28), abs=1e-9)
    tracks = [element for element in result.document.elements if element.kind == 'polyline']
    assert len(tracks) == 140 and {round(e.paint.width) for e in tracks} == {25, 102}


def _raw_proteus_white_circles() -> list[tuple[float, float, float]]:
    """Independent of the importer: white four-cubic paths straight from the exported text."""
    import re
    text = (PROTEUS / 'B_A_.svg').read_text(encoding='utf-8')
    circles = []
    for group in re.finditer(r'<g fill="#ffffff"[^>]*>\s*<path [^>]*d="([^"]*)"', text):
        data = group[1]
        if re.sub(r'[^A-Za-z]', '', data) != 'MCCCC':
            continue
        numbers = [float(value) for value in re.findall(r'-?\d+(?:\.\d+)?', data)]
        xs, ys = numbers[0::2], numbers[1::2]
        assert (xs[0], ys[0]) == (xs[-1], ys[-1])  # Returns to its start without Z.
        circles.append(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(xs) - min(xs)) / 2))
    return circles


@pytest.mark.parametrize('flip', [False, True])
def test_genuine_proteus_drill_review_finds_every_unclosed_white_hole(flip):
    from mikrocam.core.svg_drills import detect_svg_drills
    raw = _raw_proteus_white_circles()
    assert len(raw) == 25 and {radius for *_, radius in raw} == {50.0}  # 50 units = 0.5 mm.
    source = (PROTEUS / 'B_A_.svg').read_bytes()
    review = detect_svg_drills(import_svg_bytes(source, 'B_A_.svg', flip=flip))
    expected = [(x / 100, 44.28 - y / 100 if flip else y / 100) for x, y, _ in raw]
    found = [candidate.center_mm for candidate in review.candidates]
    assert len(found) == 25
    for wanted in expected:  # One-to-one: holes are at least 2.5 mm apart.
        assert sum(math.dist(actual, wanted) <= 1e-6 for actual in found) == 1, wanted
    # Proteus approximates each 1 mm hole with four cubics (kappa 0.5522); the fitted diameter
    # exceeds 1 mm only by that approximation (<= 0.027 % of r per side).
    assert all(1 <= candidate.diameter_mm <= 1.0003 for candidate in review.candidates)
    from mikrocam.core.drill_groups import group_drill_selection
    tools = group_drill_selection(review, tuple(range(25)))
    assert len(tools) == 1 and len(tools[0].centers_mm) == 25
    assert tools[0].diameter_mm == pytest.approx(1, abs=3e-4)
    codes = [item.code for item in review.notices]
    assert codes.count('noncircular-opening') == 1  # Only the white board background rectangle.
    assert 'unsupported-opening' not in codes and 'heuristic' in codes


ILLUSTRATOR_XMP = ROOT / 'illustrator-wortschule-hilfsverb'
_PT = 50 / 141.732  # XMP MaxPageSize 50 mm over the exported 141.732-unit viewBox.


def test_illustrator_xmp_export_is_unmodified_mit_licensed_upstream_bytes():
    provenance = _assert_retained_bytes(ILLUSTRATOR_XMP)
    assert provenance['license'] == 'MIT'
    assert provenance['upstream_revision'] == 'eea2cf5d856bff46ebc96b1dd472e869a604c31e'
    assert 'Copyright (c) 2022 Stefan Wintermeyer' in (ILLUSTRATOR_XMP / 'LICENSE').read_text(encoding='utf-8')
    source = (ILLUSTRATOR_XMP / 'hilfsverb.svg').read_bytes()
    assert 0 < source.count(b'\r\n') < source.count(b'\n')  # Exported mixed line endings are retained.


def test_genuine_illustrator_xmp_export_identifies_illustrator_from_both_fields():
    source = (ILLUSTRATOR_XMP / 'hilfsverb.svg').read_bytes()
    assessment = detect_cad_source(source, 'inkscape.svg', 'SVG')
    assert assessment.application == 'Illustrator' and assessment.status == 'identified'
    assert [(item.field, item.application) for item in assessment.evidence] == [
        ('svg.generator-comment', 'Illustrator'), ('svg.xmp.CreatorTool', 'Illustrator')]
    assert assessment.evidence[1].value == 'Adobe Illustrator 25.3 (Windows)'
    validate_cad_assessment(assessment)


@pytest.mark.parametrize('object_type', ['geometry', 'gerber'])
@pytest.mark.parametrize('flip', [False, True])
def test_genuine_illustrator_page_size_comes_from_xmp_max_page_size(object_type, flip):
    from shapely import union_all
    from mikrocam.core.import_report import build_import_report
    source = (ILLUSTRATOR_XMP / 'hilfsverb.svg').read_bytes()
    result = import_svg_bytes(source, 'hilfsverb.svg', flip=flip, object_type=object_type)
    notices = [(item.code, item.message) for item in result.document.notices]
    assert ('xmp-page-size', 'SVG width uses XMP page dimension 50 mm.') in notices
    assert ('xmp-page-size', 'SVG height uses XMP page dimension 50 mm.') in notices
    assert (result.document.viewport.width_mm, result.document.viewport.height_mm) == pytest.approx((50, 50))
    report = build_import_report(result)
    assert report.coordinates.source_width is None and report.coordinates.source_units == ('absent', 'absent')
    assert report.coordinates.view_box == pytest.approx((0, 0, 141.732, 141.732))
    assert report.source_sha256 == _provenance(ILLUSTRATOR_XMP)['files']['hilfsverb.svg']['sha256']
    # Colour is positive material: the white disc does not subtract from the red disc.
    material = union_all(result.geometry_mm)
    radius, x, y = 52.044 * _PT, 74.098 * _PT, 72.921 * _PT
    y = 50 - y if flip else y
    assert material.is_valid and material.bounds == pytest.approx(
        (x - radius, y - radius, x + radius, y + radius), abs=.01)
    assert 0.999 * 3.141592653589793 * radius ** 2 <= material.area <= 3.141592653589793 * radius ** 2


@pytest.mark.parametrize('flip', [False, True])
def test_genuine_illustrator_concentric_white_disc_is_one_reviewed_drill_candidate(flip):
    from mikrocam.core.svg_drills import detect_svg_drills
    source = (ILLUSTRATOR_XMP / 'hilfsverb.svg').read_bytes()
    review = detect_svg_drills(import_svg_bytes(source, 'hilfsverb.svg', flip=flip))
    assert len(review.candidates) == 1
    candidate = review.candidates[0]
    y = 72.921 * _PT
    assert candidate.center_mm == pytest.approx((74.098 * _PT, 50 - y if flip else y), abs=1e-6)
    assert candidate.diameter_mm == pytest.approx(2 * 26.022 * _PT, abs=1e-6)
    assert (candidate.opening_id, candidate.pad_id) == ('2:circle', '1:circle')
    assert any(item.code == 'heuristic' for item in review.notices)


ILLUSTRATOR_LAYERS = ROOT / 'illustrator-commons-history-of-china'
_SVG_NAME = 'History_of_China_for_template_heading.svg'
_PX = 25.4 / 96


def test_illustrator_commons_export_is_unmodified_public_domain_bytes():
    provenance = _assert_retained_bytes(ILLUSTRATOR_LAYERS)
    assert provenance['license'] == 'Public domain (PD-self)'
    source = (ILLUSTRATOR_LAYERS / _SVG_NAME).read_bytes()
    assert hashlib.sha1(source).hexdigest() == '7d7f6de20e33bf80501ba252d8d52ff9f0ab5490'  # Commons record.
    notice = (ILLUSTRATOR_LAYERS / 'LICENSE').read_text(encoding='utf-8')
    assert 'release this work into the public domain' in notice and 'Lệ Xuân' in notice
    assert b'style="enable-background:new 0 0 3051.3 718.7;"' in source


def test_genuine_illustrator_generator_comment_identifies_illustrator():
    source = (ILLUSTRATOR_LAYERS / _SVG_NAME).read_bytes()
    assessment = detect_cad_source(source, _SVG_NAME, 'SVG')
    assert assessment.application == 'Illustrator' and assessment.status == 'identified'
    assert [(item.field, item.application) for item in assessment.evidence] == [
        ('svg.generator-comment', 'Illustrator')]
    assert 'Adobe Illustrator 24.1.0' in assessment.evidence[0].value


@pytest.mark.parametrize('object_type', ['geometry', 'gerber'])
@pytest.mark.parametrize('flip', [False, True])
def test_genuine_illustrator_layers_css_compound_fill_and_stroke_import(object_type, flip):
    from shapely import union_all
    source = (ILLUSTRATOR_LAYERS / _SVG_NAME).read_bytes()
    result = import_svg_bytes(source, _SVG_NAME, flip=flip, object_type=object_type)
    height = 718.7 * _PX
    assert (result.document.viewport.width_mm, result.document.viewport.height_mm) == pytest.approx(
        (3051.3 * _PX, height))
    assert not any(item.code.startswith('xmp') for item in result.document.notices)
    layers = [item.message for item in result.document.notices if item.code == 'visible-layer']
    assert layers == ['Visible source group/layer: Layer_2_1_ / Layer_1-2',
                      'Visible source group/layer: Layer_2_1_ / Layer_1-2 / Layer_2-2']
    elements = result.document.elements
    assert [element.kind for element in elements] == ['path'] * 4 + ['rect'] + ['path'] * 4 + ['rect']
    assert [dict(element.attributes).get('class') for element in elements] == ['st0'] * 4 + ['st1'] + [None] * 4 + ['st2']
    assert all(element.paint.fill_rule == 'nonzero' for element in elements)
    # The embedded fill:none class leaves the construction rectangle without material.
    assert not elements[4].paint.fill and not elements[4].paint.stroke and not result.rendered[4].geometry_mm
    # The stroke-only frame: 520.1 x 560.9 user units, 40-unit stroke, mitred square corners.
    frame = union_all(result.rendered[9].geometry_mm)
    assert elements[9].paint.stroke and elements[9].paint.width == 40 and not elements[9].paint.fill
    x0, x1, y0, y1 = 2474.7 * _PX, 3034.8 * _PX, 47.7 * _PX, 648.6 * _PX
    if flip:
        y0, y1 = height - y1, height - y0
    assert frame.bounds == pytest.approx((x0, y0, x1, y1), abs=1e-6)
    assert frame.area == pytest.approx((560.1 * 600.9 - 480.1 * 520.9) * _PX ** 2, rel=1e-9)
    assert len(frame.interiors) == 1
    # Nonzero compound lettering keeps its opposite-winding counters as holes.
    material = union_all(result.geometry_mm)
    assert material.is_valid and len(material.geoms) == 16
    assert sum(len(polygon.interiors) for polygon in material.geoms) == 25
    assert material.bounds[2] == pytest.approx(x1, abs=1e-6)
