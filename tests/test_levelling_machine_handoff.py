"""Single-owner GRBL handoff, with mocks and an inert Qt dock only."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import importlib

import pytest
from PyQt6 import QtWidgets

from appGUI.GUIElements import FCComboBox
from appPlugins.ToolLevelling import ToolLevelling
from mikrocam.bridge.serial_transport import PortInfo
from mikrocam.ui.machine_panel import open_machine_panel

levelling = importlib.import_module("appPlugins.ToolLevelling")


@pytest.fixture
def tool(qapp):
    value = ToolLevelling.__new__(ToolLevelling)
    value.app = MagicMock()
    value.ui = MagicMock()
    value.ui.al_controller_combo.get_value.return_value = "GRBL"
    value.grbl_ser_port = MagicMock()
    return value


@pytest.mark.parametrize("name,args", [
    ("on_grbl_connect", ()), ("on_grbl_wake", ()), ("on_grbl_send_command", ()),
    ("send_grbl_command", ("G1 X1",)), ("send_grbl_block", ("G1 X1",)),
    ("_send_grbl_probe_command", ("G38.2 Z-1 F10",)),
    ("on_grbl_get_parameter", ("10",)), ("on_grbl_jog", ("xplus",)),
    ("on_grbl_zero", ("x",)), ("on_grbl_homing", ()),
    ("send_grbl_realtime", (b"!",)), ("on_grbl_reset", ()),
    ("on_grbl_pause_resume", (True,)), ("on_grbl_autolevel", ()),
])
def test_grbl_callbacks_cannot_open_write_read_or_schedule(tool, monkeypatch, name, args):
    serial_url = MagicMock(side_effect=AssertionError("port open attempted"))
    serial_class = MagicMock(side_effect=AssertionError("serial constructor attempted"))
    monkeypatch.setattr(levelling.serial, "serial_for_url", serial_url)
    monkeypatch.setattr(levelling.serial, "Serial", serial_class)
    getattr(tool, name)(*args)
    serial_url.assert_not_called()
    serial_class.assert_not_called()
    assert not tool.grbl_ser_port.mock_calls
    tool.app.worker_task.emit.assert_not_called()
    assert tool.app.inform.emit.call_args.args[0].startswith("[WARNING_NOTCL]")


def test_public_connect_is_disabled_for_offline_controller_too(tool, monkeypatch):
    tool.ui.al_controller_combo.get_value.return_value = "MACH3"
    factory = MagicMock()
    monkeypatch.setattr(levelling.serial, "serial_for_url", factory)
    tool.on_grbl_connect()
    factory.assert_not_called()
    assert not tool.grbl_ser_port.mock_calls


def test_search_uses_metadata_never_probe_opens(tool, monkeypatch):
    metadata = MagicMock(return_value=(PortInfo("COM_TEST", "Mock metadata"),))
    monkeypatch.setattr("mikrocam.bridge.serial_transport.list_ports", metadata)
    factory = MagicMock(side_effect=AssertionError("serial open attempted"))
    monkeypatch.setattr(levelling.serial, "Serial", factory)
    assert tool.on_grbl_list_serial_ports() == ["COM_TEST"]
    factory.assert_not_called()


def qt_tool(qapp):
    value = ToolLevelling.__new__(ToolLevelling)
    main = QtWidgets.QMainWindow()
    value.app = SimpleNamespace(ui=main)
    frame = QtWidgets.QFrame()
    value.layout = QtWidgets.QVBoxLayout(frame)
    controller_frame = QtWidgets.QFrame(frame)
    QtWidgets.QGridLayout(controller_frame)
    value.layout.addWidget(controller_frame)
    combo = FCComboBox()
    combo.addItems(["MACH3", "MACH4", "LinuxCNC", "GRBL"])
    old = QtWidgets.QFrame(controller_frame)
    controller_frame.layout().addWidget(old, 2, 0)
    value.ui = SimpleNamespace(c_frame=controller_frame, grbl_frame=old, al_controller_combo=combo,
                              h_gcode_button=QtWidgets.QPushButton(),
                              view_h_gcode_button=QtWidgets.QPushButton(),
                              import_heights_button=QtWidgets.QPushButton())
    value.on_grbl_search_ports = MagicMock()
    return value, main, frame


@pytest.mark.parametrize("offline", ["MACH3", "MACH4", "LinuxCNC"])
def test_controller_switches_restore_offline_controls_without_search(qapp, offline):
    value, main, frame = qt_tool(qapp)
    for _ in range(3):
        value.ui.al_controller_combo.set_value("GRBL")
        value.on_controller_change_alter_ui()
        assert value.ui.grbl_frame.isHidden() and not value.ui.grbl_frame.isEnabled()
        assert not value.ui.machine_handoff.isHidden()
        assert value.ui.h_gcode_button.isHidden()
        value.ui.al_controller_combo.set_value(offline)
        value.on_controller_change_alter_ui()
        assert value.ui.machine_handoff.isHidden()
        assert not value.ui.h_gcode_button.isHidden()
        assert not value.ui.view_h_gcode_button.isHidden()
        assert not value.ui.import_heights_button.isHidden()
    value.on_grbl_search_ports.assert_not_called()
    frame.close()
    main.close()


def test_button_reuses_existing_machine_panel_without_connect(qapp):
    value, main, frame = qt_tool(qapp)
    panel = open_machine_panel(value.app)
    panel.connect_machine = MagicMock(side_effect=AssertionError("implicit connect"))
    value.ui.al_controller_combo.set_value("GRBL")
    value.on_controller_change_alter_ui()
    panel.hide()
    value.ui.machine_handoff_button.click()
    assert value.app._mikrocam_machine_panel is panel and not panel.isHidden()
    assert panel._worker is None
    panel.connect_machine.assert_not_called()
    panel.close()
    frame.close()
    main.close()


def test_handoff_stays_enabled_without_eligible_legacy_cnc_job(qapp):
    value, main, frame = qt_tool(qapp)
    value.ui.c_frame.setEnabled(False)
    value.ui.al_controller_combo.set_value("GRBL")
    value.on_controller_change_alter_ui()
    assert value.ui.machine_handoff_button.isEnabled()
    value.ui.machine_handoff_button.click()
    assert value.app._mikrocam_machine_panel._worker is None
    value.app._mikrocam_machine_panel.close()
    frame.close()
    main.close()
