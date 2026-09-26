"""Plain laser planning data validation, without desktop or device access."""
from dataclasses import FrozenInstanceError
import math

import pytest
from shapely.geometry import box

from mikrocam.core.laser_job import LaserJob, LaserPass, LaserRecipe, PlanarRegion
from mikrocam.core.laser_paths import CopperFeatures, LaserPath, LaserPlan, PlanOptions


def example_job():
    return LaserJob('test', PlanarRegion.from_geometry(box(0, 0, 4, 4)),
                    LaserRecipe('explicit', (LaserPass('one', 30, 100, 20, 80),)))


def test_path_copies_points_and_is_immutable():
    points = [[0, 0], [1, 2]]
    path = LaserPath(points, 'contour')
    points[0][0] = 99
    assert path.points == ((0, 0), (1, 2))
    with pytest.raises(FrozenInstanceError):
        path.role = 'hatch'


@pytest.mark.parametrize('kwargs', [
    {'points': []}, {'points': None}, {'points': [(0, 0), (0, 0)]},
    {'points': [(0, 0, 1), (1, 2, 3)]}, {'points': [(0, 0), (math.inf, 1)]},
    {'role': 'rapid'}, {'role': 'hatch'}, {'scan_index': 1}, {'hatch_family': 0},
    {'role': 'hatch', 'scan_index': True, 'hatch_family': 0},
    {'role': 'hatch', 'scan_index': 1, 'hatch_family': 2},
])
def test_invalid_paths(kwargs):
    values = {'points': ((0, 0), (1, 1)), 'role': 'contour'}
    values.update(kwargs)
    with pytest.raises(ValueError):
        LaserPath(**values)


@pytest.mark.parametrize('kwargs', [
    {'contour_mode': 'bogus'}, {'contour_mode': []}, {'region_mode': 'automatic'},
    {'hatch': 1}, {'cross_hatch': 1}, {'cross_hatch': True},
    {'contour_mode': 'none'}, {'spacing_mm': 0}, {'spacing_mm': -1},
    {'spacing_mm': True}, {'spacing_mm': math.nan}, {'angle_deg': math.inf},
])
def test_invalid_options(kwargs):
    with pytest.raises(ValueError):
        PlanOptions(**kwargs)


def test_valid_hatch_options_and_scan_indices():
    options = PlanOptions('none', True, 0.02, -450, True, 'clearance')
    assert options.spacing_mm == 0.02 and options.angle_deg == -450
    assert LaserPath(((0, 0), (1, 2)), 'hatch', -12, 1).scan_index == -12


def test_features_and_plan_are_typed_nonempty_data():
    job = example_job()
    features = CopperFeatures(job.region)
    assert features.copper is job.region and features.board is None
    with pytest.raises(ValueError):
        CopperFeatures(job.region, pads='guess')
    with pytest.raises(ValueError):
        CopperFeatures(None)
    with pytest.raises(ValueError):
        LaserPlan(job, PlanOptions(), ())
    with pytest.raises(ValueError):
        LaserPlan(job, PlanOptions(), ('line',))
    path = LaserPath(((0, 0), (1, 1)), 'contour')
    assert LaserPlan(job, PlanOptions(), (path,)).paths == (path,)
