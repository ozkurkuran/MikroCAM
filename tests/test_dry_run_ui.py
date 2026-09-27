"""Reviewed dry-run UI bindings, bounded previews and owned Qt preparation."""
from threading import Event, get_ident
from types import SimpleNamespace

import pytest
from PyQt6 import QtCore, QtWidgets

from mikrocam.core.gcode_models import SourceSnapshot
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.ui.dry_run_panel import DryRunPanel
from mikrocam.ui.dry_run_worker import DryRunWorker
from mikrocam.ui.machine_panel import MachinePanel
from mikrocam.ui.machine_worker import MachineWorker
from mikrocam.ui.preflight_panel import PreflightPanel
from mikrocam.machine.job_models import JobObservation
from mikrocam.machine.models import ConnectionState, MachineSnapshot
from test_gcode_preflight import HEADER, setup


def reviewed(lines=1):
    source = SourceSnapshot('cut.nc', HEADER + 'M3 S100\n' +
                            ''.join(f'G1 X{1 + index % 2} Z0 F60\n' for index in range(lines)) + 'M30\n')
    return source, analyze_gcode(source, setup())


@pytest.fixture
def panel(qtbot):
    source, report = reviewed()
    widget = DryRunPanel(source=source, report=report)
    qtbot.addWidget(widget)
    yield widget
    assert widget.shutdown()


def prepare(panel, qtbot, height='8'):
    panel.height_edit.setText(height)
    panel.prepare()
    qtbot.waitUntil(lambda: panel._worker is None, timeout=3000)
    assert panel.result is not None, panel.summary_label.text()
    return panel.result


def test_height_is_blank_and_prepare_requires_explicit_valid_value(panel):
    assert panel.height_edit.text() == '' and not panel.transfer_button.isEnabled()
    panel.prepare()
    assert panel._worker is None and panel.result is None
    assert panel.summary_label.text()


def test_real_worker_preview_identifies_original_derived_plane_bounds_time_and_lineage(panel, qtbot,
                                                                                     monkeypatch):
    import mikrocam.ui.dry_run_worker as module
    original = module.prepare_dry_run
    owners = []
    def calculate(*args, **kwargs):
        owners.append(get_ident())
        return original(*args, **kwargs)
    monkeypatch.setattr(module, 'prepare_dry_run', calculate)
    value = prepare(panel, qtbot)
    assert owners and owners[0] != get_ident()
    assert value.original_source.sha256 in panel.summary_label.text()
    assert value.prepared_job.source.sha256 in panel.summary_label.text()
    assert '8' in panel.summary_label.text() and 'nominal' in panel.summary_label.text().lower()
    assert panel.preview_table.rowCount() == min(200, len(value.lineage))
    for row in range(panel.preview_table.rowCount()):
        assert panel.preview_table.item(row, 0).text() == str(row + 1)
        origin = value.lineage[row]
        assert panel.preview_table.item(row, 1).text() == ('Generated' if origin is None else str(origin))


def test_large_preview_is_capped_with_total_visible(qtbot):
    source, report = reviewed(220)
    widget = DryRunPanel(source=source, report=report)
    qtbot.addWidget(widget)
    try:
        value = prepare(widget, qtbot)
        assert len(value.lineage) > 200 and widget.preview_table.rowCount() == 200
        assert str(len(value.lineage)) in widget.summary_label.text()
    finally:
        assert widget.shutdown()


@pytest.mark.parametrize('change', ['height', 'source', 'cancel'])
def test_pending_real_preparation_is_cancelled_and_stale_output_suppressed(panel, qtbot, monkeypatch, change):
    import mikrocam.ui.dry_run_worker as module
    original = module.prepare_dry_run
    entered, release = Event(), Event()
    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(2)
        return original(*args, **kwargs)
    monkeypatch.setattr(module, 'prepare_dry_run', delayed)
    panel.height_edit.setText('8')
    panel.prepare()
    try:
        qtbot.waitUntil(entered.is_set)
        if change == 'height':
            panel.height_edit.setText('9')
        elif change == 'source':
            panel.set_source(*reviewed(2))
        else:
            panel.cancel()
        release.set()
        qtbot.waitUntil(lambda: panel._worker is None, timeout=2500)
        assert panel.result is None and panel.reviewed_binding() is None
        assert not panel.transfer_button.isEnabled()
    finally:
        release.set()


def test_explicit_transfer_uses_only_derived_reviewed_binding_and_height_invalidates(panel, qtbot):
    transfers = []
    panel.job_receiver = lambda *args: transfers.append(args)
    value = prepare(panel, qtbot)
    assert not transfers
    panel.transfer()
    assert transfers[0][:2] == (value.prepared_job.source, value.prepared_job.report)
    provider = transfers[0][2]
    assert provider() == transfers[0][:2]
    changes = []
    panel.reviewed_changed.connect(lambda: changes.append(True))
    panel.height_edit.setText('9')
    assert changes and provider() is None and panel.preview_table.rowCount() == 0


