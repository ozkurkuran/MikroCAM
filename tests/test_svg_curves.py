"""Analytic and geometric error checks for bounded SVG curve flattening."""
import math

import pytest
from shapely import LineString, Point

from mikrocam.core.svg_curves import flatten_arc, flatten_cubic, flatten_quadratic


@pytest.mark.parametrize('controls', [((0., 0.), (0., 10.), (10., 10.), (10., 0.)),
                                     ((0., 0.), (10., 10.), (-10., -10.), (1., 0.)),
                                     ((0., 0.), (20., 0.), (-20., 0.), (1., 0.))])
def test_cubic_preserves_endpoints_and_bounds_analytic_curve_distance(controls):
    points = flatten_cubic(*controls, .005)
    assert points[0] == controls[0] and points[-1] == controls[-1]
    approximation = LineString(points)
    for index in range(1001):
        t = index / 1000
        weights = ((1-t)**3, 3*t*(1-t)**2, 3*t*t*(1-t), t**3)
        point = tuple(sum(weight * control[axis] for weight, control in zip(weights, controls))
                      for axis in range(2))
        assert approximation.distance(Point(point)) <= .005 + 1e-12


def test_quadratic_samples_bow_and_straight_bezier_needs_only_endpoints():
    points = flatten_quadratic((0., 0.), (1., 2.), (2., 0.), .001)
    assert (1., 1.) in points
    assert len(points) > 10
    assert flatten_cubic((0., 0.), (1., 1.), (2., 2.), (3., 3.), .01) == ((0., 0.), (3., 3.))


@pytest.mark.parametrize('sweep', [90., -90., 180., -270., 360.])
def test_rotated_ellipse_error_and_exact_endpoints(sweep):
    center, radii, rotation, first = (4., 7.), (10., 3.), 30., 20.
    def point(degrees):
        angle, turn = math.radians(degrees), math.radians(rotation)
        x, y = radii[0] * math.cos(angle), radii[1] * math.sin(angle)
        return (center[0] + x*math.cos(turn) - y*math.sin(turn),
                center[1] + x*math.sin(turn) + y*math.cos(turn))
    start, end = point(first), point(first+sweep)
    points = flatten_arc(center, radii, rotation, first, sweep, start, end, .002)
    assert points[0] == start and points[-1] == end
    approximation = LineString(points)
    for index in range(1001):
        assert approximation.distance(Point(point(first+sweep*index/1000))) <= .002 + 1e-12


def test_arc_full_circle_has_exact_closure_and_no_duplicate_endpoint_drift():
    points = flatten_arc((0., 0.), (2., 2.), 0., 0., 360., (2., 0.), (2., 0.), .005)
    assert len(points) > 30 and points[0] == points[-1]
    assert LineString(points).is_ring


@pytest.mark.parametrize('tolerance', [0., -1., True, math.nan, math.inf, '1'])
def test_invalid_tolerance_rejected(tolerance):
    with pytest.raises(ValueError):
        flatten_cubic((0., 0.), (0., 1.), (1., 1.), (1., 0.), tolerance)


@pytest.mark.parametrize('point', [(math.nan, 0.), (math.inf, 0.), (True, 0.),
                                  (1e10, 0.), (1.,), [0., 0.]])
def test_invalid_control_point_rejected(point):
    with pytest.raises(ValueError):
        flatten_quadratic((0., 0.), point, (1., 0.), .01)


@pytest.mark.parametrize('radii,sweep', [((-1., 2.), 90.), ((0., 2.), 90.),
                                       ((1., 2.), 361.), ((1., 2.), math.inf)])
def test_invalid_ellipse_parameters_rejected(radii, sweep):
    with pytest.raises(ValueError):
        flatten_arc((0., 0.), radii, 0., 0., sweep, (1., 0.), (0., 1.), .01)


def test_point_budget_and_depth_limits_fail_explicitly(monkeypatch):
    import mikrocam.core.svg_curves as curves
    monkeypatch.setattr(curves, 'MAX_ELEMENT_POINTS', 10)
    with pytest.raises(ValueError, match='budget|limit'):
        flatten_cubic((0., 0.), (0., 100.), (100., 100.), (100., 0.), .0001)
    with pytest.raises(ValueError, match='budget|limit'):
        flatten_arc((0., 0.), (100., 100.), 0., 0., 360., (100., 0.), (100., 0.), .0001)
    with pytest.raises(ValueError, match='budget|limit'):
        flatten_quadratic((0., 0.), (0., 100.), (100., 0.), 1e-300)


def test_huge_tolerance_keeps_a_non_degenerate_circle():
    points = flatten_arc((0., 0.), (1., 1.), 0., 0., 360., (1., 0.), (1., 0.), 10.)
    assert len(points) >= 5 and LineString(points).is_ring


def test_arc_endpoint_snapping_shares_total_error_budget():
    points = flatten_arc((0., 0.), (100., 100.), 0., 0., 90., (100., 0.), (0., 99.991), .01)
    approximation = LineString(points)
    for index in range(10001):
        angle = math.pi / 2 * index / 10000
        assert approximation.distance(Point(100 * math.cos(angle), 100 * math.sin(angle))) <= .01


def test_arc_inconsistent_endpoint_is_explicit_error():
    with pytest.raises(ValueError, match='endpoint'):
        flatten_arc((0., 0.), (100., 100.), 0., 0., 90., (100., 0.), (0., 99.98), .01)
