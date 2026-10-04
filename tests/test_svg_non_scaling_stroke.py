"""Physical semantics of vector-effect="non-scaling-stroke" (spec 041, US2).

The stroke width is measured in the root viewport's CSS pixel space (1 px = 25.4/96 mm, zoom 1),
independent of viewBox scale and element transforms. Unpainted strokes are an exact no-op.
"""
import math

import pytest
from shapely import union_all

from mikrocam.bridge.svg_import import import_svg_bytes
from mikrocam.core.svg_transform import non_scaling_stroke_width

PX = 25.4 / 96
ROOT = 'width="100mm" height="100mm" viewBox="0 0 1000 1000"'  # 0.1 mm per user unit.


def load(body, root=ROOT, *, flip=False, object_type='geometry'):
    source = f'<svg xmlns="http://www.w3.org/2000/svg" {root}>{body}</svg>'.encode()
    return import_svg_bytes(source, 'nss.svg', flip=flip, object_type=object_type)


def material(body, root=ROOT, **kwargs):
    return union_all(load(body, root, **kwargs).geometry_mm)


def test_width_is_root_css_pixels_divided_by_the_similarity_scale():
    assert non_scaling_stroke_width(3., (.1, 0., 0., .1, 5., 7.)) == pytest.approx(3 * PX / .1, rel=1e-12)
    rotated = (.2 * math.cos(.5), -.2 * math.sin(.5), .2 * math.sin(.5), .2 * math.cos(.5), 0., 0.)
    assert non_scaling_stroke_width(2., rotated) == pytest.approx(2 * PX / .2, rel=1e-12)
    assert non_scaling_stroke_width(2., (0., .2, .2, 0., 0., 0.)) == pytest.approx(2 * PX / .2, rel=1e-12)
    assert non_scaling_stroke_width(2., (.1, 0., 0., -.1, 0., 50.)) == pytest.approx(2 * PX / .1, rel=1e-12)
    assert non_scaling_stroke_width(0., (.1, 0., 0., .1, 0., 0.)) == 0


@pytest.mark.parametrize('matrix', [(.1, 0., 0., .2, 0., 0.), (.1, .05, 0., .1, 0., 0.),
                                    (.1, 0., .01, .1, 0., 0.)])
def test_non_similarity_mapping_is_rejected_not_guessed(matrix):
    with pytest.raises(ValueError, match='non-uniform scale or skew'):
        non_scaling_stroke_width(1., matrix)


@pytest.mark.parametrize('flip', [False, True])
@pytest.mark.parametrize('object_type', ['geometry', 'gerber'])
def test_painted_stroke_width_ignores_viewbox_scale(flip, object_type):
    line = '<line x1="100" y1="500" x2="900" y2="500" stroke="black" stroke-width="3" {}/>'
    shape = material(line.format('vector-effect="non-scaling-stroke"'), flip=flip, object_type=object_type)
    half = 3 * PX / 2
    assert shape.bounds == pytest.approx((10, 50 - half, 90, 50 + half), abs=1e-9)
    assert shape.area == pytest.approx(80 * 3 * PX, rel=1e-12)
    scaling = material(line.format(''), flip=flip, object_type=object_type)
    assert scaling.bounds == pytest.approx((10, 49.85, 90, 50.15), abs=1e-9)


def test_rotation_scale_and_use_translation_do_not_change_physical_width():
    body = ('<defs><line id="seg" x1="100" y1="250" x2="400" y2="250" stroke="black" stroke-width="3" '
            'vector-effect="non-scaling-stroke"/></defs>'
            '<g transform="rotate(30 500 500) scale(2)"><use href="#seg" x="10" y="20"/></g>')
    shape = material(body)
    assert shape.area == pytest.approx(60 * 3 * PX, rel=1e-9)  # 300 units x2 = 60 mm, butt caps.


def test_absolute_stroke_width_unit_is_its_own_physical_length():
    body = ('<g transform="scale(4)"><line x1="25" y1="125" x2="225" y2="125" stroke="red" '
            'stroke-width="0.5mm" vector-effect="non-scaling-stroke"/></g>')
    shape = material(body)
    assert shape.bounds == pytest.approx((10, 49.75, 90, 50.25), abs=1e-9)


def test_round_joined_circle_ring_has_the_screen_space_width():
    body = ('<circle cx="500" cy="500" r="100" fill="none" stroke="black" stroke-width="2" '
            'stroke-linejoin="round" vector-effect="non-scaling-stroke"/>')
    half = 2 * PX / 2
    shape = material(body)
    assert shape.area == pytest.approx(math.pi * ((10 + half) ** 2 - (10 - half) ** 2), rel=2e-3)
    assert shape.bounds == pytest.approx((40 - half, 40 - half, 60 + half, 60 + half), abs=.011)


