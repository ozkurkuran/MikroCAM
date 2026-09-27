"""Fixed typed manual controls and GUI/worker admission, without physical devices."""
from dataclasses import replace
from threading import get_ident

import pytest
from PyQt6 import QtCore, QtWidgets

from mikrocam.bridge.serial_transport import PortInfo
from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.manual_models import JogRequest, SelectG54Request, ZeroRequest
from mikrocam.machine.models import (ConnectionState, MachineSnapshot, MachineState,
                                    ManualObservation, ManualPhase)
from mikrocam.ui.machine_controls import MachineManualControls
from mikrocam.ui.machine_panel import MachinePanel


def ready():
    return MachineSnapshot(connection=ConnectionState.CONNECTED, state=MachineState.IDLE,
                           raw_state='Idle', machine_position_mm=(0.,0.,0.), work_position_mm=(0.,0.,0.),
                           report_units='mm', stale=False,
                           manual=ManualObservation(can_jog=True, can_zero=True, can_select_g54=True))


@pytest.fixture
def controls(qtbot):
    value = MachineManualControls()
    qtbot.addWidget(value)
    return value


def test_presets_defaults_no_repeating_keys_or_raw_text(controls):
    assert tuple(controls.step_combo.itemData(i) for i in range(3)) == (.1, 1., 10.)
    assert tuple(controls.feed_combo.itemData(i) for i in range(3)) == (100., 300., 600.)
    assert controls.step_combo.currentData() == .1 and controls.feed_combo.currentData() == 100.
    assert not controls.step_combo.isEditable() and not controls.feed_combo.isEditable()
    assert len(controls.jog_buttons) == 6
    assert not any(button.autoRepeat() for button in controls.findChildren(QtWidgets.QPushButton))
    assert not controls.findChildren(QtWidgets.QLineEdit)
    assert not any(button.isEnabled() for button in controls.jog_buttons.values())
    help_text = ' '.join(label.text().lower() for label in controls.findChildren(QtWidgets.QLabel))
    for word in ('persistent', 'outputs', 'startup', 'parking', 'physical'):
        assert word in help_text


def test_every_control_emits_only_bounded_typed_intent(controls):
    controls.set_snapshot(ready(), True)
    received = []
    controls.requested.connect(received.append)
    controls.step_combo.setCurrentIndex(2)
    controls.feed_combo.setCurrentIndex(1)
    for (axis, sign), button in controls.jog_buttons.items():
        button.click()
        assert received[-1] == JogRequest(axis, sign*10., 300.)
    controls.select_g54_button.click()
    assert received[-1] == SelectG54Request()
    for label, button in controls.zero_buttons.items():
        button.click()
        assert received[-1] == ZeroRequest(tuple(label))


@pytest.mark.parametrize('phase', [ManualPhase.PREPARING, ManualPhase.MOVING,
                                  ManualPhase.VERIFYING, ManualPhase.CANCELLING])
def test_observation_flags_lock_new_actions_but_priority_stop_remains(controls, phase):
    snapshot = replace(ready(), manual=ManualObservation(phase=phase, action='jog', can_cancel=True))
    controls.set_snapshot(snapshot, True)
    assert not controls.select_g54_button.isEnabled()
    assert not any(button.isEnabled() for button in controls.jog_buttons.values())
    assert not any(button.isEnabled() for button in controls.zero_buttons.values())
    assert controls.cancel_button.isEnabled() and controls.abort_button.isEnabled()
    controls.set_pending()
    assert controls.cancel_button.isEnabled() and controls.abort_button.isEnabled()


def test_pending_admission_survives_identical_old_ready_snapshot(controls):
    controls.set_snapshot(ready(), True)
    controls.set_pending()
    controls.set_snapshot(replace(ready(), last_report_at=1.), True)
    assert not any(button.isEnabled() for button in controls.jog_buttons.values())
    assert 'pending' in controls.operation_label.text().lower()
    controls.set_snapshot(replace(ready(), manual=ManualObservation(phase=ManualPhase.COMPLETE,
                          action='jog', can_jog=True)), True)
    assert all(button.isEnabled() for button in controls.jog_buttons.values())


def test_disconnected_or_absent_worker_disables_every_manual_control(controls):
    for snapshot, worker_available in ((MachineSnapshot(), True), (ready(), False)):
        controls.set_snapshot(snapshot, worker_available)
        assert not any(button.isEnabled() for button in controls.findChildren(QtWidgets.QPushButton))


def test_uncertain_stop_diagnostic_is_visible(controls):
    controls.set_snapshot(replace(ready(), manual=ManualObservation(phase=ManualPhase.ABORTED,
                          diagnostic='Possible parking', stop_unverified=True)), True)
    text = controls.operation_label.text().lower()
    assert 'unverified' in text and 'parking' in text


class IntentWorker(QtCore.QObject):
    snapshot_ready = QtCore.pyqtSignal(object)

    def __init__(self, accepts=True):
        super().__init__()
        self.accepts = accepts
        self.requests = []
        self.cancelled = self.aborted = 0

    def submit(self, request):
        self.requests.append(request)
        return self.accepts

    def cancel_jog(self):
        self.cancelled += 1

    def abort(self):
        self.aborted += 1


