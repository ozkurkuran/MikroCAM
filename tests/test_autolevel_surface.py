from dataclasses import replace
import pytest
from mikrocam.core.probe_map import ProbeGrid, ProbeMap
from mikrocam.core.autolevel_surface import AutoLevelSettings, surface_height, cell_crossings


def height_map(function=lambda x, y: x + 2*y, offset=(0., 0., 0.)):
    grid = ProbeGrid((0., 1., 2.), (0., 1., 2.))
    return ProbeMap(grid, tuple(function(x,y) for x,y in grid.points), offset, 'complete', 'simulated')


@pytest.mark.parametrize('function', [lambda x,y: 3., lambda x,y: .01*x+.02*y,
                                      lambda x,y: x*y, lambda x,y: x*y + x - y])
@pytest.mark.parametrize('point', [(0.,0.), (2.,2.), (1.,.5), (.3,1.7), (2.,.25)])
def test_bilinear_analytic_surface_and_closed_edges(function, point):
    value = height_map(function)
    assert surface_height(value, *point) == pytest.approx(function(*point), abs=1e-12)


@pytest.mark.parametrize('point', [(-1e-8,0.), (2.00000001,1.), (1.,-.01), (1.,3.),
                                  (float('nan'),0.), (True,1.)])
def test_no_extrapolation_or_invalid_query(point):
    with pytest.raises(ValueError):
        surface_height(height_map(), *point)


def test_complete_outcome_required_even_when_all_points_exist():
    value = replace(height_map(), outcome='aborted')
    with pytest.raises(ValueError):
        surface_height(value, .5, .5)
    with pytest.raises(ValueError):
        AutoLevelSettings(value, 0., 1., .01, .01)


@pytest.mark.parametrize('field,value', [('reference_z_mm',True), ('reference_z_mm',float('inf')),
    ('max_segment_mm',0), ('max_segment_mm',11), ('chord_error_mm',0),
    ('surface_error_mm',.00001), ('surface_error_mm',True)])
def test_settings_require_explicit_bounded_numbers(field,value):
    original = AutoLevelSettings(height_map(), 0., 1., .01, .01)
    with pytest.raises(ValueError):
        replace(original, **{field:value})


def test_cell_crossings_corner_dedup_and_reverse():
    grid = height_map().grid
    assert cell_crossings(grid, (0.,0.), (2.,2.)) == (0., .5, 1.)
    assert cell_crossings(grid, (2.,2.), (0.,0.)) == (0., .5, 1.)
    assert cell_crossings(grid, (0.,.5), (0.,1.5)) == (0., .5, 1.)



def test_nonuniform_axes_and_nonconstant_cell_slopes():
    grid=ProbeGrid((0.,.25,2.), (0.,.5,2.))
    value=ProbeMap(grid,tuple(x*y + x - 2*y for x,y in grid.points),(0.,0.,0.),'complete','measured')
    for x,y in ((.125,.25),(.8,1.3),(2.,2.)):
        assert surface_height(value,x,y)==pytest.approx(x*y+x-2*y,abs=1e-12)
