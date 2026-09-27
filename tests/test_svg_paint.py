"""Independent analytic fixtures for local SVG primitives and material paint."""
import math

import pytest
from shapely import union_all
from shapely.geometry import Polygon

from mikrocam.core.svg_models import SvgPaint, SvgPath
from mikrocam.core.svg_paint import primitive_paths, render_svg_paths


IDENTITY = (1., 0., 0., 1., 0., 0.)


def attrs(**values):
    return tuple((key, str(value)) for key, value in values.items())


def square(x=0., y=0., side=10., clockwise=False):
    points = ((x, y), (x + side, y), (x + side, y + side), (x, y + side), (x, y))
    return SvgPath(tuple(reversed(points)) if clockwise else points, True)


def geometry(paths, paint=SvgPaint(), matrix=IDENTITY, **kwargs):
    return union_all(render_svg_paths(paths, paint, matrix, **kwargs).geometry_mm)


def test_rect_absolute_local_lengths_and_closed_metadata():
    paths = primitive_paths('rect', attrs(x='1in', y='2mm', width='2.54cm', height='72pt'), .005)
    assert paths[0].closed and paths[0].points[0] == paths[0].points[-1]
    result = geometry(paths)
    assert result.bounds == pytest.approx((96., 2 * 96 / 25.4, 192., 2 * 96 / 25.4 + 96.))
    assert result.area == pytest.approx(96. ** 2)


@pytest.mark.parametrize('kind,values', [('rect', dict(width=0, height=3)),
                                      ('circle', dict(r=0)), ('ellipse', dict(rx=3, ry=0))])
def test_zero_sized_primitives_are_empty(kind, values):
    assert primitive_paths(kind, attrs(**values), .005) == ()


@pytest.mark.parametrize('kind,values', [('rect', dict(width=-1, height=0)),
                                      ('rect', dict(width=3, height=3, rx=-1)),
                                      ('circle', dict(r=-1)), ('ellipse', dict(rx=1, ry=-2))])
def test_negative_dimensions_rejected(kind, values):
    with pytest.raises(ValueError):
        primitive_paths(kind, attrs(**values), .005)


def test_circle_ellipse_and_rounded_rect_analytic_area():
    circle = geometry(primitive_paths('circle', attrs(cx=5, cy=-2, r=3), .001))
    assert circle.bounds == pytest.approx((2., -5., 8., 1.))
    assert abs(circle.area - math.pi * 9) < .03
    ellipse = geometry(primitive_paths('ellipse', attrs(rx=4, ry=2), .001))
    assert ellipse.bounds == pytest.approx((-4., -2., 4., 2.))
    assert abs(ellipse.area - math.pi * 8) < .04
    rounded = geometry(primitive_paths('rect', attrs(width=10, height=6, rx=2), .001))
    assert rounded.bounds == pytest.approx((0., 0., 10., 6.))
    assert abs(rounded.area - (60 - 16 + math.pi * 4)) < .03


def test_rounded_rect_radius_clamped_and_missing_partner_inherited():
    paths = primitive_paths('rect', attrs(width=8, height=4, ry=99), .001)
    assert abs(geometry(paths).area - math.pi * 8) < .04


def test_lines_polygons_and_polylines_preserve_source_closure():
    assert primitive_paths('line', attrs(x1=1, y1=2, x2=3, y2=4), .005) == (
        SvgPath(((1., 2.), (3., 4.))),)
    opened = primitive_paths('polyline', attrs(points='0,0 10,0 0,10'), .005)
    closed = primitive_paths('polygon', attrs(points='0,0 10,0 0,10'), .005)
    assert not opened[0].closed and closed[0].closed
    assert geometry(opened).area == 50
    rendered = render_svg_paths(opened, SvgPaint(), IDENTITY)
    assert not rendered.paths_mm[0].closed and len(rendered.paths_mm[0].points) == 3


@pytest.mark.parametrize('kind,values', [('path', {}), ('polygon', dict(points='0 0 1')),
                                      ('polyline', dict(points='0,0 bad')),
                                      ('circle', dict(r='nan')), ('rect', dict(width='10%', height=1))])
