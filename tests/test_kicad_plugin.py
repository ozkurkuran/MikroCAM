"""Standalone IPC bridge snapshots live board and only launches complete exports."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

def module():
    path=ROOT/'integrations/kicad/bridge.py'
    spec=importlib.util.spec_from_file_location('mikrocam_kicad_bridge',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

@pytest.fixture
def setup(tmp_path):
    repo=tmp_path/'repo space';repo.mkdir();(repo/'flatcam.py').write_text('')
    python=tmp_path/'python.exe';python.write_bytes(b'fake')
    output=tmp_path/'transfers'
    config={'schema':1,'repo_root':str(repo),'python_executable':str(python),'transfer_directory':str(output)}
    saved=[];launched=[];calls=[]
    def save_as(path,**kwargs):
        saved.append((path,kwargs));Path(path).write_bytes(b'live unsaved snapshot')
    board=SimpleNamespace(name='live board.kicad_pcb',save_as=save_as)
    client=SimpleNamespace(get_board=lambda:board,get_version=lambda:SimpleNamespace(major=10,minor=0),get_kicad_binary_path=lambda name:'C:/KiCad10/'+name)
    def run(args,**kwargs):
        calls.append((args,kwargs));out=Path(args[args.index('--output')+1]);out.write_bytes(b'complete package')
        return SimpleNamespace(returncode=0,stdout='',stderr='')
    return config,client,board,saved,calls,launched,run


def test_ipc_copy_export_and_unique_cam_launch(setup,monkeypatch):
    m=module();config,client,board,saved,calls,launched,run=setup
    monkeypatch.setattr(m.subprocess,'run',run);monkeypatch.setattr(m.subprocess,'Popen',lambda args,**kw:launched.append((args,kw)))
    first=m.transfer(client,config);second=m.transfer(client,config)
    assert first!=second and first.is_file() and second.is_file()
    assert len(saved)==2 and all(v[1]=={'overwrite':False,'include_project':True} for v in saved)
    assert all(not Path(p).exists() for p,kw in saved)
    assert all(c[1]['shell'] is False and c[1]['timeout']==330 for c in calls)
    assert all('live board.kicad_pcb' in Path(c[0][3]).name for c in calls)
    assert launched[0][0]==[config['python_executable'],str(Path(config['repo_root'])/'flatcam.py'),str(first)]
    assert launched[0][1]['shell'] is False
    assert board.name=='live board.kicad_pcb'

@pytest.mark.parametrize('mode',['snapshot','exit','timeout','missing'])
def test_failure_never_launches(setup,monkeypatch,mode):
    m=module();config,client,board,saved,calls,launched,run=setup
    if mode=='snapshot':board.save_as=lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('API copy failed'))
    def failing(args,**kwargs):
        if mode=='timeout':raise subprocess.TimeoutExpired(args,330)
        if mode=='missing':return SimpleNamespace(returncode=0,stdout='',stderr='')
        return SimpleNamespace(returncode=2,stdout='',stderr='DRC/export failed')
    monkeypatch.setattr(m.subprocess,'run',failing);monkeypatch.setattr(m.subprocess,'Popen',lambda *a,**kw:launched.append(a))
    with pytest.raises((ValueError,RuntimeError)):m.transfer(client,config)
    assert not launched

@pytest.mark.parametrize('name',['','untitled','../bad.kicad_pcb'])
def test_unnamed_or_nonlocal_board_rejected(setup,monkeypatch,name):
    m=module();config,client,board,saved,calls,launched,run=setup;board.name=name
    monkeypatch.setattr(m.subprocess,'run',run)
    with pytest.raises(ValueError):m.transfer(client,config)
    assert not saved and not calls


def test_real_schema_manifest():
    m=module()  # Also proves optional kipy is not needed just to import the script.
    import json
    value=json.loads((ROOT/'integrations/kicad/plugin.json').read_text())
    assert value['runtime']['type']=='python'
    assert value['actions'][0]['scopes']==['pcb'] and value['actions'][0]['show-button'] is True
    assert all((ROOT/'integrations/kicad'/p).is_file() for p in value['actions'][0]['icons-light'])



def test_main_with_pinned_sdk_without_newer_close_api(setup,monkeypatch,tmp_path):
    m=module();config,client,board,saved,calls,launched,run=setup
    import sys
    monkeypatch.setitem(sys.modules,'kipy',SimpleNamespace(KiCad=lambda **kw:client))
    monkeypatch.setenv('KICAD_API_SOCKET','qa-socket')
    monkeypatch.setattr(m,'configuration',lambda path:config)
    monkeypatch.setattr(m,'transfer',lambda k,c:tmp_path/'done.mcam-transfer')
    assert m.main()==0
