"""Analytic circular travel must include transformed extrema, not just the chord."""
import math

import pytest

from mikrocam.core.gcode_lexer import GcodeError
from mikrocam.core.gcode_motion import make_arc, motion_bounds, motion_length
from mikrocam.core.placement import Placement


def test_rotated_quarter_helix_has_interior_machine_y_extreme():
    start, end = (1.,0.,0.), (0.,1.,2.)
    arc = make_arc(start, end, False, ij=(-1.,0.), line=4)
    low, high = motion_bounds(start, end, Placement(rotation_deg=45), 3., arc)
    assert low == pytest.approx((-2**-.5, 2**-.5, 3.), abs=1e-12)
    assert high == pytest.approx((2**-.5, 1., 5.), abs=1e-12)
    assert motion_length(start, end, arc) == pytest.approx(math.hypot(math.pi/2, 2))


def test_mirror_changes_sweep_and_preserves_correct_interior_extreme():
    start, end = (1.,0.,0.), (0.,1.,0.)
    arc = make_arc(start, end, False, ij=(-1.,0.))
    low, high = motion_bounds(start, end, Placement(rotation_deg=45, mirror_x=True), 0., arc)
    assert low == pytest.approx((-1., -2**-.5, 0.), abs=1e-12)
    assert high == pytest.approx((-2**-.5, 2**-.5, 0.), abs=1e-12)


@pytest.mark.parametrize('clockwise', [True, False])
@pytest.mark.parametrize('radius,sweep', [(2.,math.pi/3), (-2.,5*math.pi/3)])
def test_signed_radius_selects_major_or_minor_sweep(clockwise, radius, sweep):
    arc = make_arc((0.,0.,0.), (2.,0.,0.), clockwise, radius=radius)
    assert abs(arc.sweep) == pytest.approx(sweep)
    assert (arc.sweep < 0) is clockwise


@pytest.mark.parametrize('clockwise', [True, False])
def test_full_circle_helix_bounds_and_length(clockwise):
    start, end = (1.,0.,-2.), (1.,0.,3.)
    arc = make_arc(start, end, clockwise, ij=(-1.,0.))
    low, high = motion_bounds(start, end, Placement(translation=(10.,20.), rotation_deg=17), 4., arc)
    assert low == pytest.approx((9.,19.,2.))
    assert high == pytest.approx((11.,21.,7.))
    assert motion_length(start,end,arc) == pytest.approx(math.hypot(2*math.pi,5))


@pytest.mark.parametrize('end,kwargs', [((3.,0.,0.), {'radius':1.}),
    ((0.,0.,0.), {'radius':1.}), ((1.,0.,0.), {'radius':0.}),
    ((1.,0.,0.), {'ij':(0.,0.)}), ((0.,2.,0.), {'ij':(1.,0.)}),
    ((1.,0.,0.), {'ij':(1.,0.), 'radius':1.}), ((1.,0.,0.), {})])
def test_impossible_or_ambiguous_arc_is_blocked(end, kwargs):
    with pytest.raises(GcodeError) as caught:
        make_arc((0.,0.,0.), end, False, line=7, **kwargs)
    assert caught.value.line == 7


def test_permitted_endpoint_rounding_does_not_understate_bounds():
    start, end = (1.,0.,0.), (0.,1.004,0.)
    arc = make_arc(start,end,False,ij=(-1.,0.))
    low, high = motion_bounds(start,end,Placement(),0.,arc)
    assert high[1] >= 1.004
    with pytest.raises(GcodeError):
        make_arc(start,(0.,1.006,0.),False,ij=(-1.,0.))


def test_analytic_extrema_contain_dense_samples_under_arbitrary_placement():
    start,end=(2.,0.,1.),(0.,2.,5.)
    for clockwise in (False,True):
        arc=make_arc(start,end,clockwise,ij=(-2.,0.))
        for mirror in (False,True):
            placement=Placement(origin=(1.,2.),translation=(-7.,9.),rotation_deg=37.,mirror_x=mirror)
            low,high=motion_bounds(start,end,placement,-3.,arc)
            for i in range(1001):
                angle=arc.start_angle+arc.sweep*i/1000
                xy=placement.apply_point((2*math.cos(angle),2*math.sin(angle)))
                point=(*xy, -2.+4*i/1000)
                assert all(low[j]-1e-12<=point[j]<=high[j]+1e-12 for j in range(3))


def test_linear_bounds_include_initial_position_and_vertical_travel():
    low,high=motion_bounds((1.,2.,3.),(-1.,4.,-5.),Placement(translation=(10.,20.)),2.)
    assert low==(9.,22.,-3.) and high==(11.,24.,5.)
    assert motion_length((1.,2.,3.),(-1.,4.,-5.))==pytest.approx(math.sqrt(72))