def test_invalid_primitive_syntax_rejected(kind, values):
    with pytest.raises(ValueError):
        primitive_paths(kind, attrs(**values), .005)


@pytest.mark.parametrize('rule,reverse,area', [('evenodd', False, 64), ('evenodd', True, 64),
                                           ('nonzero', False, 100), ('nonzero', True, 64)])
def test_fill_rules_nested_orientation(rule, reverse, area):
    result = geometry((square(), square(2., 2., 6., reverse)), SvgPaint(fill_rule=rule))
    assert result.area == area


def test_nested_island_and_disjoint_ring_fill():
    result = geometry((square(), square(2., 2., 6., True), square(4., 4., 2.), square(20., 0., 3.)))
    assert result.area == 77
    assert len(result.geoms) == 3


def test_self_intersecting_fill_rejected_without_repair():
    bow = SvgPath(((0., 0.), (3., 3.), (0., 3.), (3., 0.), (0., 0.)), True)
    with pytest.raises(ValueError, match='simple|intersect|valid'):
        geometry((bow,))


def test_crossing_simple_rings_rejected_until_compound_scope():
    with pytest.raises(ValueError, match='ring|intersect'):
        geometry((square(), square(5., 5.)))


@pytest.mark.parametrize('points', [((0., 0.), (3., 3.), (0., 3.), (3., 0.)),
                                    ((0., 0.), (3., 0.), (1., 0.), (4., 0.))])
def test_self_crossing_or_overlapping_open_stroke_rejected(points):
    with pytest.raises(ValueError, match='simple|intersect|overlap'):
        geometry((SvgPath(points),), SvgPaint(fill=False, stroke=True))


@pytest.mark.parametrize('cap,bounds,area', [('butt', (0., -1., 10., 1.), 20),
                                        ('square', (-1., -1., 11., 1.), 24),
                                        ('round', (-1., -1., 11., 1.), 20 + math.pi)])
def test_stroke_caps_are_solid_local_material(cap, bounds, area):
    result = geometry((SvgPath(((0., 0.), (10., 0.))),),
                      SvgPaint(fill=False, stroke=True, width=2., linecap=cap))
    assert result.bounds == pytest.approx(bounds)
    assert abs(result.area - area) < .04


def test_stroke_expands_before_nonuniform_affine():
    line = SvgPath(((0., 0.), (10., 0.)))
    matrix = (3., 1., 0., 2., 7., -4.)
    result = geometry((line,), SvgPaint(fill=False, stroke=True, width=2.), matrix)
    assert result.bounds == pytest.approx((6., -6., 38., -2.))
    assert result.area == pytest.approx(120.)


def test_round_stroke_error_budget_survives_affine_amplification():
    result = geometry((SvgPath(((0., 0.), (0., 0.))),),
                      SvgPaint(fill=False, stroke=True, width=4., linecap='round'),
                      (10., 0., 0., 3., 0., 0.))
    analytic = Polygon(tuple((20 * math.cos(i * math.tau / 10000),
                              6 * math.sin(i * math.tau / 10000)) for i in range(10000)))
    assert result.hausdorff_distance(analytic) < .005


@pytest.mark.parametrize('cap,area', [('butt', 0.), ('square', 4.), ('round', math.pi)])
@pytest.mark.parametrize('closed', [False, True])
def test_zero_length_stroke_cap_material(cap, area, closed):
    result = geometry((SvgPath(((3., 4.),) * (4 if closed else 2), closed),),
                      SvgPaint(fill=False, stroke=True, width=2., linecap=cap))
    assert abs(result.area - area) < .04


def test_local_stroke_bounds_are_checked_before_small_affine():
    path = SvgPath(((1e9, 0.), (1e9, 1.)))
    with pytest.raises(ValueError, match='bounds|coordinates'):
        geometry((path,), SvgPaint(fill=False, stroke=True, width=2.),
                 (.001, 0., 0., .001, 0., 0.))


