"""GUI-owned preflight snapshots and bounded worker lifecycle without hardware."""
from dataclasses import replace
from threading import Event, get_ident
from types import SimpleNamespace

import pytest
from PyQt6 import QtCore, QtWidgets

from mikrocam.core.gcode_models import Finding, PreflightReport, PreflightSetup, SourceSnapshot
from mikrocam.core.placement import Placement
from mikrocam.ui import preflight_panel


SOURCE = SourceSnapshot('job', 'G21 G90 G94\nG1 X1 F100\n')
SETUP = PreflightSetup((0., 0., 5.), Placement(), 0., (-10., -10., -10.),
                       (10., 10., 10.), 2.)


def report(source=SOURCE, **kwargs):
    value = PreflightReport(source.name, source.sha256, SETUP, True,
                            ((0., 0., 5.), (1., 0., 5.)), 2, 0, 1, 0, 1., .6,
                            ('mm',), ('absolute',), (), 0, 0)
    return replace(value, **kwargs)


class ControlledWorker(QtCore.QObject):
    completed = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    cancelled = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()

    def __init__(self, source, setup, parent=None):
        super().__init__(parent)
        self.source, self.setup = source, setup
        self.final_report = None
        self.running = self.cancel_flag = False
        self.wait_result = True
        self.waits = []

    def start(self):
        self.running = True

    def cancel(self):
        self.cancel_flag = True

    def is_cancelled(self):
        return self.cancel_flag

    def wait(self, timeout):
        self.waits.append(timeout)
        if self.wait_result:
            self.running = False
        return self.wait_result

    def finish(self, value=None):
        if value is not None:
            self.final_report = value
            self.completed.emit(value)
        self.running = False
        self.finished.emit()


@pytest.fixture
def panel(qtbot, monkeypatch):
    monkeypatch.setattr(preflight_panel, 'PreflightWorker', ControlledWorker)
    widget = preflight_panel.PreflightPanel()
    qtbot.addWidget(widget)
    monkeypatch.setattr(widget.setup_widget, 'value', lambda: SETUP)
    yield widget
    if widget._worker is not None:
        widget._worker.wait_result = True
    assert widget.shutdown()


def test_empty_setup_never_starts_worker(qtbot, monkeypatch):
    monkeypatch.setattr(preflight_panel, 'PreflightWorker', ControlledWorker)
    widget = preflight_panel.PreflightPanel()
    qtbot.addWidget(widget)
    assert all(not field.text() for field in widget.setup_widget.fields.values())
    widget.load_source(SOURCE)
    widget.analyze()
    assert widget._worker is None and widget.report is None
    assert widget.result_label.text()
    assert widget.shutdown()


def test_success_displays_exact_source_identity_report_and_assumptions(panel, qtbot):
    panel.load_source(SOURCE)
    assert SOURCE.name in panel.source_label.text() and SOURCE.sha256 in panel.source_label.text()
    panel.analyze()
    worker = panel._worker
    assert worker.source is SOURCE and worker.setup == SETUP
    assert not panel.analyze_button.isEnabled() and panel.cancel_button.isEnabled()
    panel.analyze()
    assert panel._worker is worker
    worker.finish(report())
    qtbot.waitUntil(lambda: panel._worker is None)
    assert panel.report == report()
    text = panel.result_label.text().lower()
    assert 'declared' in text and 'nominal' in text and 'physical' in text
    assert worker.waits == [2000]


def test_partial_bounds_unknown_time_and_capped_findings_are_explicit(panel, qtbot):
    panel.load_source(SOURCE)
    panel.analyze()
    findings = tuple(Finding(i + 1, 'unsupported', 'Unknown semantics') for i in range(200))
    value = report(complete=False, duration_seconds=None, findings=findings,
                   finding_count=250, error_count=250)
    panel._worker.finish(value)
    qtbot.waitUntil(lambda: panel._worker is None)
    assert panel.findings_table.rowCount() == 200
    text = panel.result_label.text().lower()
    assert 'partial' in text and 'unknown' in text and '250' in text


@pytest.mark.parametrize('change', ['source', 'setup', 'cancel'])
def test_changed_or_cancelled_inputs_reject_already_queued_completion(panel, qtbot, change):
    panel.load_source(SOURCE)
    panel.analyze()
    worker = panel._worker
    worker.finish(report())
    if change == 'source':
        panel.load_source(SourceSnapshot('new', 'G21 G90\nG0 Z6\n'))
    elif change == 'setup':
        panel.setup_widget.changed.emit()
    else:
        panel.cancel()
    qtbot.waitUntil(lambda: panel._worker is None)
    assert worker.cancel_flag and panel.report is None
    assert panel.findings_table.rowCount() == 0


