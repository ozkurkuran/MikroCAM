"""Owned Qt communication threads and a read-only panel, using fake I/O only."""
from dataclasses import replace
from threading import Event, get_ident
from types import SimpleNamespace

import pytest
from PyQt6 import QtCore, QtWidgets
from PyQt6.sip import isdeleted

from mikrocam.bridge.machine import make_controller
from mikrocam.bridge.serial_transport import PortInfo
from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.models import ConnectionState, MachineSnapshot, MachineState
from mikrocam.ui.machine_panel import MachinePanel, open_machine_panel
from mikrocam.ui.machine_worker import MachineWorker


class ThreadCheckedFake(FakeGRBL):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calls = []

    def _record(self, name):
        assert QtCore.QThread.currentThread() != QtWidgets.QApplication.instance().thread()
        self.calls.append((name, get_ident()))

    def open(self):
        self._record('open')
        super().open()

    def read(self, size):
        self._record('read')
        return super().read(size)

    def write(self, data):
        self._record('write')
        return super().write(data)

    def close(self):
        self._record('close')
        super().close()


@pytest.fixture
def panel(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    transports = []
    factories = []

    def factory(port):
        assert port == 'COM17'
        assert QtCore.QThread.currentThread() != window.thread()
        factories.append(get_ident())
        fake = ThreadCheckedFake(status=b'<Idle|MPos:3,4,5|WCO:1,2,3>\n')
        transports.append(fake)
        return MachineController(fake)

    value = MachinePanel(window, controller_factory=factory,
                         ports_provider=lambda: (PortInfo('COM17', 'Simulated'),))
    window.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, value)
    yield value, transports, factories
    assert value.shutdown()


def test_construction_and_metadata_refresh_do_not_create_controller(panel):
    value, transports, factories = panel
    assert value.port_combo.currentData() == 'COM17'
    assert not factories and not transports and not value.busy
    assert not value.disconnect_button.isEnabled()
    assert all(label.text() == 'Unavailable' for label in value.machine_labels + value.work_labels)
    assert 'reset' in value.widget().findChildren(QtWidgets.QLabel)[0].text().lower()


def test_ten_owned_thread_sessions_and_no_duplicate_connect(panel, qtbot):
    value, transports, factories = panel
    for _ in range(10):
        value.connect_machine()
        worker = value._worker
        value.connect_machine()
        assert value._worker is worker
        assert not value.connect_button.isEnabled() and value.disconnect_button.isEnabled()
        qtbot.waitUntil(lambda: value.last_snapshot.machine_position_mm == (3., 4., 5.))
        assert tuple(label.text() for label in value.machine_labels) == ('3.000', '4.000', '5.000')
        assert tuple(label.text() for label in value.work_labels) == ('2.000', '2.000', '2.000')
        value.disconnect_machine()
        qtbot.waitUntil(lambda: not value.busy)
        assert isdeleted(worker) or not worker.isRunning()
        assert all(label.text() == 'Unavailable' for label in value.machine_labels + value.work_labels)
    assert len(transports) == len(factories) == 10
    for fake, thread_id in zip(transports, factories):
        assert not fake.is_open and fake.open_count == 1
        assert {identity for _, identity in fake.calls} == {thread_id}
        assert {name for name, _ in fake.calls} >= {'open', 'read', 'write', 'close'}
        assert set(fake.writes) <= {b'?', b'$$\n'}


def test_worker_stop_before_start_never_constructs_or_opens(qtbot):
    calls = []
    worker = MachineWorker(lambda: calls.append(True))
    snapshots = []
    worker.snapshot_ready.connect(snapshots.append)
    worker.stop()
    worker.start()
    qtbot.waitUntil(lambda: worker.isFinished())
    qtbot.waitUntil(lambda: bool(snapshots))
    assert not calls
    assert snapshots[-1].connection is ConnectionState.DISCONNECTED


