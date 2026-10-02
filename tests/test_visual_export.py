"""PNG helpers preserve full canvas, DPI, ordering and atomic cancellation."""
from dataclasses import replace
from io import BytesIO
import json
import zipfile
import numpy as np
import pytest
from PIL import Image
from test_visual_recipe import job
from mikrocam.bridge.visual_export import export_png_package
from mikrocam.bridge.visual_png import decode_mask_png
from mikrocam.laser.visual_plan import build_plan
from mikrocam.core.laser_paths import PlanningCancelled


def test_png_package_full_grid_and_dpi(tmp_path):
    original=job(); plan=build_plan(original.mask,original.interlace,original.revision)
    target=tmp_path/'groups.zip'; export_png_package(original,plan,target)
    total=np.zeros(original.mask.burn.shape,dtype=np.uint16)
    with zipfile.ZipFile(target) as archive:
        files=[n for n in archive.namelist() if n.endswith('.png')]
        assert files==['group-00.png','group-01.png','group-02.png']
        for name in files:
            data=archive.read(name)
            total+=decode_mask_png(data,original.mask.grid).burn
            image=Image.open(BytesIO(data))
            assert image.size==(13,10) and image.mode=='1'
            assert image.info['dpi']==pytest.approx((508,508),abs=.001)
        manifest=json.loads(archive.read('manifest.json'))
        assert manifest['native_lightburn_settings_applied'] is False
        assert [p['group_index'] for p in manifest['passes']]==[0,2,1,1,0,2,2,1,0]
        assert manifest['canvas_mm']==pytest.approx([.65,.5])
    assert np.array_equal(total,original.mask.burn)


def test_stale_or_cancelled_export_preserves_destination(tmp_path):
    original=job(); plan=build_plan(original.mask,original.interlace,original.revision)
    target=tmp_path/'groups.zip'; target.write_bytes(b'old')
    with pytest.raises(ValueError,match='PLAN_STALE'):
        export_png_package(replace(original,revision=6),plan,target)
    with pytest.raises(PlanningCancelled): export_png_package(original,plan,target,cancelled=lambda:True)
    assert target.read_bytes()==b'old' and list(tmp_path.iterdir())==[target]