def test_completed_result_is_cleared_when_setup_changes(panel, qtbot):
    panel.load_source(SOURCE)
    panel.analyze()
    panel._worker.finish(report())
    qtbot.waitUntil(lambda: panel._worker is None)
    panel.setup_widget.changed.emit()
    assert panel.report is None and panel.findings_table.rowCount() == 0


def test_old_cancellation_signal_preserves_new_input_explanation(panel, qtbot):
    panel.load_source(SOURCE)
    panel.analyze()
    worker = panel._worker
    panel.load_source(SourceSnapshot('replacement', SOURCE.text))
    explanation = panel.result_label.text()
    worker.cancelled.emit()
    worker.finish()
    qtbot.waitUntil(lambda: panel._worker is None)
    assert panel.result_label.text() == explanation and panel.report is None


def test_failed_file_load_clears_report_but_labels_retained_snapshot(panel, qtbot, tmp_path):
    panel.load_source(SOURCE)
    panel.analyze()
    panel._worker.finish(report())
    qtbot.waitUntil(lambda: panel._worker is None)
    panel.load_file(tmp_path / 'missing.nc')
    assert panel.report is None and panel.source is SOURCE
    assert SOURCE.sha256 in panel.source_label.text()
    assert 'previous' in panel.result_label.text().lower()
    assert panel.analyze_button.isEnabled()


@pytest.mark.parametrize('change', ['edit', 'delete', 'replacement'])
def test_selected_provider_refresh_invalidates_result(panel, qtbot, change):
    current = [SOURCE]
    panel.source_provider = lambda: current[0]
    panel.use_selected()
    panel.analyze()
    panel._worker.finish(report())
    qtbot.waitUntil(lambda: panel._worker is None)
    if change == 'delete':
        current[0] = None
    elif change == 'replacement':
        current[0] = SourceSnapshot('other selection', SOURCE.text)
    else:
        current[0] = SourceSnapshot(SOURCE.name, 'G21 G90\nG0 Z99\n')
    qtbot.waitUntil(lambda: panel.report is None, timeout=1500)
    assert panel.source is None


def test_selected_provider_is_rechecked_before_queued_result_display(panel, qtbot):
    current = [SOURCE]
    panel.source_provider = lambda: current[0]
    panel.use_selected()
    panel.analyze()
    worker = panel._worker
    worker.finish(report())
    current[0] = SourceSnapshot('replacement', SOURCE.text)
    qtbot.waitUntil(lambda: panel._worker is None)
    assert panel.report is None and panel.source is None


def test_selected_provider_failure_is_visible_and_clears_prior_source(panel):
    panel.load_source(SOURCE)
    def failed_provider():
        raise RuntimeError('selected object was deleted')
    panel.source_provider = failed_provider
    panel.use_selected()
    assert panel.source is None and panel.report is None
    assert 'selected object was deleted' in panel.result_label.text()
    assert not panel.analyze_button.isEnabled()


def test_file_snapshot_remains_identified_after_external_file_edit(panel, tmp_path, qtbot):
    path = tmp_path / 'loaded.nc'
    path.write_text(SOURCE.text, encoding='utf-8')
    panel.load_file(path)
    loaded = panel.source
    assert 'snapshot' in panel.source_label.text().lower()
    panel.analyze()
    panel._worker.finish(report(loaded))
    qtbot.waitUntil(lambda: panel._worker is None)
    path.write_text('changed', encoding='utf-8')
    qtbot.wait(550)
    assert panel.source == loaded and panel.report is not None


def test_cancelled_file_dialog_leaves_current_source_and_result(panel, monkeypatch, qtbot):
    panel.load_source(SOURCE)
    panel.analyze()
    panel._worker.finish(report())
    qtbot.waitUntil(lambda: panel._worker is None)
    previous = panel.report
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileName', lambda *a, **k: ('', ''))
    panel.load_file()
    assert panel.source is SOURCE and panel.report is previous


@pytest.mark.parametrize('mismatch', ['source', 'setup'])
def test_worker_report_with_mismatched_identity_is_never_presented(panel, qtbot, mismatch):
    panel.load_source(SOURCE)
    panel.analyze()
    value = (report(SourceSnapshot('other', SOURCE.text)) if mismatch == 'source'
             else report(setup=replace(SETUP, safe_z_mm=3.)))
    panel._worker.finish(value)
    qtbot.waitUntil(lambda: panel._worker is None)
    assert panel.report is None


def test_worker_error_is_visible_without_a_success_report(panel, qtbot):
    panel.load_source(SOURCE)
    panel.analyze()
    panel._worker.failed.emit('analysis failed')
    panel._worker.finish()
    qtbot.waitUntil(lambda: panel._worker is None)
    assert 'analysis failed' in panel.result_label.text() and panel.report is None


