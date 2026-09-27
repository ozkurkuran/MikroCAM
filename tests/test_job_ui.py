"""Explicit reviewed-source transfer, mechanical confirmation and truthful job UI."""
from dataclasses import replace
from types import SimpleNamespace

import pytest
from PyQt6 import QtCore, QtWidgets

from mikrocam.core.cnc_job import PreparedJob
from mikrocam.core.gcode_models import SourceSnapshot
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.machine.job_models import JobObservation, JobPhase
from mikrocam.machine.models import ConnectionState, MachineSnapshot
from mikrocam.ui.job_controls import JobControls
from mikrocam.ui.machine_panel import MachinePanel
from mikrocam.ui.preflight_panel import PreflightPanel
from test_gcode_preflight import HEADER, setup


def reviewed():
    source = SourceSnapshot('reviewed.nc', HEADER + 'G1 X1 F60\nM30')
    return source, analyze_gcode(source, setup())


def ready_snapshot(**changes):
    return MachineSnapshot(connection=ConnectionState.CONNECTED,
                           job=JobObservation(can_start=True, **changes))


def test_start_requires_new_explicit_mechanical_equipment_confirmation(qtbot):
    widget = JobControls()
    qtbot.addWidget(widget)
    source, report = reviewed()
    widget.set_job(PreparedJob(source, report))
    widget.set_snapshot(ready_snapshot(), True)
    assert not widget.start_button.isEnabled() and not widget.confirm_checkbox.isChecked()
    assert 'laser' in widget.confirm_checkbox.text().lower()
    widget.confirm_checkbox.setChecked(True)
    assert widget.start_button.isEnabled()
    with qtbot.waitSignal(widget.start_requested) as signal:
        widget.start_button.click()
    assert signal.args[0].mechanical_confirmed and not widget.confirm_checkbox.isChecked()
    assert not widget.start_button.isEnabled()


def test_progress_means_accepted_blocks_not_physical_completion(qtbot):
    widget = JobControls()
    qtbot.addWidget(widget)
    value = JobObservation(phase=JobPhase.COMPLETING, source_name='active.nc',
                           source_sha256='a' * 64, acknowledged=4, total=4, source_line=7,
                           diagnostic='Waiting for endpoint', can_stop=True)
    widget.set_snapshot(MachineSnapshot(connection=ConnectionState.CONNECTED, job=value), True)
    text = widget.progress_label.text().lower()
    assert 'accepted' in text and 'physical' in text and '4/4' in text and 'active.nc' in text
    assert not widget.start_button.isEnabled() and widget.stop_button.isEnabled()


def test_invalidated_start_intent_does_not_lock_new_transfer_with_unchanged_ready_observation(qtbot):
    widget = JobControls()
    qtbot.addWidget(widget)
    source, report = reviewed()
    job = PreparedJob(source, report)
    widget.set_job(job)
    widget.set_snapshot(ready_snapshot(), True)
    widget.set_pending()
    widget.set_job(None)
    widget.set_job(job)
    widget.confirm_checkbox.setChecked(True)
    assert widget.start_button.isEnabled()
    active = JobObservation(phase=JobPhase.RUNNING, source_name=source.name,
                            source_sha256=source.sha256, total=3, can_stop=True)
    widget.set_snapshot(MachineSnapshot(connection=ConnectionState.CONNECTED, job=active), True)
    widget.set_job(job)
    widget.confirm_checkbox.setChecked(True)
    assert not widget.start_button.isEnabled()


def test_disconnect_request_keeps_active_identity_while_coordinates_become_unavailable(panel):
    source, _report = reviewed()
    observation = JobObservation(phase=JobPhase.RUNNING, source_name=source.name,
                                 source_sha256=source.sha256, acknowledged=2, total=4,
                                 source_line=3, can_stop=True)
    panel.last_snapshot = MachineSnapshot(connection=ConnectionState.CONNECTED, job=observation)
    panel._worker = SimpleNamespace(stop=lambda: None)
    try:
        panel.disconnect_machine()
        assert panel.last_snapshot.job == observation
        assert source.sha256 in panel.job_controls.progress_label.text()
        assert not panel.job_controls.start_button.isEnabled()
    finally:
        panel._worker = None


