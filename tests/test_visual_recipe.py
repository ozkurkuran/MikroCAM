"""Portable visual jobs preserve pixels, sources and all scheduling decisions."""
from dataclasses import replace
from io import BytesIO
import json
from types import SimpleNamespace
import numpy as np
import pytest
from PIL import Image
from mikrocam.bridge.visual_bitmap import inspect_bitmap
from mikrocam.bridge.visual_workflow import prepare_visual_job
from mikrocam.bridge.visual_recipe import job_to_payload, job_from_payload, save_visual_recipe, load_visual_recipe
from mikrocam.bridge.visual_project import attach_visual_job, read_visual_job
from mikrocam.core.visual import PreparationSettings, SourceAsset
from mikrocam.core.interlace_job import InterlaceSettings
from mikrocam.core.placement import Placement
from mikrocam.core.laser_paths import PlanningCancelled


def job():
    image=Image.new('1',(13,10),1); image.putpixel((0,0),0)
    stream=BytesIO(); image.save(stream,format='PNG'); data=stream.getvalue()
    return prepare_visual_job(SourceAsset('original.png',data,inspect_bitmap(data)),
        PreparationSettings(.65,.5),InterlaceSettings(count=3,order_mode='mixed',round_count=3,
        vary_order_each_round=True,delay_ms=13),Placement(translation=(4,8)),None,revision=5)


def test_roundtrip_without_source_file(tmp_path):
    original=job(); target=tmp_path/'work.json'
    save_visual_recipe(original,target)
    loaded=load_visual_recipe(target)
    assert loaded.source==original.source
    assert loaded.preparation==original.preparation and loaded.interlace==original.interlace
    assert loaded.placement==original.placement and loaded.revision==5
    assert loaded.mask.sha256==original.mask.sha256 and np.array_equal(loaded.mask.burn,original.mask.burn)
    assert loaded.renderer_name==original.renderer_name


@pytest.mark.parametrize('corrupt',['source_hash','mask_hash','count','grid','orders','future','png','extra'])
def test_corrupt_payload_rejected(corrupt):
    payload=job_to_payload(job())
    if corrupt=='source_hash': payload['source']['sha256']='0'*64
    elif corrupt=='mask_hash': payload['mask']['sha256']='0'*64
    elif corrupt=='count': payload['mask']['black_pixel_count']=99
    elif corrupt=='grid': payload['grid']['width_px']=14
    elif corrupt=='orders': payload['interlace']['effective_orders'][0]=[0,0,2]
    elif corrupt=='future': payload['schema_version']=99
    elif corrupt=='png': payload['mask']['data_base64']='broken!'
    else: payload['unexpected']=1
    with pytest.raises(ValueError): job_from_payload(payload)


def test_migration_missing_interlace_is_disabled():
    payload=job_to_payload(job()); del payload['interlace']
    loaded=job_from_payload(payload)
    assert loaded.interlace==InterlaceSettings(count=1)


def test_project_payload_roundtrip_and_snapshot_independence():
    owner=SimpleNamespace(obj_options={})
    original=job(); attach_visual_job(owner,original)
    stored=json.loads(json.dumps(owner.obj_options))
    restored=read_visual_job(SimpleNamespace(obj_options=stored))
    assert restored.mask.sha256==original.mask.sha256
    assert restored.source.data==original.source.data and restored.interlace==original.interlace
    assert read_visual_job(SimpleNamespace(obj_options={})) is None


def test_cancelled_save_and_prepare_leave_previous_file(tmp_path):
    target=tmp_path/'work.json'; target.write_bytes(b'previous')
    with pytest.raises(PlanningCancelled): save_visual_recipe(job(),target,cancelled=lambda:True)
    assert target.read_bytes()==b'previous' and list(tmp_path.iterdir())==[target]
    original=job()
    with pytest.raises(PlanningCancelled):
        prepare_visual_job(original.source,original.preparation,original.interlace,
                           original.placement,None,1,cancelled=lambda:True)


def test_failed_replace_keeps_old_file(tmp_path,monkeypatch):
    import mikrocam.laser.visual_files as files
    target=tmp_path/'work.json'; target.write_bytes(b'old')
    def fail(*args): raise OSError('disk failure')
    monkeypatch.setattr(files.os,'replace',fail)
    with pytest.raises(OSError): save_visual_recipe(job(),target)
    assert target.read_bytes()==b'old' and list(tmp_path.iterdir())==[target]


def test_duplicate_json_key_and_nonfinite_rejected(tmp_path):
    for data in ('{"schema_version":1,"schema_version":1}', '{"value":NaN}'):
        target=tmp_path/'bad.json'; target.write_text(data)
        with pytest.raises(ValueError): load_visual_recipe(target)


def test_cached_grid_rejects_boolean_numeric_values():
    payload=job_to_payload(job())
    # bool is equal to int in Python; cached metadata must nevertheless have real numeric types.
    payload['grid']['requested_dpi']=True
    with pytest.raises(ValueError): job_from_payload(payload)
    source=job()
    from mikrocam.core.visual import PreparationSettings
    from mikrocam.bridge.visual_workflow import prepare_visual_job
    tiny=prepare_visual_job(source.source,PreparationSettings(.05,.05),source.interlace,source.placement,None,1)
    payload=job_to_payload(tiny); payload['grid']['width_px']=True
    with pytest.raises(ValueError): job_from_payload(payload)


def test_portable_schema_is_versioned_and_embedded():
    from pathlib import Path
    schema=json.loads((Path(__file__).parents[1]/'mikrocam/laser/visual_recipe.schema.json').read_text())
    assert schema['properties']['schema_version']=={'const':1}
    assert schema['properties']['kind']=={'const':'visual_interlace'}
    assert schema['additionalProperties'] is False
    assert {'source','mask','preparation','grid','placement','revision'} <= set(schema['required'])
