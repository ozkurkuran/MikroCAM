"""Versioned transfer integrity and bounded archive rejection before import."""
import io
import json
from hashlib import sha256
from dataclasses import replace
from pathlib import Path
import zipfile
import pytest
from mikrocam.core.kicad_transfer import TransferFile, TransferManifest, TransferPackage, manifest_from_dict, manifest_to_dict
from mikrocam.kicad.package import read_package, write_package

GERBER=b'%FSLAX46Y46*%%MOMM*%%TF.FileFunction,Copper,L1,Top*%%ADD10C,1*%D10*X1000000Y1000000D03*M02*'
DRILL=b'M48\nMETRIC,TZ\n; #@! TF.FileFunction,Plated,1,2,PTH\nT1C1.0\n%\nT1\nX1.0Y1.0\nM30\n'

def sample():
    contents=(GERBER,DRILL)
    rows=tuple(TransferFile(n,k,r,sha256(b).hexdigest(),len(b)) for n,k,r,b in zip(('board-F_Cu.gbr','board-PTH.drl'),('gerber','excellon'),('F.Cu','PTH'),contents))
    drc=b'{"violations":[],"unconnected_items":[],"schematic_parity":[]}'
    m=TransferManifest('board.kicad_pcb','a'*64,'10.0.6',rows,(),sha256(drc).hexdigest(),0,0,0)
    return TransferPackage(m,drc,contents)

def rewrite(path, mutate):
    with zipfile.ZipFile(path) as z: pairs=[(n,z.read(n)) for n in z.namelist()]
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',message='Duplicate name:')
        with zipfile.ZipFile(path,'w') as z:
            for n,b in mutate(pairs):z.writestr(n,b)


def test_package_roundtrip_bytes_roles_and_schema(tmp_path):
    value=sample();path=tmp_path/'ışıklı kart.mcam-transfer'
    write_package(path,value)
    assert read_package(path)==value
    assert manifest_from_dict(manifest_to_dict(value.manifest))==value.manifest

@pytest.mark.parametrize('change',[
    lambda p:p+[('../outside',b'bad')],
    lambda p:p+[('files/extra.gbr',b'bad')],
    lambda p:p+[p[-1]],
    lambda p:[(n,b+b'tamper' if n.endswith('.gbr') else b) for n,b in p],
    lambda p:[(n,b'{}' if n=='drc.json' else b) for n,b in p],
    lambda p:[(n,b.replace(b'"schema":1',b'"schema":2') if n=='manifest.json' else b) for n,b in p],
    lambda p:[(n,b.replace(b'"schema":1',b'"schema":1,"schema":1') if n=='manifest.json' else b) for n,b in p],
])
def test_invalid_archive_rejected(tmp_path,change):
    path=tmp_path/'bad.mcam-transfer';write_package(path,sample());rewrite(path,change)
    with pytest.raises(ValueError):read_package(path)

@pytest.mark.parametrize('name',['../bad','nested/name','bad\\name','C:bad',' bad','bad\x00',''])
def test_member_name_refuses_nonlocal_paths(name):
    with pytest.raises(ValueError):replace(sample().manifest.files[0],name=name)

@pytest.mark.parametrize('field,value',[('schema',True),('schema',2),('units','IN'),('origin','plot'),('drc_errors',-1),('board_sha256','bad'),('kicad_version','11.0.0')])
def test_strict_schema(field,value):
    d=manifest_to_dict(sample().manifest);d[field]=value
    with pytest.raises(ValueError):manifest_from_dict(d)

def test_atomic_failure_preserves_destination(tmp_path,monkeypatch):
    import mikrocam.kicad.package as mod
    path=tmp_path/'old.mcam-transfer';path.write_bytes(b'old')
    monkeypatch.setattr(mod.os,'replace',lambda *a:(_ for _ in ()).throw(OSError('full')))
    with pytest.raises(OSError):write_package(path,sample())
    assert path.read_bytes()==b'old'
    assert list(tmp_path.iterdir())==[path]

def test_declared_size_and_drc_count_cannot_lie():
    p=sample()
    with pytest.raises(ValueError):replace(p,contents=(GERBER+b'bad',DRILL))
    with pytest.raises(ValueError):replace(p,manifest=replace(p.manifest,drc_errors=1))

def test_symlink_archive_member_rejected(tmp_path):
    path=tmp_path/'link.mcam-transfer';write_package(path,sample())
    with zipfile.ZipFile(path,'a') as z:
        info=zipfile.ZipInfo('files/link');info.create_system=3;info.external_attr=(0o120777<<16);z.writestr(info,b'outside')
    with pytest.raises(ValueError):read_package(path)