def test_shutdown_timeout_retains_worker_and_ignores_close_then_allows_retry(panel):
    panel.load_source(SOURCE)
    panel.analyze()
    worker = panel._worker
    worker.wait_result = False
    assert not panel.shutdown()
    assert panel._worker is worker and worker.cancel_flag
    event = QtCore.QEvent(QtCore.QEvent.Type.Close)
    panel.closeEvent(event)
    assert not event.isAccepted() and panel._worker is worker
    worker.wait_result = True
    assert panel.shutdown() and panel._worker is None


def test_shutdown_and_restart_suppresses_old_sender(panel, qtbot):
    panel.load_source(SOURCE)
    panel.analyze()
    old = panel._worker
    assert panel.shutdown()
    panel.analyze()
    current = panel._worker
    old.completed.emit(report())
    qtbot.wait(10)
    assert panel._worker is current and panel.report is None
    current.finish(report())
    qtbot.waitUntil(lambda: panel._worker is None)
    assert panel.report is not None


def test_lazy_singleton_provider_never_selects_or_exports(qtbot, monkeypatch):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    job = SimpleNamespace(kind='cncjob', source_file=SOURCE.text, obj_options={'name': SOURCE.name})
    calls = []
    def get_active():
        calls.append(True)
        return job
    app = SimpleNamespace(ui=window, collection=SimpleNamespace(get_active=get_active))
    first = preflight_panel.open_preflight_panel(app)
    qtbot.addWidget(first)
    second = preflight_panel.open_preflight_panel(app)
    assert first is second and calls == [] and first.source is None
    first.use_selected()
    assert first.source == SOURCE and calls == [True]
    assert first.shutdown()


@pytest.fixture
def real_panel(qtbot, monkeypatch):
    widget = preflight_panel.PreflightPanel()
    qtbot.addWidget(widget)
    monkeypatch.setattr(widget.setup_widget, 'value', lambda: SETUP)
    yield widget
    assert widget.shutdown()


@pytest.mark.parametrize('text, allowed', [(SOURCE.text, True),
                                          ('G21 G90 G94\nG0 X99\n', False)])
def test_real_worker_delivers_allowed_or_hazard_report_on_gui_thread(real_panel, qtbot, monkeypatch,
                                                                  text, allowed):
    import mikrocam.ui.preflight_worker as module
    original_analyze, original_render = module.analyze_gcode, real_panel._render_report
    analysis_threads, render_threads = [], []
    gui = get_ident()
    def analyze(*args):
        analysis_threads.append(get_ident())
        return original_analyze(*args)
    def render(value):
        assert QtCore.QThread.currentThread() == QtWidgets.QApplication.instance().thread()
        render_threads.append(get_ident())
        original_render(value)
    monkeypatch.setattr(module, 'analyze_gcode', analyze)
    monkeypatch.setattr(real_panel, '_render_report', render)
    real_panel.load_source(SourceSnapshot('real.nc', text))
    real_panel.analyze()
    qtbot.waitUntil(lambda: real_panel._worker is None, timeout=3000)
    assert real_panel.report.allowed is allowed
    assert len(analysis_threads) == 1 and analysis_threads[0] != gui
    assert render_threads == [gui]


@pytest.mark.parametrize('change', ['cancel', 'setup', 'source'])
def test_real_large_source_change_cancels_owned_analysis_without_stale_report(real_panel, qtbot,
                                                                           monkeypatch, change):
    import mikrocam.ui.preflight_worker as module
    original = module.analyze_gcode
    entered, release = Event(), Event()
    def paused(source, setup, cancelled):
        assert QtCore.QThread.currentThread() != QtWidgets.QApplication.instance().thread()
        checks = 0
        def checkpoint():
            nonlocal checks
            checks += 1
            if checks == 32:
                entered.set()
                assert release.wait(2)
            return cancelled()
        return original(source, setup, checkpoint)
    monkeypatch.setattr(module, 'analyze_gcode', paused)
    source = SourceSnapshot('large.nc', 'G21 G90 G94\n' + 'G1 X1 F100\n' * 100_000)
    real_panel.load_source(source)
    real_panel.analyze()
    try:
        qtbot.waitUntil(entered.is_set)
        owned = real_panel._worker
        real_panel.analyze()
        assert real_panel._worker is owned
        if change == 'cancel':
            real_panel.cancel()
        elif change == 'setup':
            real_panel.setup_widget.changed.emit()
        else:
            real_panel.load_source(SOURCE)
        assert owned.is_cancelled()
        release.set()
        qtbot.waitUntil(lambda: real_panel._worker is None, timeout=2000)
        assert real_panel.report is None
    finally:
        release.set()


def test_ten_real_worker_sessions_leave_no_owner_or_stale_result(real_panel, qtbot):
    for _ in range(10):
        real_panel.load_source(SOURCE)
        real_panel.analyze()
        qtbot.waitUntil(lambda: real_panel._worker is None, timeout=2000)
        assert real_panel.report.allowed and real_panel.shutdown()
        assert real_panel._worker is None
