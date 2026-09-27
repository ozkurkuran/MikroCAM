"""Owned offline worker cancellation and delivery cannot touch GUI or hardware."""
from threading import Event, get_ident

import pytest
from PyQt6 import QtCore, QtWidgets

from mikrocam.core.gcode_models import SourceSnapshot
from mikrocam.ui.preflight_worker import PreflightWorker
from test_gcode_preflight import HEADER, setup


def test_real_worker_analyzes_immutable_inputs_off_gui_thread(qtbot, monkeypatch):
    import mikrocam.ui.preflight_worker as module
    original=module.analyze_gcode
    owners=[]
    def analyze(*args):
        assert QtCore.QThread.currentThread()!=QtWidgets.QApplication.instance().thread()
        owners.append(get_ident())
        return original(*args)
    monkeypatch.setattr(module,'analyze_gcode',analyze)
    source=SourceSnapshot('x.nc',HEADER+'G1 X1 F60')
    value=PreflightWorker(source,setup())
    with qtbot.waitSignal(value.completed,timeout=2000) as signal:
        value.start()
    assert value.wait(2000) and signal.args[0].allowed
    assert value.final_report is signal.args[0]
    assert len(owners)==1 and owners[0]!=get_ident()
    assert source.text==HEADER+'G1 X1 F60'


def test_cancel_before_start_skips_analysis_and_has_no_result(qtbot,monkeypatch):
    import mikrocam.ui.preflight_worker as module
    def forbidden(*args):
        pytest.fail('Cancelled worker must not analyze')
    monkeypatch.setattr(module,'analyze_gcode',forbidden)
    value=PreflightWorker(SourceSnapshot('x.nc',HEADER+'G1 X1 F60'),setup())
    value.cancel()
    with qtbot.waitSignal(value.cancelled,timeout=2000):
        value.start()
    assert value.wait(2000) and value.final_report is None


def test_cancel_after_calculation_suppresses_completed_delivery(qtbot,monkeypatch):
    import mikrocam.ui.preflight_worker as module
    original=module.analyze_gcode
    entered,release=Event(),Event()
    def paused(*args):
        report=original(*args)
        entered.set()
        assert release.wait(2)
        return report
    monkeypatch.setattr(module,'analyze_gcode',paused)
    value=PreflightWorker(SourceSnapshot('x.nc',HEADER+'G1 X1 F60'),setup())
    completed=[]
    value.completed.connect(completed.append)
    value.start()
    try:
        qtbot.waitUntil(entered.is_set)
        value.cancel()
        with qtbot.waitSignal(value.cancelled,timeout=2000):
            release.set()
        assert value.wait(2000) and not completed and value.final_report is None
    finally:
        release.set()
        assert value.wait(2000)


def test_worker_failure_is_bounded_and_not_a_report(qtbot,monkeypatch):
    import mikrocam.ui.preflight_worker as module
    def fail(*args):
        raise ValueError('x'*1000)
    monkeypatch.setattr(module,'analyze_gcode',fail)
    value=PreflightWorker(SourceSnapshot('x.nc',HEADER+'G1 X1 F60'),setup())
    with qtbot.waitSignal(value.failed,timeout=2000) as signal:
        value.start()
    assert value.wait(2000) and len(signal.args[0])==256 and value.final_report is None
