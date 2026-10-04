"""Thin firmware presentation on the Machine panel (spec 042, FR-013)."""
import pytest
from PyQt6 import QtCore, QtWidgets

from mikrocam.bridge.serial_transport import PortInfo
from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.firmware import (FirmwareObservation, IdentificationPhase, identify)
from mikrocam.ui.machine_firmware import describe_firmware, firmware_details
from mikrocam.ui.machine_panel import MachinePanel


def test_descriptions_for_each_phase_and_family():
    assert describe_firmware(FirmwareObservation()) == 'Not identified'
    assert describe_firmware(FirmwareObservation(IdentificationPhase.PENDING)) == 'Identifying…'
    grbl = FirmwareObservation(IdentificationPhase.IDENTIFIED,
                               identify('', ('[VER:1.1h.20190830:]', '[OPT:V,15,128]')))
    text = describe_firmware(grbl)
    assert text.startswith('GRBL 1.1h (build 20190830)')
    assert 'RX 128 B' in text and 'char-counting budget 128 B' in text and 'motion enabled' in text
    hal = FirmwareObservation(IdentificationPhase.IDENTIFIED, identify(
        "GrblHAL 1.1f ['$' or '$HELP' for help]", ('[VER:1.1f.20240101:]', '[OPT:VN,35,1024]')))
    text = describe_firmware(hal)
    assert text.startswith('grblHAL 1.1f') and 'motion disabled' in text and 'axis count' in text
    fnc = FirmwareObservation(IdentificationPhase.IDENTIFIED, identify(
        '', ('[VER:4.1 FluidNC v4.1.1 (esp32-wifi) :]', '[OPT:PHSEW]')))
    assert describe_firmware(fnc).startswith('FluidNC 4.1.1') and 'RX unknown' in describe_firmware(fnc)
    failed = FirmwareObservation(IdentificationPhase.FAILED, identify('', ()), diagnostic='No reply')
    assert describe_firmware(failed).startswith('Unknown') and 'motion disabled' in describe_firmware(failed)
    details = firmware_details(hal)
    assert '0x87 full-status' in details and 'Tool' in details


@pytest.fixture
def panel(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    fakes = []

    def factory(port):
        fakes.append(FakeGRBL(firmware=port))
        return MachineController(fakes[-1])

    value = MachinePanel(window, controller_factory=factory,
                         ports_provider=lambda: (PortInfo('grbl', 'GRBL'), PortInfo('grblhal', 'HAL')))
    window.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, value)
    yield value, fakes, qtbot
    assert value.shutdown()


@pytest.mark.parametrize('profile,prefix,enabled', [('grbl', 'GRBL 1.1h', True),
                                                    ('grblhal', 'grblHAL 1.1f', True)])
def test_panel_shows_firmware_and_motion_controls_follow_capability(panel, profile, prefix, enabled):
    value, fakes, qtbot = panel
    assert value.firmware_label.text() == 'Not identified'
    value.port_combo.setCurrentIndex(value.port_combo.findData(profile))
    value.connect_machine()
    qtbot.waitUntil(lambda: value.firmware_label.text().startswith(prefix), timeout=5000)
    qtbot.waitUntil(lambda: value.last_snapshot.machine_position_mm is not None, timeout=5000)
    button = value.manual_controls.jog_buttons[('X', 1)]
    if enabled:
        qtbot.waitUntil(button.isEnabled, timeout=5000)
    else:
        qtbot.wait(300)
        assert not button.isEnabled()
    assert value.firmware_label.toolTip()
    value.disconnect_machine()
    qtbot.waitUntil(lambda: not value.busy, timeout=5000)
    assert value.firmware_label.text() == 'Not identified'


def test_status_tooltip_explains_alarm_codes_per_family():
    from mikrocam.ui.machine_firmware import controller_code_hint
    hal = FirmwareObservation(IdentificationPhase.IDENTIFIED, identify(
        "GrblHAL 1.1f ['$' or '$HELP' for help]", ('[VER:1.1f.20240101:]', '[OPT:VN,35,1024,3,0]',
                                                     '[NEWOPT:ENUMS,RT+]', '[FIRMWARE:grblHAL]')))
    grbl = FirmwareObservation(IdentificationPhase.IDENTIFIED,
                               identify('', ('[VER:1.1h.20190830:]', '[OPT:V,15,128]')))
    assert 'E-stop' in controller_code_hint('ALARM:10', '', hal)
    assert 'dual-axis' in controller_code_hint('ALARM:10', '', grbl)
    assert 'Homing required' in controller_code_hint('', 'Alarm:11', hal)
    assert controller_code_hint('Status is stale', 'Idle', grbl) == ''


def test_panel_status_tooltip_follows_grblhal_alarm(panel):
    value, fakes, qtbot = panel
    value.port_combo.setCurrentIndex(value.port_combo.findData('grblhal'))
    value.connect_machine()
    qtbot.waitUntil(lambda: value.last_snapshot.firmware.motion_allowed, timeout=5000)
    fakes[-1].status = b'<Alarm:10|MPos:0.000,0.000,0.000|FS:0,0>\r\n'
    fakes[-1].inject(b'ALARM:10\r\n')
    qtbot.waitUntil(lambda: 'E-stop' in value.status_label.toolTip(), timeout=5000)
    value.disconnect_machine()
    qtbot.waitUntil(lambda: not value.busy, timeout=5000)
