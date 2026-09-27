"""Authored analytic fixtures exercise the actual complete offline SVG import."""
import hashlib

import pytest
from shapely import union_all

from mikrocam.bridge.svg_import import import_svg_bytes
from mikrocam.core.import_report import build_import_report
from mikrocam.core.svg_drills import detect_svg_drills


def svg(body, attrs='width="100mm" height="100mm" viewBox="0 0 100 100"'):
    return f'<svg {attrs}>{body}</svg>'.encode('utf-8')


def imported(body, *, flip=False):
    return import_svg_bytes(svg(body), 'analytic-illustrator.svg', flip=flip)


def assert_material(result, bounds, area):
    material = union_all(result.geometry_mm)
    assert material.is_valid
    assert material.bounds == pytest.approx(bounds, abs=1e-9)
    assert material.area == pytest.approx(area, abs=.001)


def test_xmp_css_hidden_layers_and_visible_child_preserve_raw_source_facts():
    payload = svg(
        '<metadata><t:MaxPageSize d:w="20" d:h="40" d:unit="mm"/></metadata>'
        '<style>.hidden{display:none}.veil{visibility:hidden}.show{visibility:visible}</style>'
        '<g id="hidden-layer" class="hidden"><rect width="10" height="20"/></g>'
        '<g id="visible-layer" class="veil"><rect width="10" height="20"/>'
        '<rect id="chosen" class="show" x="2" y="3" width="4" height="5"/></g>',
        'width="100%" height="100%" viewBox="0 0 10 20" '
        'xmlns:t="http://ns.adobe.com/xap/1.0/t/pg/" '
        'xmlns:d="http://ns.adobe.com/xap/1.0/sType/Dimensions#"')
    result = import_svg_bytes(payload, 'layers.svg', flip=False)
    assert_material(result, (4, 6, 12, 16), 80)
    assert len(result.document.elements) == 1
    element = result.document.elements[0]
    assert dict(element.attributes)['class'] == 'show'
    assert 'style' not in dict(element.attributes)
    assert element.layer_path == ('visible-layer',)
    report = build_import_report(result)
    assert report.source_sha256 == hashlib.sha256(payload).hexdigest()
    assert report.coordinates.source_width == report.coordinates.source_height == '100%'
    assert report.coordinates.viewport_mm == pytest.approx((20, 40))
    assert report.quality.bounds_mm == pytest.approx((4, 6, 12, 16))
    assert any('xmp' in notice.message.lower() for notice in report.notices)


@pytest.mark.parametrize(('path', 'rule', 'area'), [
    ('M0 0H10V10H0Z M5 0H15V10H5Z', 'nonzero', 150),
    ('M0 0H10V10H0Z M5 0H15V10H5Z', 'evenodd', 100),
    ('M0 0H10V10H0Z M5 0V10H15V0Z', 'nonzero', 100),
    ('M0 0L10 10L0 10L10 0Z', 'evenodd', 50),
])
def test_compound_linear_area_and_retained_source_contours(path, rule, area):
    result = imported(f'<path d="{path}" fill-rule="{rule}"/>')
    assert union_all(result.geometry_mm).area == pytest.approx(area, abs=.001)
    assert dict(result.document.elements[0].attributes)['d'] == path
    assert len(result.rendered[0].paths_mm) == (1 if 'L10 10' in path else 2)
    assert all(p.closed for p in result.rendered[0].paths_mm)


def test_user_space_clip_transform_is_in_target_group_frame():
    result = imported('<defs><clipPath id="c"><rect x="1" y="2" width="3" height="4"/></clipPath></defs>'
                      '<g transform="translate(10 20) scale(2)" clip-path="url(#c)">'
                      '<rect width="10" height="10"/></g>')
    assert_material(result, (12, 24, 18, 32), 48)


def test_nested_parent_child_clips_intersect_and_keep_unclipped_paths_for_report():
    payload = svg('<defs><clipPath id="parent"><rect width="8" height="10"/></clipPath>'
                  '<clipPath id="child"><rect x="4" y="2" width="6" height="6"/></clipPath></defs>'
                  '<g id="layer" clip-path="url(#parent)"><rect id="target" width="10" height="10" '
                  'clip-path="url(#child)"/></g>')
    result = import_svg_bytes(payload, 'intersection.svg', flip=False)
    assert_material(result, (4, 2, 8, 8), 24)
    assert len(result.document.elements) == len(result.rendered) == 1
    assert len(result.document.elements[0].clips) == 2
    assert len(result.rendered[0].paths_mm) == 1
    assert max(p[0] for p in result.rendered[0].paths_mm[0].points) == 10
    report = build_import_report(result)
    assert report.quality.bounds_mm == (4, 2, 8, 8)
    assert report.quality.closed_paths == 1
    assert report.source_sha256 == hashlib.sha256(payload).hexdigest()