def test_preflight_owns_one_reused_dry_dock_and_shutdown(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    widget = PreflightPanel(window)
    source, report = reviewed()
    widget.load_source(source)
    assert not widget.dry_run_button.isEnabled()
    widget.report = report
    widget._sync_controls()
    assert widget.dry_run_button.isEnabled()
    first = widget.open_dry_run()
    second = widget.open_dry_run()
    assert first is second and first.height_edit.text() == ''
    prepare(first, qtbot)
    assert widget.shutdown() and first.reviewed_binding() is None


def test_original_closed_or_changed_synchronously_discards_machine_pending_start(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    preflight = PreflightPanel(window)
    source, report = reviewed()
    preflight.load_source(source)
    preflight.report = report
    dry = preflight.open_dry_run()
    value = prepare(dry, qtbot)
    machine = MachinePanel(window, ports_provider=lambda: ())
    try:
        machine.load_preflight(value.prepared_job.source, value.prepared_job.report, dry.reviewed_binding)
        qtbot.waitUntil(lambda: machine.job_controls.prepared_job is not None)
        worker = MachineWorker(lambda: None)
        ready = MachineSnapshot(connection=ConnectionState.CONNECTED, job=JobObservation(can_start=True))
        worker._publish(ready)
        machine._worker = worker
        machine.last_snapshot = ready
        machine._render_snapshot()
        machine.job_controls.confirm_checkbox.setChecked(True)
        machine.job_controls.start_button.click()
        assert worker._pending is not None
        preflight.setup_widget.changed.emit()
        assert worker._pending is None and machine.job_controls.prepared_job is None
        assert dry.result is None and dry.reviewed_binding() is None
    finally:
        machine._worker = None
        assert machine.shutdown() and preflight.shutdown()


def test_shutdown_timeout_keeps_worker_and_refuses_close(panel, monkeypatch):
    worker = SimpleNamespace(cancel=lambda: None, wait=lambda timeout: False)
    panel._worker = worker
    assert not panel.shutdown() and panel._worker is worker
    event = QtCore.QEvent(QtCore.QEvent.Type.Close)
    panel.closeEvent(event)
    assert not event.isAccepted()
    panel._worker = None


def test_closed_standalone_panel_cannot_accept_a_late_prepare_click(panel):
    panel.height_edit.setText('8')
    assert panel.shutdown()
    panel.prepare()
    assert panel._worker is None and not panel.prepare_button.isEnabled()


def test_close_and_explicit_reopen_reuses_dock_without_reusing_approval(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    widget = PreflightPanel(window)
    source, report = reviewed()
    widget.load_source(source)
    widget.report = report
    dry = widget.open_dry_run()
    prepare(dry, qtbot)
    dry.close()
    assert dry.result is None and dry.reviewed_binding() is None
    reopened = widget.open_dry_run()
    assert reopened is dry and dry.result is None
    assert dry.prepare_button.isEnabled()
    assert widget.shutdown()


def test_parent_shutdown_cancels_both_workers_and_shares_one_two_second_budget(qtbot, monkeypatch):
    import mikrocam.ui.preflight_panel as module
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    widget = PreflightPanel(window)
    source, report = reviewed()
    widget.load_source(source)
    widget.report = report
    dry = widget.open_dry_run()
    events, clock = [], [0.]
    monkeypatch.setattr(module, 'monotonic', lambda: clock[0])
    def wait_dry(timeout):
        events.append(('dry-wait', timeout))
        clock[0] += timeout / 1000
        return False
    dry._worker = SimpleNamespace(cancel=lambda: events.append(('dry-cancel',)), wait=wait_dry)
    widget._worker = SimpleNamespace(cancel=lambda: events.append(('preflight-cancel',)),
                                     wait=lambda timeout: events.append(('preflight-wait', timeout)) or False)
    try:
        assert not widget.shutdown()
        first_wait = next(index for index, event in enumerate(events) if event[0].endswith('wait'))
        assert ('dry-cancel',) in events[:first_wait] and ('preflight-cancel',) in events[:first_wait]
        assert sum(event[1] for event in events if event[0].endswith('wait')) <= 2000
        assert dry._worker is not None and widget._worker is not None
    finally:
        dry._worker = widget._worker = None
        assert widget.shutdown()


def test_worker_cancel_before_start_never_delivers_result(qtbot):
    source, report = reviewed()
    worker = DryRunWorker(source, report, 8.)
    worker.cancel()
    with qtbot.waitSignal(worker.cancelled, timeout=2000):
        worker.start()
    assert worker.wait(2000) and worker.final_result is None