@pytest.fixture
def panel(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    widget = MachinePanel(window, ports_provider=lambda: ())
    qtbot.addWidget(widget)
    yield widget
    assert widget.shutdown()


def test_transfer_prepares_off_serial_owner_and_changed_binding_invalidates_start(panel, qtbot):
    source, report = reviewed()
    current = [(source, report)]
    panel.load_preflight(source, report, lambda: current[0])
    qtbot.waitUntil(lambda: panel.job_controls.prepared_job is not None)
    panel.job_controls.set_snapshot(ready_snapshot(), True)
    panel.job_controls.confirm_checkbox.setChecked(True)
    current[0] = None
    qtbot.waitUntil(lambda: panel.job_controls.prepared_job is None, timeout=1500)
    assert not panel.job_controls.confirm_checkbox.isChecked()
    assert not panel.job_controls.start_button.isEnabled()


def test_confirmation_resets_on_reconnect_input_change_and_start(panel, qtbot):
    source, report = reviewed()
    panel.load_preflight(source, report)
    qtbot.waitUntil(lambda: panel.job_controls.prepared_job is not None)
    panel.job_controls.confirm_checkbox.setChecked(True)
    panel.disconnect_machine()
    assert not panel.job_controls.confirm_checkbox.isChecked()
    panel.load_preflight(source, report)
    assert not panel.job_controls.confirm_checkbox.isChecked()


def test_preflight_transfer_is_explicit_and_provider_invalidates_on_setup_or_close(qtbot):
    transfers = []
    widget = PreflightPanel(job_receiver=lambda *args: transfers.append(args))
    qtbot.addWidget(widget)
    source, report = reviewed()
    widget.load_source(source)
    widget.report = report
    widget._sync_controls()
    assert not transfers and widget.transfer_button.isEnabled()
    widget.transfer_to_machine()
    assert len(transfers) == 1 and transfers[0][:2] == (source, report)
    provider = transfers[0][2]
    assert provider() == (source, report)
    widget.setup_widget.changed.emit()
    assert provider() is None
    widget.report = report
    assert widget.shutdown() and provider() is None


def test_binding_rechecked_immediately_before_start_without_waiting_timer(panel, qtbot):
    source, report = reviewed()
    current = [(source, report)]
    panel.load_preflight(source, report, lambda: current[0])
    qtbot.waitUntil(lambda: panel.job_controls.prepared_job is not None)
    accepted = []
    panel._worker = SimpleNamespace(submit=lambda value: accepted.append(value) or True,
                                    invalidate_pending_job=lambda _job: False)
    panel.last_snapshot = ready_snapshot()
    panel.job_controls.set_snapshot(panel.last_snapshot, True)
    panel.job_controls.confirm_checkbox.setChecked(True)
    current[0] = None
    panel.job_controls.start_button.click()
    panel._worker = None
    assert not accepted and panel.job_controls.prepared_job is None


def test_active_job_identity_survives_preflight_replacement(panel, qtbot):
    source, report = reviewed()
    panel.load_preflight(source, report)
    qtbot.waitUntil(lambda: panel.job_controls.prepared_job is not None)
    observation = JobObservation(phase=JobPhase.RUNNING, source_name=source.name,
                                 source_sha256=source.sha256, acknowledged=1, total=3,
                                 source_line=1, can_pause=True, can_stop=True)
    panel.last_snapshot = MachineSnapshot(connection=ConnectionState.CONNECTED, job=observation)
    panel._render_snapshot()
    replacement = SourceSnapshot('replacement', source.text)
    panel.load_preflight(replacement, analyze_gcode(replacement, report.setup))
    assert source.sha256 in panel.job_controls.progress_label.text()
    assert source.name in panel.job_controls.progress_label.text()


def test_preflight_change_synchronously_discards_reserved_start_before_owner_admission(panel, qtbot):
    from mikrocam.ui.machine_worker import MachineWorker
    preflight = PreflightPanel()
    qtbot.addWidget(preflight)
    source, report = reviewed()
    preflight.load_source(source)
    preflight.report = report
    panel.load_preflight(source, report, preflight._execution_binding)
    qtbot.waitUntil(lambda: panel.job_controls.prepared_job is not None)
    worker = MachineWorker(lambda: None)
    worker._publish(ready_snapshot())
    panel._worker = worker
    panel.last_snapshot = ready_snapshot()
    panel._render_snapshot()
    panel.job_controls.confirm_checkbox.setChecked(True)
    panel.job_controls.start_button.click()
    assert worker._pending is not None
    preflight.setup_widget.changed.emit()
    assert worker._pending is None and panel.job_controls.prepared_job is None
    accepted = []
    worker._process_intent(SimpleNamespace(request_job=lambda request: accepted.append(request)))
    assert not accepted
    panel._worker = None
    assert preflight.shutdown()


def test_preparation_shutdown_timeout_retains_worker_and_window(panel, qtbot, monkeypatch):
    source, report = reviewed()
    panel.load_preflight(source, report)
    worker = panel._prepare_worker
    original = worker.wait
    monkeypatch.setattr(worker, 'wait', lambda timeout: False)
    assert not panel.shutdown() and panel._prepare_worker is worker
    event = QtCore.QEvent(QtCore.QEvent.Type.Close)
    panel.closeEvent(event)
    assert not event.isAccepted()
    monkeypatch.setattr(worker, 'wait', original)
    assert panel.shutdown()


def test_shutdown_prioritizes_serial_stop_and_shares_one_four_second_join_budget(panel, monkeypatch):
    import mikrocam.ui.machine_panel as module
    events, clock = [], [0.]
    monkeypatch.setattr(module, 'monotonic', lambda: clock[0], raising=False)
    def wait_prepare(timeout):
        events.append(('prepare-wait', timeout))
        clock[0] += timeout / 1000
        return False
    def wait_serial(timeout):
        events.append(('serial-wait', timeout))
        return False
    panel._prepare_worker = SimpleNamespace(cancel=lambda: events.append(('prepare-cancel',)),
                                             wait=wait_prepare)
    panel._worker = SimpleNamespace(stop=lambda: events.append(('serial-stop',)), wait=wait_serial)
    try:
        assert not panel.shutdown()
        assert events.index(('serial-stop',)) < next(i for i, item in enumerate(events)
                                                   if item[0] == 'prepare-wait')
        waits = [item[1] for item in events if item[0].endswith('wait')]
        assert sum(waits) <= 4000
    finally:
        panel._prepare_worker = panel._worker = None


@pytest.fixture
def real_panel(qtbot):
    from mikrocam.bridge.serial_transport import PortInfo
    from mikrocam.machine.controller import MachineController
    from mikrocam.machine.fake import FakeGRBL
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    fakes = []
    def controller_factory(_port):
        fake = FakeGRBL(machine_position=(0., 0., 5.))
        fakes.append(fake)
        return MachineController(fake)
    widget = MachinePanel(window, controller_factory=controller_factory,
                          ports_provider=lambda: (PortInfo('COM17', 'Fake only'),))
    qtbot.addWidget(widget)
    yield widget, fakes
    assert widget.shutdown()


def start_real_job(panel, source, report, qtbot):
    panel.load_preflight(source, report)
    qtbot.waitUntil(lambda: panel.job_controls.prepared_job is not None)
    panel.connect_machine()
    qtbot.waitUntil(lambda: panel.last_snapshot.job.can_start, timeout=3000)
    assert not panel.job_controls.confirm_checkbox.isChecked()
    panel.job_controls.confirm_checkbox.setChecked(True)
    panel.job_controls.start_button.click()
    assert not panel.job_controls.confirm_checkbox.isChecked()


def test_ten_real_qt_streaming_sessions_finish_and_release_both_owned_workers(real_panel, qtbot):
    panel, fakes = real_panel
    source, report = reviewed()
    for _ in range(10):
        start_real_job(panel, source, report, qtbot)
        qtbot.waitUntil(lambda: panel.last_snapshot.job.phase is JobPhase.COMPLETE, timeout=6000)
        observation = panel.last_snapshot.job
        assert observation.source_sha256 == source.sha256 and observation.acknowledged == observation.total
        assert panel.shutdown()
        assert panel._worker is None and panel._prepare_worker is None and not fakes[-1].is_open
        assert not panel.job_controls.confirm_checkbox.isChecked()


def test_real_pause_resume_with_pending_ack_then_stop_retains_identity_and_uncertainty(real_panel, qtbot):
    panel, fakes = real_panel
    source = SourceSnapshot('queued.nc', HEADER + '\n'.join(f'G1 X{i} F600' for i in range(1, 21)))
    report = analyze_gcode(source, setup())
    start_real_job(panel, source, report, qtbot)
    qtbot.waitUntil(lambda: bool(fakes) and fakes[-1]._job.pending_target is not None, timeout=6000)
    fake = fakes[-1]
    panel.job_controls.pause_button.click()
    qtbot.waitUntil(lambda: panel.last_snapshot.job.phase is JobPhase.PAUSED, timeout=4000)
    assert panel.job_controls.resume_button.isEnabled() and b'!' in fake.writes
    accepted = len(fake.job_writes)
    qtbot.wait(300)
    assert len(fake.job_writes) == accepted
    panel.job_controls.resume_button.click()
    qtbot.waitUntil(lambda: b'~' in fake.writes, timeout=2000)
    panel.job_controls.stop_button.click()
    qtbot.waitUntil(lambda: panel.last_snapshot.job.phase in (JobPhase.ABORTED, JobPhase.FAILED), timeout=2000)
    assert panel.last_snapshot.job.stop_unverified
    assert source.sha256 in panel.job_controls.progress_label.text()
    assert not panel.job_controls.start_button.isEnabled()
