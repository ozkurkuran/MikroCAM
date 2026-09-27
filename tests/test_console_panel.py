"""Console integration reuses the existing owner and retains terminal evidence."""
from dataclasses import replace
from types import SimpleNamespace

import pytest
from PyQt6 import QtCore, QtWidgets
from PyQt6.sip import isdeleted

from mikrocam.machine.console_models import ConsoleObservation, ConsolePhase, ConsoleRequest
from mikrocam.machine.models import ConnectionState, MachineSnapshot
from mikrocam.machine.wire_log import WireRecord, WireSnapshot
from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.bridge.serial_transport import PortInfo
from mikrocam.ui.machine_panel import MachinePanel


@pytest.fixture
def panel(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    value = MachinePanel(window, controller_factory=lambda: pytest.fail('No controller expected'),
                         ports_provider=lambda: ())
    window.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, value)
    yield value
    value._worker = None
    assert value.shutdown()


def terminal_snapshot():
    return MachineSnapshot(connection=ConnectionState.ERROR,
                           console=ConsoleObservation(ConsolePhase.FAILED, '$I', 'Read failed'),
                           wire=WireSnapshot((WireRecord(1, 1., 'TX', b'$I\n', 'complete'),)))


def test_panel_is_inert_and_routes_typed_console_to_same_owner(panel):
    assert not panel.busy
    assert not panel.console_controls.toggle_button.isChecked()
    requests = []
    panel._worker = SimpleNamespace(submit=lambda request: requests.append(request) or True)
    panel.last_snapshot = MachineSnapshot(connection=ConnectionState.CONNECTED,
                                          console=ConsoleObservation(can_query=True))
    panel._render_snapshot()
    panel.console_controls.query_combo.setCurrentText('$I')
    panel.console_controls.send_button.click()
    assert requests == [ConsoleRequest('$I')]
    assert not panel.console_controls.send_button.isEnabled()


@pytest.mark.parametrize('mode', ['unavailable', 'occupied', 'invalid', 'stopping'])
def test_rejected_submission_is_visible_without_raw_io(panel, mode):
    def submit(request):
        assert isinstance(request, ConsoleRequest)
        if mode == 'invalid':
            raise ValueError('Owner denied query')
        return False

    panel._worker = None if mode == 'unavailable' else SimpleNamespace(submit=submit)
    panel._stopping = mode == 'stopping'
    panel.submit_console(ConsoleRequest('$I'))
    assert 'rejected' in panel.console_controls.diagnostic_label.text().lower()


def test_disconnect_without_worker_retains_final_query_and_wire(panel):
    final = terminal_snapshot()
    panel.last_snapshot = final
    panel._render_snapshot()
    panel.disconnect_machine()
    assert panel.last_snapshot.connection is ConnectionState.DISCONNECTED
    assert panel.last_snapshot.console == final.console
    assert panel.last_snapshot.wire == final.wire
    assert "b'$I\\n'" in panel.console_controls.log_view.toPlainText()
    assert 'Read failed' in panel.console_controls.diagnostic_label.text()


def test_disconnect_pending_close_keeps_evidence_and_disables_query(panel):
    calls = []
    panel._worker = SimpleNamespace(stop=lambda: calls.append('stop'))
    final = terminal_snapshot()
    panel.last_snapshot = final
    panel.disconnect_machine()
    assert calls == ['stop']
    assert panel.last_snapshot.console == final.console
    assert panel.last_snapshot.wire == final.wire
    assert not panel.console_controls.send_button.isEnabled()


def test_release_uses_final_owner_snapshot_without_erasing_failure(panel):
    final = terminal_snapshot()
    calls = []
    panel._worker = SimpleNamespace(wait=lambda timeout: True, final_snapshot=final,
                                    deleteLater=lambda: calls.append('deleted'))
    panel._release_worker()
    assert calls == ['deleted'] and not panel.busy
    assert panel.last_snapshot is final
    assert 'Read failed' in panel.console_controls.diagnostic_label.text()
    assert "b'$I\\n'" in panel.console_controls.log_view.toPlainText()


def test_new_connecting_session_resets_only_local_view(panel):
    final = terminal_snapshot()
    panel.last_snapshot = final
    panel._render_snapshot()
    panel.console_controls.clear_button.click()
    panel.last_snapshot = MachineSnapshot(connection=ConnectionState.CONNECTING)
    panel._render_snapshot()
    panel.last_snapshot = replace(final, connection=ConnectionState.DISCONNECTED)
    panel._render_snapshot()
    assert "b'$I\\n'" in panel.console_controls.log_view.toPlainText()


def test_live_owner_queries_and_ten_reconnects_keep_final_log(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    fakes = []

    def factory(port):
        assert port == 'COM17'
        assert QtCore.QThread.currentThread() != window.thread()
        fake = FakeGRBL()
        fakes.append(fake)
        return MachineController(fake)

    panel = MachinePanel(window, controller_factory=factory,
                         ports_provider=lambda: (PortInfo('COM17', 'Fake'),))
    window.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, panel)
    try:
        for _ in range(10):
            panel.connect_machine()
            worker = panel._worker
            qtbot.waitUntil(lambda: panel.console_controls.send_button.isEnabled(), timeout=4000)
            for command in ('?', '$$', '$G', '$#', '$N', '$I'):
                panel.console_controls.query_combo.setCurrentText(command)
                panel.console_controls.send_button.click()
                qtbot.waitUntil(lambda: panel.last_snapshot.console.phase is ConsolePhase.COMPLETE
                                 and panel.last_snapshot.console.command == command, timeout=4000)
                assert panel.console_controls.send_button.isEnabled()
                assert QtCore.QThread.currentThread() == panel.console_controls.thread()
            assert '[VER:' in panel.console_controls.log_view.toPlainText()
            panel.disconnect_machine()
            qtbot.waitUntil(lambda: not panel.busy, timeout=4000)
            assert isdeleted(worker) or not worker.isRunning()
            assert '[VER:' in panel.console_controls.log_view.toPlainText()
            assert panel.last_snapshot.console.command == '$I'
            panel.console_controls.clear_button.click()
            assert '[VER:' not in panel.console_controls.log_view.toPlainText()
        assert all(fake.open_count == 1 and not fake.is_open for fake in fakes)
    finally:
        assert panel.shutdown()
