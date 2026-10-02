"""Installer changes only bridge files/API setting and retains backups."""
import json
from pathlib import Path
import pytest
from mikrocam.kicad.install_plugin import install_plugin


def test_targeted_install_reinstall_backups_and_settings(tmp_path):
    plugins=tmp_path/'plugins';settings=tmp_path/'settings/kicad_common.json'
    settings.parent.mkdir();settings.write_text(json.dumps({'theme':'dark','api':{'enable_server':False,'other':42}}))
    other=plugins/'other/plugin.json';other.parent.mkdir(parents=True);other.write_bytes(b'untouched')
    result=install_plugin(plugins,settings,Path(__import__('sys').executable),tmp_path/'transfers')
    assert other.read_bytes()==b'untouched'
    config=json.loads((result/'config.json').read_text())
    assert config['schema']==1 and Path(config['repo_root']).is_dir()
    updated=json.loads(settings.read_text());assert updated=={'theme':'dark','api':{'enable_server':True,'other':42}}
    backups=list(settings.parent.glob('kicad_common.json.mikrocam-backup-*'));assert len(backups)==1
    assert json.loads(backups[0].read_text())['api']['enable_server'] is False
    first=(result/'config.json').read_bytes();(result/'custom.txt').write_bytes(b'preserved')
    install_plugin(plugins,settings,Path(__import__('sys').executable),tmp_path/'transfers')
    assert (result/'custom.txt').read_bytes()==b'preserved'
    assert (result/'config.json').read_bytes()==first
    assert len(list(plugins.rglob('plugin.json')))==2, 'Backups must not register duplicate KiCad actions'
    assert any(p.name=='config.json' for p in (plugins.parent/'mikrocam-bridge-backups').rglob('*'))


def test_bad_settings_not_overwritten(tmp_path):
    settings=tmp_path/'kicad_common.json';settings.write_bytes(b'bad settings')
    with pytest.raises(ValueError):install_plugin(tmp_path/'plugins',settings,Path(__import__('sys').executable),tmp_path/'out')
    assert settings.read_bytes()==b'bad settings'