def test_join_modes_and_miter_limit_change_material():
    path = SvgPath(((0., 0.), (5., 0.), (5., 5.)))
    areas = {}
    for join in ('miter', 'round', 'bevel'):
        areas[join] = geometry((path,), SvgPaint(fill=False, stroke=True, width=2., linejoin=join)).area
    assert areas['miter'] > areas['round'] > areas['bevel']
    sharp = SvgPath(((0., 0.), (5., 0.), (0., 1.)))
    low = geometry((sharp,), SvgPaint(fill=False, stroke=True, width=2., miterlimit=1.))
    high = geometry((sharp,), SvgPaint(fill=False, stroke=True, width=2., miterlimit=20.))
    assert high.bounds[2] > low.bounds[2] + 4


@pytest.mark.parametrize('limit', [0., .5, 1., 4.])
def test_exceeded_svg_miter_falls_back_to_bevel_instead_of_clipped_miter(limit):
    path = SvgPath(((0., 0.), (5., 0.), (0., 1.)))
    actual = geometry((path,), SvgPaint(fill=False, stroke=True, width=2., miterlimit=limit))
    expected = geometry((path,), SvgPaint(fill=False, stroke=True, width=2., linejoin='bevel'))
    assert actual.symmetric_difference(expected).area < 1e-12


@pytest.mark.parametrize('points', [((0., 0.), (5., 0.), (5., 5.), (4., .5)),
                                   ((0., 0.), (5., 0.), (5., -5.), (4., -.5))])
def test_miter_fallback_is_per_corner_not_whole_path(points):
    from shapely.geometry import LineString
    path = SvgPath(points)
    actual = geometry((path,), SvgPaint(fill=False, stroke=True, width=2., miterlimit=4.))
    bevel = LineString(points).buffer(1, cap_style=2, join_style=3)
    direction = 1 if points[2][1] > 0 else -1
    patch = Polygon(((5., -direction), (6., -direction), (6., 0.)))
    assert actual.symmetric_difference(bevel.union(patch)).area < 1e-12


def test_coincident_open_endpoints_have_caps_instead_of_an_invented_closing_join():
    path = SvgPath(((0., 0.), (10., 0.), (10., 10.), (0., 10.), (0., 0.)))
    actual = geometry((path,), SvgPaint(fill=False, stroke=True, width=2.))
    assert actual.area == pytest.approx(79.)
    assert not actual.covers(Polygon(((-1., -1.), (0., -1.), (0., 0.), (-1., 0.))))


def test_unpainted_centerline_retention_is_explicit_and_not_fill():
    paths = (SvgPath(((0., 0.), (1., 2.))),)
    assert render_svg_paths(paths, SvgPaint(fill=False), IDENTITY).geometry_mm == ()
    retained = render_svg_paths(paths, SvgPaint(fill=False), IDENTITY, retain_centerlines=True)
    assert retained.geometry_mm[0].geom_type == 'LineString'
    assert retained.notices


def test_unpainted_subpath_is_retained_alongside_filled_material():
    paths = (square(), SvgPath(((20., 0.), (30., 0.))))
    rendered = render_svg_paths(paths, SvgPaint(), IDENTITY, retain_centerlines=True)
    assert {item.geom_type for item in rendered.geometry_mm} == {'Polygon', 'LineString'}
    assert rendered.notices


def test_fill_stroke_union_and_transformed_path_facts():
    rendered = render_svg_paths((square(),), SvgPaint(stroke=True, width=2.),
                                (1., 0., 0., 1., 3., 4.))
    assert union_all(rendered.geometry_mm).area == 144.
    assert rendered.paths_mm[0].points[0] == (3., 4.)


@pytest.mark.parametrize('tolerance', [0, -1, True, float('inf'), 10 ** 1000])
def test_invalid_tolerance_rejected(tolerance):
    with pytest.raises(ValueError):
        primitive_paths('circle', attrs(r=1), tolerance)


def test_point_budget_prevents_large_round_stroke_before_buffer(monkeypatch):
    import mikrocam.core.svg_paint as module
    monkeypatch.setattr(module, 'MAX_ELEMENT_POINTS', 20)
    with pytest.raises(ValueError, match='point|budget'):
        geometry((SvgPath(((0., 0.), (10., 0.))),),
                 SvgPaint(fill=False, stroke=True, width=100., linecap='round'))
