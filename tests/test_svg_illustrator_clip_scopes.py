"""Independent analytic scope and bounded expansion checks through actual SVG import."""
import pytest
from shapely import union_all

from mikrocam.bridge.svg_import import import_svg_bytes


def source(body, attrs='width="100mm" height="100mm" viewBox="0 0 100 100"'):
    return f'<svg {attrs}>{body}</svg>'.encode('utf-8')


def test_root_bbox_clip_respects_viewbox_origin_scale_and_outer_root_transform():
    payload = source('<defs><clipPath id="c" clipPathUnits="objectBoundingBox">'
                     '<rect x=".25" y=".2" width=".5" height=".6"/></clipPath></defs>'
                     '<rect x="20" y="25" width="20" height="10"/>',
                     'width="120mm" height="60mm" viewBox="10 20 60 30" '
                     'transform="translate(96 0)" clip-path="url(#c)"')
    result = import_svg_bytes(payload, 'root-scope.svg', flip=False)
    material = union_all(result.geometry_mm)
    # The selected middle 50% x / 60% y is 10x6 source units, then 2mm/unit.
    # Root translation is outside viewBox: 96 CSS pixels = 25.4mm.
    assert material.bounds == pytest.approx((55.4, 14, 75.4, 26))
    assert material.area == pytest.approx(240, abs=.001)
    assert len(result.document.elements[0].clips) == 1


def test_repeated_local_use_bbox_applications_have_independent_physical_scopes():
    payload = source('<defs><clipPath id="half" clipPathUnits="objectBoundingBox">'
                     '<rect width=".5" height="1"/></clipPath>'
                     '<g id="part" clip-path="url(#half)"><rect width="10" height="4"/></g></defs>'
                     '<use href="#part" x="10" y="5"/>'
                     '<use href="#part" x="40" y="15" transform="scale(2 3)"/>')
    result = import_svg_bytes(payload, 'separate-use.svg', flip=False)
    first, second = (union_all(rendered.geometry_mm) for rendered in result.rendered)
    assert first.bounds == pytest.approx((10, 5, 15, 9))
    assert first.area == pytest.approx(20)
    assert second.bounds == pytest.approx((80, 45, 90, 57))
    assert second.area == pytest.approx(120)
    assert union_all(result.geometry_mm).area == pytest.approx(140)
    clips = [element.clips[0] for element in result.document.elements]
    assert clips[0].source_id == clips[1].source_id == 'half'
    assert clips[0].application_id != clips[1].application_id


def test_two_node_local_clip_use_cycle_is_rejected_without_partial_result():
    payload = source('<defs><use id="a" href="#b"/><use id="b" href="#a"/>'
                     '<clipPath id="c"><use href="#a"/></clipPath></defs>'
                     '<rect width="10" height="10"/>'
                     '<rect width="10" height="10" clip-path="url(#c)"/>')
    with pytest.raises(ValueError, match='[Cc]yclic|reference'):
        import_svg_bytes(payload, 'two-node-cycle.svg', flip=False)


def chain_source(use_count):
    nodes = ''.join(f'<use id="u{i}" href="#u{i+1}"/>' for i in range(use_count - 1))
    nodes += f'<use id="u{use_count-1}" href="#shape"/>'
    return source('<defs><rect id="shape" x="2" y="3" width="4" height="5"/>' + nodes
                  + '<clipPath id="c"><use href="#u0"/></clipPath></defs>'
                  '<rect width="10" height="10" clip-path="url(#c)"/>')


def test_exact_clip_reference_depth_boundary_accepts_32_source_ids():
    # One clip ID + 30 distinct use IDs + one shape ID = 32 referenced IDs.
    result = import_svg_bytes(chain_source(30), 'depth32.svg', flip=False)
    material = union_all(result.geometry_mm)
    assert material.bounds == pytest.approx((2, 3, 6, 8))
    assert material.area == pytest.approx(20)


def test_clip_reference_depth_33_is_explicitly_rejected():
    with pytest.raises(ValueError, match='excessive|depth|reference'):
        import_svg_bytes(chain_source(31), 'depth33.svg', flip=False)


def test_reduced_clip_pair_budget_rejects_before_union_overlay(monkeypatch):
    import mikrocam.core.svg_clip as clipping
    overlay_calls = []
    original_union = clipping.union_all

    def observe_union(*args, **kwargs):
        overlay_calls.append(True)
        return original_union(*args, **kwargs)

    monkeypatch.setattr(clipping, 'MAX_CLIP_PAIRS', 0)
    monkeypatch.setattr(clipping, 'union_all', observe_union)
    payload = source('<defs><clipPath id="c"><rect width="5" height="5"/></clipPath></defs>'
                     '<rect width="10" height="10" clip-path="url(#c)"/>')
    with pytest.raises(ValueError, match='budget|simplify'):
        import_svg_bytes(payload, 'pair-budget.svg', flip=False)
    assert overlay_calls == []
