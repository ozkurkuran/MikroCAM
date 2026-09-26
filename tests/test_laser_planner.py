"""Laser orchestration applies shared placement once and keeps the recipe/source."""
from dataclasses import replace
import subprocess
import sys

import pytest
from shapely.geometry import box

from mikrocam.core.laser_job import LaserJob, LaserPass, LaserRecipe, PlanarRegion
from mikrocam.core.laser_paths import CopperFeatures, PlanOptions, PlanningCancelled
from mikrocam.core.placement import Placement
from mikrocam.laser.planner import plan_laser


def job():
    return LaserJob('board', PlanarRegion.from_geometry(box(0, 0, 4, 4)),
                    LaserRecipe('explicit', (LaserPass('one', 30, 100, 20, 80),)))


def test_one_placement_after_contour_and_hatch_with_source_unchanged():
    original = job()
    placement = Placement(origin=(1, 2), translation=(100, 200), rotation_deg=37, mirror_x=True)
    options = PlanOptions(hatch=True, cross_hatch=True, spacing_mm=0.5)
    source_plan = plan_laser(original, options)
    placed = plan_laser(replace(original, placement=placement), options)
    assert len(placed.paths) == len(source_plan.paths)
    for source_path, final_path in zip(source_plan.paths, placed.paths):
        assert final_path.points == placement.apply_points(source_path.points)
        assert final_path.scan_index == source_path.scan_index
    assert placed.job.region == original.region and placed.job.recipe is original.recipe


def test_unavailable_inner_and_mismatched_feature_snapshot_fail():
    with pytest.raises(ValueError, match='[Nn]o paths|[Ee]mpty'):
        plan_laser(job(), PlanOptions(contour_mode='inner'))
    wrong = CopperFeatures(PlanarRegion.from_geometry(box(0, 0, 2, 2)))
    with pytest.raises(ValueError, match='source|copper'):
        plan_laser(job(), PlanOptions(), wrong)
    with pytest.raises(PlanningCancelled):
        plan_laser(job(), PlanOptions(), cancelled=lambda: True)


def test_fresh_process_has_no_qt_host_or_device_imports():
    code = '''
import sys
from shapely.geometry import box
from mikrocam.core.laser_job import LaserJob, LaserRecipe, LaserPass, PlanarRegion
from mikrocam.core.laser_paths import PlanOptions
from mikrocam.laser.planner import plan_laser
j=LaserJob('x',PlanarRegion.from_geometry(box(0,0,1,1)),LaserRecipe('r',(LaserPass('p',20,10,20,80),)))
assert plan_laser(j,PlanOptions()).paths
assert not any(m.split('.')[0] in {'PyQt6','serial','appMain','vispy'} for m in sys.modules)
'''
    result = subprocess.run([sys.executable, '-I', '-c', 'import sys;sys.path.insert(0,".");'+code],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