def test_close_during_factory_cannot_open_after_stop(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    entered, release = Event(), Event()
    fake = ThreadCheckedFake()

    def factory(port):
        entered.set()
        release.wait(.15)
        return MachineController(fake)

    value = MachinePanel(window, controller_factory=factory,
                         ports_provider=lambda: (PortInfo('COM17', 'Simulated'),))
    value.connect_machine()
    qtbot.waitUntil(entered.is_set)
    assert value.close()
    assert not value.busy and fake.open_count == 0 and not fake.is_open
    release.set()


def test_shutdown_waits_for_bounded_read_and_closes_in_owner_thread(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    entered = Event()

    class BoundedReadFake(ThreadCheckedFake):
        def read(self, size):
            entered.set()
            Event().wait(.15)
            return super().read(size)

    fake = BoundedReadFake()
    value = MachinePanel(window, controller_factory=lambda port: MachineController(fake),
                         ports_provider=lambda: (PortInfo('COM17', 'Simulated'),))
    value.connect_machine()
    qtbot.waitUntil(entered.is_set)
    worker = value._worker
    assert value.shutdown()
    assert not value.busy and not fake.is_open
    assert isdeleted(worker) or not worker.isRunning()
    assert len({identity for _, identity in fake.calls}) == 1
    assert fake.calls[-1][0] == 'close'


def test_worker_preserves_io_error_after_finally_disconnect(qtbot):
    fake = ThreadCheckedFake()
    fake.read_error = OSError('simulated unplug')
    worker = MachineWorker(lambda: MachineController(fake))
    snapshots = []
    worker.snapshot_ready.connect(snapshots.append)
    worker.start()
    qtbot.waitUntil(lambda: worker.isFinished())
    qtbot.waitUntil(lambda: snapshots and snapshots[-1].connection is ConnectionState.ERROR)
    assert 'simulated unplug' in snapshots[-1].diagnostic
    assert snapshots[-1].machine_position_mm is None and not fake.is_open


def test_failed_close_during_stop_remains_error_until_explicit_acknowledgement(panel, qtbot):
    value, transports, _ = panel
    value.connect_machine()
    qtbot.waitUntil(lambda: value.last_snapshot.machine_position_mm is not None)
    worker = value._worker
    transports[-1].close_error = OSError('close rejected')
    value.disconnect_machine()
    qtbot.waitUntil(lambda: not value.busy)
    assert worker.final_snapshot.connection is ConnectionState.ERROR
    assert value.last_snapshot.connection is ConnectionState.ERROR
    assert 'close rejected' in value.status_label.text()
    assert value.disconnect_button.isEnabled()
    value.disconnect_machine()
    assert value.last_snapshot.connection is ConnectionState.DISCONNECTED


def test_finished_worker_is_joined_before_disposal(panel, qtbot, monkeypatch):
    value, _, _ = panel
    value.connect_machine()
    qtbot.waitUntil(lambda: value.last_snapshot.machine_position_mm is not None)
    worker = value._worker
    joined = []
    original_wait = worker.wait

    def wait(timeout):
        result = original_wait(timeout)
        joined.append(result)
        return result

    monkeypatch.setattr(worker, 'wait', wait)
    value.disconnect_machine()
    qtbot.waitUntil(lambda: not value.busy)
    assert joined and all(joined)


def test_factory_error_visible_and_reconnect_remains_possible(panel, qtbot):
    value, _, _ = panel

    def broken(port):
        raise OSError('factory unavailable')

    original = value.controller_factory
    value.controller_factory = broken
    value.connect_machine()
    qtbot.waitUntil(lambda: not value.busy)
    assert value.last_snapshot.connection is ConnectionState.ERROR
    assert 'factory unavailable' in value.status_label.text()
    assert value.connect_button.isEnabled()
    value.controller_factory = original
    value.connect_machine()
    qtbot.waitUntil(lambda: value.last_snapshot.machine_position_mm is not None)


def test_stale_unknown_units_and_unknown_state_are_truthful(panel, qtbot):
    value, _, _ = panel
    value.connect_machine()
    qtbot.waitUntil(lambda: value.last_snapshot.machine_position_mm is not None)
    worker = value._worker
    for kwargs in ({'stale': True}, {'report_units': None}):
        snapshot = replace(value.last_snapshot, **kwargs)
        worker.snapshot_ready.emit(snapshot)
        qtbot.waitUntil(lambda: value.last_snapshot == snapshot)
        assert all(label.text() == 'Unavailable' for label in value.machine_labels + value.work_labels)
    snapshot = replace(value.last_snapshot, state=MachineState.UNKNOWN, raw_state='Vendor:2')
    worker.snapshot_ready.emit(snapshot)
    qtbot.waitUntil(lambda: 'Vendor:2' in value.state_label.text())


def test_fresh_status_without_units_explains_unverified_positions(panel, qtbot):
    value, _, _ = panel
    value.connect_machine()
    qtbot.waitUntil(lambda: value.last_snapshot.machine_position_mm is not None)
    snapshot = replace(value.last_snapshot, report_units=None, stale=False, diagnostic='')
    value._worker.snapshot_ready.emit(snapshot)
    qtbot.waitUntil(lambda: value.last_snapshot == snapshot)
    assert 'units' in value.status_label.text().lower()
    assert 'unverified' in value.status_label.text().lower()


def test_old_sender_and_stopping_snapshots_do_not_repopulate(panel, qtbot):
    value, _, _ = panel
    value.connect_machine()
    qtbot.waitUntil(lambda: value.last_snapshot.machine_position_mm is not None)
    previous = value.last_snapshot
    old_worker = value._worker
    value.disconnect_machine()
    old_worker.snapshot_ready.emit(previous)
    qtbot.waitUntil(lambda: not value.busy)
    assert value.last_snapshot.machine_position_mm is None
    value.connect_machine()
    qtbot.waitUntil(lambda: value.last_snapshot.machine_position_mm is not None)
    alien = MachineWorker(lambda: None)
    alien.snapshot_ready.connect(value._receive_snapshot)
    alien.snapshot_ready.emit(replace(previous, machine_position_mm=(99., 99., 99.)))
    qtbot.wait(30)
    assert value.last_snapshot.machine_position_mm == (3., 4., 5.)


def test_snapshot_widgets_update_on_gui_thread(panel, qtbot, monkeypatch):
    value, _, _ = panel
    checked = []
    for label in (value.connection_label, value.state_label, value.status_label, *value.machine_labels):
        original = label.setText

        def set_text(text, original=original):
            assert QtCore.QThread.currentThread() == value.thread()
            checked.append(text)
            original(text)

        monkeypatch.setattr(label, 'setText', set_text)
    value.connect_machine()
    qtbot.waitUntil(lambda: value.last_snapshot.machine_position_mm is not None)
    assert checked


def test_no_ports_and_metadata_failure_leave_connect_disabled(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    value = MachinePanel(window, ports_provider=lambda: ())
    assert not value.connect_button.isEnabled()

    def unavailable():
        raise OSError('metadata unavailable')

    value.ports_provider = unavailable
    value.refresh_ports()
    assert 'metadata unavailable' in value.status_label.text()
    assert not value.connect_button.isEnabled()


def test_shutdown_timeout_keeps_live_worker_and_ignores_close(panel, qtbot, monkeypatch):
    value, _, _ = panel
    value.connect_machine()
    qtbot.waitUntil(lambda: value.last_snapshot.machine_position_mm is not None)
    worker = value._worker
    original_wait = worker.wait
    monkeypatch.setattr(worker, 'wait', lambda timeout: False)
    assert not value.shutdown()
    assert value._worker is worker and value.busy
    assert not value.close()
    monkeypatch.setattr(worker, 'wait', original_wait)
    qtbot.waitUntil(lambda: not worker.isRunning())
    assert value.shutdown()


def test_singleton_open_never_connects_and_bridge_factory_is_inert(qtbot, monkeypatch):
    import mikrocam.bridge.machine as bridge
    import mikrocam.ui.machine_panel as panel_module
    created = []
    monkeypatch.setattr(bridge, 'SerialIO', lambda port: created.append(port) or FakeGRBL())
    controller = make_controller('COM17')
    assert created == ['COM17'] and controller.snapshot().connection is ConnectionState.DISCONNECTED
    monkeypatch.setattr(panel_module, 'list_ports', lambda: ())
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    app = SimpleNamespace(ui=window)
    first = open_machine_panel(app)
    assert open_machine_panel(app) is first and not first.busy
    assert app._mikrocam_machine_panel is first
    assert first.shutdown()