UNPAINTED = ['fill="black"', 'fill="#000000" stroke="none" stroke-width="7"',
             'fill="black" stroke="black" stroke-width="0"', 'fill="black" stroke="black" stroke-opacity="0"']


@pytest.mark.parametrize('paint', UNPAINTED)
@pytest.mark.parametrize('transform', ['', 'scale(3,1)', 'skewX(20)', 'matrix(1,0.3,0,2,5,5)'])
def test_unpainted_stroke_is_an_exact_no_op_under_any_transform(paint, transform):
    path = '<g transform="{}"><path {} {} d="M100,100 L300,100 L300,250 C250,300 150,300 100,250"/></g>'
    expected = material(path.format(transform, paint, ''))
    actual = material(path.format(transform, paint, 'vector-effect="non-scaling-stroke"'))
    assert actual.equals_exact(expected, 0)


def test_unpainted_no_op_also_holds_for_non_uniform_root_and_root_transform():
    path = '<path fill="black" vector-effect="non-scaling-stroke" d="M100,100 L300,100 L300,250 Z"/>'
    root = 'width="100mm" height="100mm" viewBox="0 0 1000 500" preserveAspectRatio="none" transform="scale(2)"'
    assert material(path, root).equals_exact(material(path.replace(' vector-effect="non-scaling-stroke"', ''), root), 0)


def test_notices_are_aggregated_per_document_not_per_element():
    body = ('<path fill="black" vector-effect="non-scaling-stroke" d="M0,0 L10,0 L10,10 Z"/>' * 3
            + '<line x2="100" stroke="black" vector-effect="non-scaling-stroke"/>' * 2)
    notices = {notice.code: notice.message for notice in load(body).notices}
    assert '3 ' in notices['non-scaling-stroke-unpainted']
    assert '2 ' in notices['non-scaling-stroke'] and '25.4/96' in notices['non-scaling-stroke']
    assert sum(code.startswith('non-scaling') for code in notices) == 2


def test_css_spellings_and_class_rules_apply_the_same_semantics():
    inline = '<line x1="100" y1="500" x2="900" y2="500" stroke="black" stroke-width="3" style="VECTOR-EFFECT: Non-Scaling-Stroke"/>'
    css = ('<style>.n{vector-effect:non-scaling-stroke}</style>'
           '<line class="n" x1="100" y1="500" x2="900" y2="500" stroke="black" stroke-width="3"/>')
    for body in (inline, css):
        assert material(body).area == pytest.approx(80 * 3 * PX, rel=1e-12)


def test_explicit_inherit_takes_the_non_inherited_parent_value_none():
    body = '<g><line x1="100" y1="500" x2="900" y2="500" stroke="black" stroke-width="3" vector-effect="inherit"/></g>'
    assert material(body).area == pytest.approx(80 * .3, rel=1e-12)


PAINTED = '<line x1="100" y1="500" x2="900" y2="500" stroke="black" vector-effect="non-scaling-stroke"/>'


@pytest.mark.parametrize('root,body,message', [
    ('width="100mm" height="100mm" viewBox="0 0 1000 500" preserveAspectRatio="none"', PAINTED,
     'non-uniform scale or skew'),
    (ROOT, f'<g transform="skewX(10)">{PAINTED}</g>', 'non-uniform scale or skew'),
    (ROOT, f'<g transform="scale(2,1)">{PAINTED}</g>', 'non-uniform scale or skew'),
    (ROOT + ' transform="scale(2)"', PAINTED, 'root transform'),
    (ROOT, PAINTED.replace('non-scaling-stroke"', 'non-scaling-stroke viewport"'), 'vector-effect'),
    (ROOT, PAINTED.replace('non-scaling-stroke"', 'non-scaling-stroke screen"'), 'vector-effect'),
    (ROOT, PAINTED.replace('non-scaling-stroke', 'non-scaling-size'), 'vector-effect'),
    (ROOT, PAINTED.replace('non-scaling-stroke', 'fixed-position'), 'vector-effect'),
    (ROOT, PAINTED.replace('non-scaling-stroke', 'bogus'), 'vector-effect'),
    (ROOT, f'<g vector-effect="non-scaling-stroke">{PAINTED.replace(" vector-effect", " data-x")}</g>',
     'vector-effect'),
    (ROOT, '<g vector-effect="non-scaling-stroke"><path fill="black" d="M0,0 L1,0 L1,1 Z"/></g>', 'vector-effect'),
    (ROOT, '<defs><line id="l" x2="9" stroke="black"/></defs><use href="#l" vector-effect="non-scaling-stroke"/>',
     'vector-effect'),
    (ROOT + ' vector-effect="non-scaling-stroke"', '<path fill="black" d="M0,0 L1,0 L1,1 Z"/>', 'vector-effect'),
])
def test_ambiguous_or_unsupported_vector_effect_fails_explicitly(root, body, message):
    with pytest.raises(ValueError, match=message):
        load(body, root)