def test_object_bbox_uses_unstroked_shape_bounds():
    result = imported('<defs><clipPath id="c" clipPathUnits="objectBoundingBox">'
                      '<rect width=".5" height="1"/></clipPath></defs>'
                      '<rect x="10" y="10" width="20" height="10" stroke="black" stroke-width="4" '
                      'clip-path="url(#c)"/>')
    assert_material(result, (10, 10, 20, 20), 100)


def test_group_object_bbox_spans_all_unclipped_source_paths_including_gap():
    result = imported('<defs><clipPath id="c" clipPathUnits="objectBoundingBox">'
                      '<rect width="75%" height="100%"/></clipPath></defs>'
                      '<g clip-path="url(#c)"><rect x="10" y="10" width="10" height="10"/>'
                      '<rect x="30" y="10" width="10" height="10"/></g>')
    assert_material(result, (10, 10, 32.5, 20), 125)
    assert len(result.document.elements) == 2
    assert result.document.elements[0].clips[0].application_id == result.document.elements[1].clips[0].application_id


def test_clip_children_are_union_not_intersection():
    result = imported('<defs><clipPath id="c"><rect width="4" height="10"/>'
                      '<rect x="6" width="4" height="10"/></clipPath></defs>'
                      '<rect width="10" height="10" clip-path="url(#c)"/>')
    assert_material(result, (0, 0, 10, 10), 80)
    assert len(union_all(result.geometry_mm).geoms) == 2


@pytest.mark.parametrize(('clip_rule', 'target_rule', 'area'), [('evenodd', 'nonzero', 64),
                                                            ('nonzero', 'evenodd', 100)])
def test_clip_own_winding_rule_is_independent_of_target_fill_and_clip_rules(clip_rule, target_rule, area):
    result = imported(f'<defs><clipPath id="c" clip-rule="{clip_rule}">'
                      '<path d="M0 0H10V10H0Z M2 2H8V8H2Z" fill-rule="evenodd"/></clipPath></defs>'
                      f'<rect width="10" height="10" fill-rule="{target_rule}" clip-rule="{target_rule}" '
                      'clip-path="url(#c)"/>')
    assert_material(result, (0, 0, 10, 10), area)


def test_clip_path_is_not_inherited_but_ancestor_application_still_restricts_child():
    result = imported('<defs><clipPath id="c"><rect width="3" height="10"/></clipPath></defs>'
                      '<g clip-path="url(#c)"><rect width="10" height="10"/></g>')
    assert_material(result, (0, 0, 3, 10), 30)
    assert len(result.document.elements[0].clips) == 1


def test_css_clip_reference_is_applied_without_injecting_style_into_source_facts():
    result = imported('<style>.cut{clip-path:url(#c)}</style>'
                      '<defs><clipPath id="c"><rect x="2" width="3" height="10"/></clipPath></defs>'
                      '<rect class="cut" width="10" height="10"/>')
    assert_material(result, (2, 0, 5, 10), 30)
    attributes = dict(result.document.elements[0].attributes)
    assert attributes['class'] == 'cut' and 'style' not in attributes and 'clip-path' not in attributes


def test_empty_clip_definition_leaves_no_importable_material():
    with pytest.raises(ValueError, match='material|geometry|empty'):
        imported('<defs><clipPath id="c"/></defs><rect width="10" height="10" clip-path="url(#c)"/>')


@pytest.mark.parametrize('flip', [False, True])
def test_clip_geometry_and_target_are_reflected_exactly_once(flip):
    result = imported('<defs><clipPath id="c"><rect x="2" y="10" width="3" height="4"/></clipPath></defs>'
                      '<rect x="1" y="8" width="10" height="10" clip-path="url(#c)"/>', flip=flip)
    assert_material(result, (2, 86, 5, 90) if flip else (2, 10, 5, 14), 12)


@pytest.mark.parametrize('hidden', ['display="none"', 'visibility="hidden"', 'style="display:none"'])
def test_hidden_clip_silhouette_is_empty_not_ignored(hidden):
    result = imported(f'<defs><clipPath id="c"><rect width="10" height="10" {hidden}/></clipPath></defs>'
                      '<rect width="10" height="10" clip-path="url(#c)"/>'
                      '<rect x="90" y="90" width="1" height="1"/>')
    assert_material(result, (90, 90, 91, 91), 1)
    assert result.rendered[0].geometry_mm == ()
    assert len(result.rendered[0].paths_mm) == 1


