"""Command failure, snapshot and common-coordinate export contracts without KiCad."""
import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import subprocess
import pytest
from mikrocam.kicad.export import export_board, discover_cli
from mikrocam.kicad.package import read_package
from test_kicad_package import GERBER,DRILL

@pytest.fixture
def source(tmp_path):
    p=tmp_path/'board space.kicad_pcb';p.write_bytes(b'(kicad_pcb (version 20260101))')
    p.with_suffix('.kicad_pro').write_text('{}');return p

def runner(calls,fail='',drc_error=False):
    def run(args,**kwargs):
        calls.append((args,kwargs))
        stage=args[1:4]
        if stage==['version']:return SimpleNamespace(returncode=0,stdout='10.0.6\n',stderr='')
        if fail=='timeout':raise subprocess.TimeoutExpired(args,60)
        if fail and fail in args:return SimpleNamespace(returncode=1,stdout='',stderr='export failed')
        out=Path(args[args.index('--output')+1])
        board=Path(args[-1]);assert board.is_file() and board.with_suffix('.kicad_pro').is_file()
        if args[1:3]==['pcb','drc']:
            report={'violations':[{'severity':'error'}] if drc_error else [],'unconnected_items':[],'schematic_parity':[]}
            out.write_text(json.dumps(report));board.write_bytes(board.read_bytes()+b'\n(refilled)')
        elif 'gerbers' in args:
            (out/'board-F_Cu.gbr').write_bytes(GERBER)
            (out/'board-Edge_Cuts.gbr').write_bytes(GERBER.replace(b'Copper,L1,Top',b'Profile,NP'))
            (out/'board-B_Cu.gbr').write_bytes(b'%MOMM*%M02*')
        elif 'drill' in args:
            (out/'board-PTH.drl').write_bytes(DRILL)
            (out/'board-NPTH.drl').write_bytes(b'M48\nMETRIC,TZ\n%\nM30\n')
        return SimpleNamespace(returncode=0,stdout='',stderr='')
    return run

def test_realistic_pipeline_snapshot_common_origin_and_drc(source,tmp_path,monkeypatch):
    import mikrocam.kicad.export as mod
    calls=[];monkeypatch.setattr(mod.subprocess,'run',runner(calls,drc_error=True))
    before=source.read_bytes();out=tmp_path/'set.mcam-transfer'
    export_board(source,out,kicad_cli='fake-cli')
    p=read_package(out)
    assert source.read_bytes()==before and p.manifest.board_sha256==sha256(before).hexdigest()
    assert p.manifest.drc_errors==1 and p.manifest.units=='MM' and p.manifest.origin=='absolute'
    assert len(p.manifest.files)==3 and len(p.manifest.skipped_empty)==2
    assert all(c[1]['shell'] is False and c[1]['timeout']==60 for c in calls)
    assert '--use-drill-file-origin' not in calls[2][0] and '--excellon-mirror-y' not in calls[3][0]
    assert calls[3][0][calls[3][0].index('--drill-origin')+1]=='absolute'
    assert Path(calls[1][0][-1])!=source and not Path(calls[1][0][-1]).exists()

@pytest.mark.parametrize('failure',['drc','gerbers','drill','timeout'])
def test_failed_command_never_publishes(source,tmp_path,monkeypatch,failure):
    import mikrocam.kicad.export as mod
    monkeypatch.setattr(mod.subprocess,'run',runner([],fail=failure))
    out=tmp_path/'set.mcam-transfer'
    with pytest.raises(ValueError):export_board(source,out,kicad_cli='fake-cli')
    assert not out.exists()

def test_source_change_prevents_mixed_snapshot(source,tmp_path,monkeypatch):
    import mikrocam.kicad.export as mod
    base=runner([])
    def changing(args,**kwargs):
        v=base(args,**kwargs)
        if 'drc' in args:source.write_bytes(b'changed')
        return v
    monkeypatch.setattr(mod.subprocess,'run',changing)
    with pytest.raises(ValueError):export_board(source,tmp_path/'x.mcam-transfer',kicad_cli='fake-cli')

@pytest.mark.parametrize('version',['9.0.0','11.0.0','not-kicad'])
def test_unsupported_cli_version(source,tmp_path,monkeypatch,version):
    import mikrocam.kicad.export as mod
    monkeypatch.setattr(mod.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=version,stderr=''))
    with pytest.raises(ValueError):export_board(source,tmp_path/'x.mcam-transfer',kicad_cli='fake-cli')

def test_missing_cli_actionable(monkeypatch):
    import mikrocam.kicad.export as mod
    monkeypatch.setattr(mod.shutil,'which',lambda *a:None)
    monkeypatch.setattr(mod,'_windows_candidates',lambda:())
    with pytest.raises(ValueError,match='KiCad'):discover_cli()


def test_output_cannot_replace_source_project(source,monkeypatch):
    import mikrocam.kicad.export as mod
    calls=[];monkeypatch.setattr(mod.subprocess,'run',runner(calls))
    project=source.with_suffix('.kicad_pro');before=project.read_bytes()
    with pytest.raises(ValueError):export_board(source,project,kicad_cli='fake-cli')
    assert not calls and project.read_bytes()==before


def test_missing_selected_layer_refused(source,tmp_path,monkeypatch):
    import mikrocam.kicad.export as mod
    base=runner([])
    def missing(args,**kwargs):
        result=base(args,**kwargs)
        if 'gerbers' in args:(Path(args[args.index('--output')+1])/'board-B_Cu.gbr').unlink()
        return result
    monkeypatch.setattr(mod.subprocess,'run',missing)
    with pytest.raises(ValueError):export_board(source,tmp_path/'set.mcam-transfer',kicad_cli='fake-cli')
