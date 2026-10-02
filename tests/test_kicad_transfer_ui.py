"""DRC admission and responsive preparation use real Qt without KiCad."""
from types import SimpleNamespace
from hashlib import sha256
from dataclasses import replace
from pathlib import Path
import threading
import pytest
from PyQt6 import QtCore,QtWidgets
from mikrocam.kicad.package import write_package
from mikrocam.ui.kicad_transfer import KiCadTransferDialog
from test_kicad_package import sample

@pytest.fixture
def dialog(qtbot,tmp_path):
    dispatch=[];parent=QtWidgets.QMainWindow();qtbot.addWidget(parent)
    app=SimpleNamespace(ui=parent,worker_task=SimpleNamespace(emit=dispatch.append))
    value=KiCadTransferDialog(app);qtbot.addWidget(value)
    return value,dispatch,tmp_path,qtbot


def complete_preparation(context):
    value,dispatch,root,qtbot=context
    assert len(dispatch)==1 and value.busy and value.package is None
    task=dispatch.pop(0);task['fcn'](*task['params'])
    qtbot.waitUntil(lambda:value.package is not None or not value.busy)


def test_clean_package_direct_import_one_worker(dialog):
    value,dispatch,root,qtbot=dialog;path=root/'set.mcam-transfer';write_package(path,sample())
    value.load_path(path);complete_preparation(dialog)
    assert len(dispatch)==1 and value.busy and value.review is not None, value.status_label.text()
    assert value.table.cellWidget(0,3).currentText()=='F.Cu'
    value._finished(((), 'test owner cleanup'))


def test_drc_errors_require_checkbox_and_recheck_at_import(dialog):
    value,dispatch,root,qtbot=dialog;p=sample();d=b'{"violations":[{"severity":"error"}],"unconnected_items":[],"schematic_parity":[]}'
    p=replace(p,drc_bytes=d,manifest=replace(p.manifest,drc_sha256=sha256(d).hexdigest(),drc_errors=1))
    path=root/'errors.mcam-transfer';write_package(path,p);value.load_path(path);complete_preparation(dialog)
    assert not dispatch and not value.import_button.isEnabled() and value.acknowledge.isVisibleTo(value), value.status_label.text()
    value.import_selected();assert not dispatch
    value.acknowledge.setChecked(True);value.review_selected();assert value.import_button.isEnabled()
    value.acknowledge.setChecked(False);value.import_selected();assert not dispatch
    value.acknowledge.setChecked(True);value.review_selected();value.import_selected();assert len(dispatch)==1
    value.reject();assert value.busy
    value._finished(((), 'test owner cleanup'))


def test_bad_archive_no_worker_or_publication(dialog):
    value,dispatch,root,qtbot=dialog;path=root/'bad.mcam-transfer';path.write_bytes(b'bad')
    value.load_path(path);complete_preparation(dialog)
    assert not dispatch and value.review is None and 'failed' in value.status_label.text().lower()


def test_package_preparation_keeps_gui_events_running(dialog,monkeypatch):
    import mikrocam.ui.kicad_transfer as mod
    value,dispatch,root,qtbot=dialog;path=root/'set.mcam-transfer';write_package(path,sample())
    read=mod.read_package;started=threading.Event();release=threading.Event();calls=[];ticks=[]
    def blocking_reader(source):
        calls.append(QtCore.QThread.currentThread()!=value.thread());started.set()
        if not release.wait(5):raise TimeoutError('test release missing')
        return read(source)
    monkeypatch.setattr(mod,'read_package',blocking_reader)
    import mikrocam.ui.manufacturing_import as base
    def gui_io(*args):raise AssertionError('Fresh source I/O belongs to preparation/import workers')
    monkeypatch.setattr(base,'review_manufacturing_files',gui_io)
    value.load_path(path)
    assert not calls and len(dispatch)==1 and value.busy and value.package is None
    value.reject();assert value.busy, 'Preparation lifetime must remain owned until it finishes'
    task=dispatch.pop(0);worker=threading.Thread(target=task['fcn'],args=task['params'])
    worker.start()
    try:
        assert started.wait(2)
        QtCore.QTimer.singleShot(0,lambda:ticks.append(True))
        qtbot.waitUntil(lambda:bool(ticks))
        assert calls==[True] and value.package is None and not dispatch
    finally:
        release.set();worker.join(5)
    assert not worker.is_alive()
    qtbot.waitUntil(lambda:value.package is not None)
    assert len(dispatch)==1 and value.busy and value.review is not None
    value._finished(((), 'test owner cleanup'))


def test_startup_exact_package_before_legacy_quit_name(monkeypatch):
    from appMain import App
    import mikrocam.ui.kicad_transfer as mod
    got=[];monkeypatch.setattr(mod,'open_kicad_transfer',lambda app,path:got.append(path))
    app=SimpleNamespace(log=SimpleNamespace(debug=lambda *a:None))
    App.on_startup_args(app,['C:/exit-save/board.mcam-transfer'])
    assert got==['C:/exit-save/board.mcam-transfer']