def test_panel_submits_once_and_disables_immediately_and_rejection_is_visible(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    panel = MachinePanel(window, ports_provider=lambda: ())
    worker = IntentWorker()
    panel._worker = worker
    panel.last_snapshot = ready()
    panel._render_snapshot()
    panel.manual_controls.jog_buttons[('X', 1)].click()
    panel.manual_controls.jog_buttons[('X', 1)].click()
    assert worker.requests == [JogRequest('X', .1, 100.)]
    assert not panel.manual_controls.select_g54_button.isEnabled()
    panel.manual_controls.abort_button.click()
    assert worker.aborted == 1
    panel._worker = None
    panel._render_snapshot()
    panel.submit_manual(JogRequest('X', .1, 100.))
    assert 'rejected' in panel.status_label.text().lower()
    worker.accepts = False
    panel._worker = worker
    panel.submit_manual(JogRequest('X', .1, 100.))
    assert 'rejected' in panel.status_label.text().lower()
    panel._worker = None


class OwnedFake(FakeGRBL):
    def __init__(self):
        super().__init__()
        self.thread_ids = set()

    def _owner(self):
        assert QtCore.QThread.currentThread() != QtWidgets.QApplication.instance().thread()
        self.thread_ids.add(get_ident())

    def open(self):
        self._owner()
        super().open()

    def read(self, size):
        self._owner()
        return super().read(size)

    def write(self, data):
        self._owner()
        return super().write(data)

    def close(self):
        self._owner()
        super().close()


@pytest.fixture
def live_panel(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    fakes = []

    def factory(port):
        fake = OwnedFake()
        fakes.append(fake)
        return MachineController(fake)

    panel = MachinePanel(window, controller_factory=factory,
                         ports_provider=lambda: (PortInfo('COM17', 'Fake'),))
    yield panel, fakes
    assert panel.shutdown()


def test_ten_real_worker_fake_action_sessions_keep_io_and_widgets_owned(live_panel, qtbot, monkeypatch):
    panel, fakes = live_panel
    original = panel.manual_controls.set_snapshot

    def render(snapshot, worker_available):
        assert QtCore.QThread.currentThread() == panel.thread()
        original(snapshot, worker_available)

    monkeypatch.setattr(panel.manual_controls, 'set_snapshot', render)
    for _ in range(10):
        panel.connect_machine()
        qtbot.waitUntil(lambda: panel.manual_controls.jog_buttons[('X', 1)].isEnabled())
        panel.manual_controls.jog_buttons[('X', 1)].click()
        assert not panel.manual_controls.jog_buttons[('X', 1)].isEnabled()
        qtbot.waitUntil(lambda: panel.last_snapshot.manual.phase is ManualPhase.COMPLETE, timeout=6000)
        assert panel.last_snapshot.machine_position_mm[0] == pytest.approx(.1)
        panel.manual_controls.zero_buttons['XY'].click()
        qtbot.waitUntil(lambda: b'G10 L20 P1 X0 Y0\n' in fakes[-1].writes, timeout=6000)
        qtbot.waitUntil(lambda: panel.last_snapshot.manual.phase is ManualPhase.COMPLETE
                       and panel.last_snapshot.manual.action == 'zero', timeout=6000)
        assert panel.last_snapshot.work_position_mm[:2] == pytest.approx((0.,0.))
        assert panel.shutdown() and not panel.busy
    assert len(fakes) == 10
    assert all(not fake.is_open and len(fake.thread_ids) == 1 for fake in fakes)


def test_cancel_and_close_during_owned_motion_send_priority_bytes(live_panel, qtbot):
    panel, fakes = live_panel
    panel.connect_machine()
    qtbot.waitUntil(lambda: panel.manual_controls.jog_buttons[('X', 1)].isEnabled())
    panel.manual_controls.jog_buttons[('X', 1)].click()
    qtbot.waitUntil(lambda: panel.last_snapshot.manual.phase is ManualPhase.MOVING, timeout=6000)
    panel.manual_controls.cancel_button.click()
    qtbot.waitUntil(lambda: b'\x85' in fakes[-1].writes)
    qtbot.waitUntil(lambda: panel.last_snapshot.manual.can_jog, timeout=6000)
    panel.manual_controls.jog_buttons[('Y', 1)].click()
    qtbot.waitUntil(lambda: panel.last_snapshot.manual.phase is ManualPhase.MOVING, timeout=6000)
    assert panel.shutdown() and not panel.busy and not fakes[-1].is_open
    assert fakes[-1].writes.count(b'\x85') == 2


def test_connect_caveat_discloses_configured_startup_blocks(live_panel):
    panel, _ = live_panel
    help_text = ' '.join(label.text().lower() for label in panel.findChildren(QtWidgets.QLabel))
    assert 'reset' in help_text and 'configured startup blocks' in help_text


def test_failed_stop_through_shutdown_retains_unverified_operation(live_panel, qtbot):
    panel, fakes = live_panel
    panel.connect_machine()
    qtbot.waitUntil(lambda: panel.manual_controls.jog_buttons[('X', 1)].isEnabled())
    panel.manual_controls.jog_buttons[('X', 1)].click()
    qtbot.waitUntil(lambda: panel.last_snapshot.manual.phase is ManualPhase.MOVING, timeout=6000)
    fakes[-1].write_error = OSError('stop delivery lost')
    assert panel.shutdown()
    assert panel.last_snapshot.manual.stop_unverified
    assert 'unverified' in panel.manual_controls.operation_label.text().lower()
    assert all(label.text() == 'Unavailable' for label in panel.machine_labels + panel.work_labels)
