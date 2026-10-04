"""The one CAM-to-machine Placement gains a full affine form without a second transform type."""
import json
import math

import pytest
from shapely.geometry import LineString, Polygon

from mikrocam.core.gcode_motion import make_arc, motion_bounds
from mikrocam.core.laser_job import LaserJob, LaserPass, LaserRecipe, PlanarRegion
from mikrocam.core.laser_json import job_from_json, job_to_json
from mikrocam.core.laser_paths import PlanOptions
from mikrocam.laser.planner import plan_laser
from mikrocam.core.placement import Placement


SHEAR = (1.002, 0.01, -0.004, 0.998, 12.5, -3.25)


def test_affine_matrix_is_used_by_points_geometry_and_inverse():
    placement = Placement(affine=SHEAR)
    a, b, d, e, xoff, yoff = SHEAR
    assert placement.matrix == SHEAR
    assert placement.apply_point((2., 3.)) == pytest.approx((a*2 + b*3 + xoff, d*2 + e*3 + yoff))
    line = placement.apply_geometry(LineString([(0., 0.), (2., 3.)]))
    assert line.coords[-1] == pytest.approx(placement.apply_point((2., 3.)))
    back = placement.inverse()
    assert back.affine is not None
    assert back.apply_point(placement.apply_point((7., -4.))) == pytest.approx((7., -4.), abs=1e-12)


def test_affine_coefficients_are_tuple_of_finite_floats():
    placement = Placement(affine=[1, 0, 0, 1, 2, 3])
    assert placement.affine == (1., 0., 0., 1., 2., 3.)
    assert all(type(value) is float for value in placement.affine)


@pytest.mark.parametrize('affine', [(1., 0., 0., 1., 0.), (1., 0., 0., 1., 0., math.nan),
                                    (1., 2., 2., 4., 0., 0.), (0., 0., 0., 0., 0., 0.),
                                    (True, 0., 0., 1., 0., 0.), 'abcdef', 3])
def test_invalid_or_singular_affine_is_rejected(affine):
    with pytest.raises(ValueError):
        Placement(affine=affine)


@pytest.mark.parametrize('rigid', [dict(origin=(1., 0.)), dict(translation=(0., 1.)),
                                   dict(rotation_deg=1.), dict(mirror_x=True)])
def test_affine_cannot_be_combined_with_rigid_fields(rigid):
    with pytest.raises(ValueError, match='[Aa]ffine'):
        Placement(affine=SHEAR, **rigid)


def test_rigid_placements_and_their_inverse_are_unchanged():
    placement = Placement(origin=(1., 2.), translation=(3., 4.), rotation_deg=30., mirror_x=True)
    assert placement.affine is None
    assert placement.inverse().affine is None
    assert placement.rigid_data() == {'origin': (1., 2.), 'translation': (3., 4.),
                                      'rotation_deg': 30., 'mirror_x': True}


def test_rigid_only_formats_reject_affine_explicitly():
    with pytest.raises(ValueError, match='rigid'):
        Placement(affine=SHEAR).rigid_data()
    region = PlanarRegion.from_geometry(Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]))
    recipe = LaserRecipe('r', (LaserPass('p', 50., 100., 20., 100.),))
    rigid = LaserJob('j', region, recipe, Placement(translation=(1., 2.), rotation_deg=10.))
    assert job_from_json(job_to_json(rigid)) == rigid
    assert set(json.loads(job_to_json(rigid))['placement']) == {'origin', 'translation',
                                                                 'rotation_deg', 'mirror_x'}
    with pytest.raises(ValueError, match='rigid'):
        job_to_json(LaserJob('j', region, recipe, Placement(affine=SHEAR)))


def _sampled_bounds(start, end, arc, placement):
    points = []
    for index in range(20001):
        theta = arc.start_angle + arc.sweep*index/20000
        points.append(placement.apply_point((arc.center[0] + arc.radius*math.cos(theta),
                                             arc.center[1] + arc.radius*math.sin(theta))))
    points += [placement.apply_point(start[:2]), placement.apply_point(end[:2])]
    return (min(p[0] for p in points), min(p[1] for p in points)), (max(p[0] for p in points),
                                                                    max(p[1] for p in points))


@pytest.mark.parametrize('clockwise', [False, True])
@pytest.mark.parametrize('affine', [SHEAR, (1.3, 0.4, -0.2, 0.7, 5., 6.), (0.9, 0.2, 0.3, -1.1, 0., 0.)])
def test_affine_arc_bounds_include_ellipse_extrema(clockwise, affine):
    start, end = (1., 0., 0.), (0., 1., 2.)
    arc = make_arc(start, end, clockwise, ij=(-1., 0.))
    placement = Placement(affine=affine)
    low, high = motion_bounds(start, end, placement, 3., arc)
    sampled_low, sampled_high = _sampled_bounds(start, end, arc, placement)
    assert low[:2] == pytest.approx(sampled_low, abs=1e-6)
    assert high[:2] == pytest.approx(sampled_high, abs=1e-6)
    assert (low[2], high[2]) == (3., 5.)


def test_affine_equal_to_rigid_gives_same_arc_bounds():
    start, end = (1., 0., 0.), (-1., 0., 0.)
    arc = make_arc(start, end, False, ij=(-1., 0.))
    rigid = Placement(translation=(4., 5.), rotation_deg=33.)
    affine = Placement(affine=rigid.matrix)
    expected = motion_bounds(start, end, rigid, 0., arc)
    actual = motion_bounds(start, end, affine, 0., arc)
    assert actual[0] + actual[1] == pytest.approx(expected[0] + expected[1], abs=1e-12)


def test_laser_plan_applies_the_same_affine_placement():
    region = PlanarRegion.from_geometry(Polygon([(0, 0), (4, 0), (4, 3), (0, 3)]))
    recipe = LaserRecipe('r', (LaserPass('p', 50., 100., 20., 100.),))
    placement = Placement(affine=SHEAR)
    plan = plan_laser(LaserJob('j', region, recipe, placement), PlanOptions())
    source = plan_laser(LaserJob('j', region, recipe, Placement()), PlanOptions())
    assert len(plan.paths) == len(source.paths)
    for placed, original in zip(plan.paths, source.paths):
        assert placed.points == placement.apply_points(original.points)
