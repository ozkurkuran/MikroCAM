"""Analytic regressions for conservative physical SVG hole interpretation."""
from dataclasses import replace
import math

import pytest

from mikrocam.bridge.svg_import import import_svg_bytes
from mikrocam.core.svg_drills import DrillCandidate, DrillReview, detect_svg_drills


def source(body, root='width="100mm" height="50mm" viewBox="0 0 100 50"'):
    return f'<svg xmlns="http://www.w3.org/2000/svg" {root}>{body}</svg>'.encode()


def pair(x=10, y=12, radius=0.5, pad=2, extra=''):
    return (f'<circle id="pad" cx="{x}" cy="{y}" r="{pad}" fill="black"/>'
            f'<circle id="hole" cx="{x}" cy="{y}" r="{radius}" fill="white" {extra}/>')


def review(body, *, flip=False, root='width="100mm" height="50mm" viewBox="0 0 100 50"'):
    return detect_svg_drills(import_svg_bytes(source(body, root), 'board.svg', flip=flip))


def test_native_circle_exact_physical_and_source_unchanged():
    imported = import_svg_bytes(source(pair()), 'board.svg', flip=False)
    before = tuple(g.wkb for g in imported.geometry_mm)
    result = detect_svg_drills(imported)
    assert len(result.candidates) == 1
    hole = result.candidates[0]
    assert hole.center_mm == pytest.approx((10, 12))
    assert hole.diameter_mm == pytest.approx(1)
    assert 'hole' in hole.opening_id and 'pad' in hole.pad_id
    assert result.source_sha256 == imported.document.source_sha256
    assert result.notices
    assert tuple(g.wkb for g in imported.geometry_mm) == before


@pytest.mark.parametrize('flip,y', [(False, 12), (True, 38)])
def test_flip_once(flip, y):
    result = review(pair(), flip=flip)
    assert result.flipped is flip
    assert result.candidates[0].center_mm == pytest.approx((10, y))


def test_nested_rotation_translation_and_unit_viewport():
    result = review('<g transform="translate(30 10) rotate(90) scale(2)">' + pair() + '</g>')
    assert result.candidates[0].center_mm == pytest.approx((6, 30))
    assert result.candidates[0].diameter_mm == pytest.approx(2)
    inch = review(pair(), root='width="1in" height="1in" viewBox="0 0 100 100"')
    assert inch.candidates[0].center_mm == pytest.approx((2.54, 3.048))
    assert inch.candidates[0].diameter_mm == pytest.approx(.254)


@pytest.mark.parametrize('shape', [
    '<rect x="9.5" y="11.5" width="1" height="1" fill="white"/>',
    '<ellipse cx="10" cy="12" rx=".5" ry=".4" fill="white"/>',
    '<path d="M9.5 11.5 H10.5 V12.5 H9.5 Z" fill="white"/>',
    '<path d="M9.5 12 A.5 .5 0 1 0 10.5 12" fill="white"/>',
    '<circle cx="10" cy="12" r=".5" fill="none" stroke="white"/>',
    '<circle cx="10" cy="12" r=".5" fill="white" stroke="black"/>',
    '<circle cx="10" cy="12" r=".5" fill="white" visibility="hidden"/>',
    '<circle cx="10" cy="12" r=".5" fill="black"/>',
])
def test_false_holes_are_not_offered(shape):
    assert not review('<circle cx="10" cy="12" r="2"/>' + shape).candidates


def test_isolated_white_nonconcentric_and_nonuniform_shapes_rejected():
    assert not review('<circle cx="10" cy="12" r=".5" fill="white"/>').candidates
    assert not review('<circle cx="10.03" cy="12" r="2"/>' +
                      '<circle cx="10" cy="12" r=".5" fill="white"/>').candidates
    assert not review('<g transform="scale(2 1)">' + pair() + '</g>').candidates


def test_transformed_ellipse_can_be_physical_circle():
    body = ('<g transform="scale(2 1)"><ellipse cx="10" cy="12" rx="1" ry="2"/>'
            '<ellipse cx="10" cy="12" rx=".25" ry=".5" fill="white"/></g>')
    assert review(body).candidates[0].diameter_mm == pytest.approx(1)


def test_closed_arc_path_and_inherited_color():
    body = ('<circle cx="10" cy="12" r="2"/><g fill="currentColor" color="#fff">'
            '<path d="M9.5 12 A.5 .5 0 1 0 10.5 12 A.5 .5 0 1 0 9.5 12 Z"/></g>')
    hole = review(body).candidates[0]
    assert hole.center_mm == pytest.approx((10, 12), abs=.001)
    assert hole.diameter_mm == pytest.approx(1, abs=.001)


