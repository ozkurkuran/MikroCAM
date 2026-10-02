"""Optional copper sources become self-contained SVG snapshots with an explicit ROI."""
from types import SimpleNamespace
import numpy as np
import pytest
from shapely.geometry import box
from mikrocam.bridge.visual_geometry import snapshot_geometry, snapshot_gerber
from mikrocam.bridge.visual_workflow import prepare_visual_job
from mikrocam.core.visual import PreparationSettings
from mikrocam.core.interlace_job import InterlaceSettings
from mikrocam.core.placement import Placement


def test_roi_and_copper_hole_are_preserved():
    copper=box(2,2,8,8).difference(box(4,4,6,6))
    source=snapshot_geometry(copper,'MM',(0,0,10,10),'top copper')
    assert source.info.kind=='geometry_snapshot' and source.info.suggested_size_mm==(10,10)
    assert source.data.startswith(b'<svg') and b'<path' in source.data
    job=prepare_visual_job(source,PreparationSettings(10,10),InterlaceSettings(),Placement(),None,1)
    assert job.mask.burn[60,60] and not job.mask.burn[100,100] and not job.mask.burn[0,0]
    inverted=prepare_visual_job(source,PreparationSettings(10,10,invert=True),InterlaceSettings(),Placement(),None,2)
    assert inverted.mask.burn[0,0] and inverted.mask.burn[100,100] and not inverted.mask.burn[60,60]


def test_snapshot_uses_declared_inches_and_detaches():
    copper=box(.2,.2,.8,.8)
    owner=SimpleNamespace(kind='gerber',units='IN',solid_geometry=copper)
    source=snapshot_gerber(owner,(0,0,25.4,25.4),'copper')
    assert owner.solid_geometry is copper and source.info.suggested_size_mm==(25.4,25.4)
    job=prepare_visual_job(source,PreparationSettings(25.4,25.4),InterlaceSettings(),Placement(),None,1)
    assert job.mask.burn[254,254] and not job.mask.burn[0,0]


@pytest.mark.parametrize('roi',[(0,0,0,1),(0,0,1,0),(0,0,float('nan'),1),None])
def test_roi_is_required_and_finite(roi):
    with pytest.raises(ValueError): snapshot_geometry(box(0,0,1,1),'MM',roi,'source')
