"""DRC admission and precise startup dispatch use real Qt without KiCad."""
from types import SimpleNamespace
from hashlib import sha256
from dataclasses import replace
from pathlib import Path
import pytest
from PyQt6 import QtWidgets
from mikrocam.kicad.package import write_package
from mikrocam.ui.kicad_transfer import KiCadTransferDialog
from test_kicad_package import sample

@pytest.fixture
def dialog(qtbot,tmp_path):
    dispatch=[];parent=QtWidgets.QMainWindow();qtbot.addWidget(parent)
    app=SimpleNamespace(ui=parent,worker_task=SimpleNamespace(emit=dispatch.append))
    value=KiCadTransferDialog(app);qtbot.addWidget(value)
    return value,dispatch,tmp_path


def test_clean_package_direct_import_one_worker(dialog):
    value,dispatch,root=dialog;path=root/'set.mcam-transfer';write_package(path,sample())
    value.load_path(path)
    assert len(dispatch)==1 and value.busy and value.review is not None
    assert value.table.cellWidget(0,3).currentText()=='F.Cu'
    value._finished(((), 'test owner cleanup'))


def test_drc_errors_require_checkbox_and_recheck_at_import(dialog):
    value,dispatch,root=dialog;p=sample();d=b'{"violations":[{"severity":"error"}],"unconnected_items":[],"schematic_parity":[]}'
    p=replace(p,drc_bytes=d,manifest=replace(p.manifest,drc_sha256=sha256(d).hexdigest(),drc_errors=1))
    path=root/'errors.mcam-transfer';write_package(path,p);value.load_path(path)
    assert not dispatch and not value.import_button.isEnabled() and value.acknowledge.isVisibleTo(value)
    value.import_selected();assert not dispatch
    value.acknowledge.setChecked(True);value.review_selected();assert value.import_button.isEnabled()
    value.acknowledge.setChecked(False);value.import_selected();assert not dispatch
    value.acknowledge.setChecked(True);value.review_selected();value.import_selected();assert len(dispatch)==1
    value.reject();assert value.busy
    value._finished(((), 'test owner cleanup'))


def test_bad_archive_no_worker_or_publication(dialog):
    value,dispatch,root=dialog;path=root/'bad.mcam-transfer';path.write_bytes(b'bad')
    value.load_path(path)
    assert not dispatch and value.review is None and 'failed' in value.status_label.text().lower()


def test_startup_exact_package_before_legacy_quit_name(monkeypatch):
    from appMain import App
    import mikrocam.ui.kicad_transfer as mod
    got=[];monkeypatch.setattr(mod,'open_kicad_transfer',lambda app,path:got.append(path))
    app=SimpleNamespace(log=SimpleNamespace(debug=lambda *a:None))
    App.on_startup_args(app,['C:/exit-save/board.mcam-transfer'])
    assert got==['C:/exit-save/board.mcam-transfer']
