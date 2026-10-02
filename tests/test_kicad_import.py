"""Complete archive/role integrity before existing manufacturing publication."""
from dataclasses import replace
from pathlib import Path
from hashlib import sha256
import pytest
from test_manufacturing_roundtrip import host
from test_kicad_package import sample,GERBER
from mikrocam.bridge.kicad_transfer import prepare_transfer


def test_prepared_roles_and_bytes(tmp_path):
    p=sample();review=prepare_transfer(p,tmp_path)
    assert [a.role for a in review.assignments]==['F.Cu','PTH']
    assert all(Path(f.path).read_bytes()==f.source_bytes for f in review.files)
    assert review.files[0].inspection.units_hint=='MM'

@pytest.mark.parametrize('field,value',[('role','B.Cu'),('role','PTH')])
def test_misleading_manifest_refused_before_files(tmp_path,field,value):
    p=sample();r=replace(p.manifest.files[0],**{field:value})
    m=replace(p.manifest,files=(r,p.manifest.files[1]))
    with pytest.raises(ValueError):prepare_transfer(replace(p,manifest=m),tmp_path)
    assert not list(tmp_path.iterdir())


def test_changed_extract_refused_at_review(tmp_path,monkeypatch):
    import mikrocam.bridge.kicad_transfer as mod
    original=mod.review_manufacturing_files
    def change(files,assignments):
        Path(files[0].path).write_bytes(b'changed');return original(files,assignments)
    monkeypatch.setattr(mod,'review_manufacturing_files',change)
    with pytest.raises(ValueError):prepare_transfer(sample(),tmp_path)


@pytest.mark.parametrize('kind',['gerber','excellon'])
def test_transfer_provenance_survives_real_object_serializer(kind,tmp_path,host):
    import json
    from camlib import to_dict,dict2obj
    from mikrocam.bridge.kicad_transfer import attach_transfer_metadata,read_transfer_metadata
    app,create_owner,_,_=host
    # Existing host fixture creates real parser/serializer classes.
    obj=create_owner(kind,'transfer evidence')
    if obj is None:
        pytest.fail('Host fixture must publish owner')
    attach_transfer_metadata(obj,sample().manifest)
    stored=json.loads(json.dumps(obj.to_dict(),default=to_dict),object_hook=dict2obj)
    restored=create_owner(kind,'restored evidence')
    restored.from_dict(stored)
    assert read_transfer_metadata(restored)==sample().manifest