def test_clip_silhouette_ignores_opacity_fill_none_and_stroke_expansion():
    result = imported('<defs><clipPath id="c" opacity="0"><rect x="2" y="3" width="4" height="5" '
                      'fill="none" stroke="black" stroke-width="20" fill-opacity="0"/></clipPath></defs>'
                      '<rect width="10" height="10" clip-path="url(#c)"/>')
    assert_material(result, (2, 3, 6, 8), 20)


def test_clip_local_use_translates_silhouette_without_publishing_definition():
    result = imported('<defs><rect id="r" width="2" height="4"/>'
                      '<clipPath id="c"><use href="#r" x="2" y="3"/></clipPath></defs>'
                      '<rect width="10" height="10" clip-path="url(#c)"/>')
    assert_material(result, (2, 3, 4, 7), 8)
    assert len(result.document.elements) == 1


@pytest.mark.parametrize('body', [
    '<rect width="10" height="10" clip-path="url(other.svg#c)"/>',
    '<rect width="10" height="10" clip-path="url(#missing)"/>',
    '<defs><clipPath id="c"><rect width="10" height="10" clip-path="url(#c)"/></clipPath></defs>'
    '<rect width="10" height="10" clip-path="url(#c)"/>',
    '<defs><clipPath id="c"><g><rect width="10" height="10"/></g></clipPath></defs>'
    '<rect width="10" height="10" clip-path="url(#c)"/>',
    '<defs><clipPath id="c"><text>unresolved</text></clipPath></defs>'
    '<rect width="10" height="10" clip-path="url(#c)"/>',
    '<defs><clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="1mm" height="1"/></clipPath></defs>'
    '<rect width="10" height="10" clip-path="url(#c)"/>',
])
def test_invalid_clip_cannot_return_success_after_other_valid_artwork(body):
    payload = svg('<rect x="90" y="90" width="1" height="1"/>' + body)
    before = hashlib.sha256(payload).hexdigest()
    with pytest.raises(ValueError):
        import_svg_bytes(payload, 'invalid.svg', flip=False)
    assert hashlib.sha256(payload).hexdigest() == before


def test_clipped_white_circle_is_not_inferred_as_complete_drill():
    result = imported('<defs><clipPath id="c"><rect width="10" height="5"/></clipPath></defs>'
                      '<circle id="pad" cx="5" cy="5" r="3" fill="black"/>'
                      '<circle id="opening" cx="5" cy="5" r="1" fill="white" clip-path="url(#c)"/>')
    review = detect_svg_drills(result)
    assert review.candidates == ()
    assert any('clip' in notice.message.lower() for notice in review.notices)


def test_many_visible_layers_keep_bounded_notices_and_vertical_flip():
    result = imported(''.join(f'<g id="layer{i}"><rect width="1" height="2"/></g>'
                              for i in range(210)), flip=True)
    assert len(result.document.notices) <= 200
    assert any(n.code == 'vertical-flip' for n in result.document.notices)
    assert any(n.code == 'layers-truncated' for n in result.document.notices)
    assert_material(result, (0, 98, 1, 100), 2)


@pytest.mark.parametrize('definition', [
    '<clipPath id="c" clipPathUnits="unknown"><rect width="1" height="1"/></clipPath>',
    '<use id="r" href="#r"/><clipPath id="c"><use href="#r"/></clipPath>',
    '<clipPath id="c">' + '<rect width="1" height="1"/>' * 65 + '</clipPath>',
])
def test_invalid_or_excessive_clip_expansion_is_rejected(definition):
    with pytest.raises(ValueError):
        imported(f'<defs>{definition}</defs><rect width="10" height="10" clip-path="url(#c)"/>')


def test_clip_chain_rejects_ninth_application():
    with pytest.raises(ValueError, match='chain'):
        imported('<defs><clipPath id="c"><rect width="10" height="10"/></clipPath></defs>'
                 + '<g clip-path="url(#c)">' * 9 + '<rect width="10" height="10"/>' + '</g>' * 9)


def test_bounding_box_clip_rejects_zero_width_source_path():
    with pytest.raises(ValueError, match='nonzero'):
        imported('<defs><clipPath id="c" clipPathUnits="objectBoundingBox">'
                 '<rect width="1" height="1"/></clipPath></defs>'
                 '<line y2="10" stroke="black" clip-path="url(#c)"/>')


def test_bbox_local_use_percent_offset_is_normalized_before_application():
    result = imported('<defs><rect id="r" width="25%" height="100%"/>'
                      '<clipPath id="c" clipPathUnits="objectBoundingBox">'
                      '<use href="#r" x="50%"/></clipPath></defs>'
                      '<rect x="10" y="20" width="20" height="10" clip-path="url(#c)"/>')
    assert_material(result, (20, 20, 25, 30), 50)