def test_duplicate_equal_holes_collapse_and_conflicting_diameters_excluded():
    result = review(pair() + '<circle cx="10" cy="12" r=".5" fill="white"/>')
    assert len(result.candidates) == 1
    assert any('duplicate' in n.code for n in result.notices)
    conflict = review(pair() + '<circle cx="10" cy="12" r=".7" fill="white"/>')
    assert not conflict.candidates
    assert any('conflict' in n.code for n in conflict.notices)


def test_overlapping_different_centres_excluded():
    body = pair() + pair(x=10.8).replace('id="pad"', 'id="pad2"').replace('id="hole"', 'id="hole2"')
    assert not review(body).candidates


def test_stable_results_and_nearby_distinct_holes():
    first = pair()
    second = pair(x=20, radius=.4).replace('id="pad"', 'id="p2"').replace('id="hole"', 'id="h2"')
    result = review(first + second)
    other = review(second + first)
    assert [(c.center_mm, c.diameter_mm) for c in result.candidates] == [
        (c.center_mm, c.diameter_mm) for c in other.candidates]


@pytest.mark.parametrize('field,value', [('center_mm', (True, 0)), ('center_mm', (math.inf, 0)),
    ('center_mm', [0, 0]), ('center_mm', (1e10, 0)), ('diameter_mm', 0), ('diameter_mm', -1),
    ('diameter_mm', True), ('diameter_mm', math.nan), ('diameter_mm', 1e10),
    ('opening_id', ''), ('pad_id', 'a'*257)])
def test_strict_candidate(field, value):
    good = DrillCandidate((0., 0.), 1., 'hole', 'pad')
    with pytest.raises(ValueError):
        replace(good, **{field: value})


@pytest.mark.parametrize('field,value', [('source_name', ''), ('source_name', 'a'*257),
    ('source_name', '\ud800'), ('source_sha256', 'Z'*64), ('flipped', 1),
    ('candidates', []), ('candidates', (None,)), ('notices', [])])
def test_strict_review(field, value):
    good = DrillReview('board.svg', '0'*64, False, (), ())
    with pytest.raises(ValueError):
        replace(good, **{field: value})


def test_circle_evidence_cap_fails_without_partial_results():
    body = ''.join(f'<circle cx="{i}" cy="1" r=".1"/>' for i in range(1001))
    with pytest.raises(ValueError, match='limit|1000|budget'):
        review(body)


def test_authored_fixture_three_holes_and_deterministic_groups():
    from pathlib import Path
    from mikrocam.core.drill_groups import group_drill_selection
    data = Path('tests/reference/svg-drills.svg').read_bytes()
    result = detect_svg_drills(import_svg_bytes(data, 'svg-drills.svg', flip=True))
    assert len(result.candidates) == 3
    for actual, expected in zip(result.candidates, ((15., 37.), (25., 37.), (35., 37.))):
        assert actual.center_mm == pytest.approx(expected, abs=1e-8)
    tools = group_drill_selection(result, (0, 1, 2))
    assert len(tools) == 2
    assert [tool.diameter_mm for tool in tools] == pytest.approx([.8, 1.2], abs=1e-6)


def test_notice_omission_and_unknown_fill_facts():
    body = '<circle cx="0" cy="0" r="2"/>' + ''.join(
        f'<rect x="{i}" y="0" width="1" height="1" fill="white"/>' for i in range(205))
    result = review(body)
    assert len(result.notices) == 200
    assert result.notices[-1].code == 'notices-truncated'
    parsed = import_svg_bytes(source(pair()), 'b.svg', flip=False)
    document = replace(parsed.document, elements=tuple(replace(e, fill_is_white=None) for e in parsed.document.elements))
    assert not detect_svg_drills(replace(parsed, document=document)).candidates


def test_duplicate_tolerance_does_not_chain_to_conflicting_diameter():
    body = pair() + ''.join(f'<circle cx="10" cy="12" r="{r}" fill="white"/>' for r in (.504, .508))
    assert not review(body).candidates


def test_compound_path_white_artwork_is_not_single_hole():
    body = ('<circle cx="10" cy="12" r="2"/>'
            '<path fill="white" fill-rule="evenodd" d="M9.5 12 A.5 .5 0 1 0 10.5 12 '
            'A.5 .5 0 1 0 9.5 12 Z M9.8 12 A.2 .2 0 1 0 10.2 12 A.2 .2 0 1 0 9.8 12 Z"/>')
    assert not review(body).candidates
