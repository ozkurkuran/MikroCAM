"""Legacy GRBL wire regressions; mock serial only."""
import importlib
from unittest.mock import MagicMock

import pytest
from PyQt6 import QtWidgets

_qapp = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

from appPlugins.ToolLevelling import ToolLevelling

levelling = importlib.import_module("appPlugins.ToolLevelling")


@pytest.fixture
def tool(monkeypatch):
    obj = ToolLevelling.__new__(ToolLevelling)
    obj.app = MagicMock()
    obj.app.options = {}
    obj.ui = MagicMock()
    obj.ui.com_list_combo.currentText.return_value = "COM_TEST"
    obj.ui.baudrates_list_combo.currentText.return_value = "115200"
    obj.ui.al_toolbar.count.return_value = 0
    obj.units = "MM"
    # Isolated mock-only retained wire behavior; runtime connection stays blocked.
    obj.ui.al_controller_combo.get_value.return_value = "MACH3"
    obj.on_grbl_connect = obj._legacy_on_grbl_connect
    # Bypass runtime guards explicitly in this mock-only retained implementation test.
    for name in dir(ToolLevelling):
        method = getattr(ToolLevelling, name)
        if callable(method) and hasattr(method, '__wrapped__'):
            setattr(obj, name, method.__wrapped__.__get__(obj, ToolLevelling))
    obj.grbl_ser_port = MagicMock()
    monkeypatch.setattr(levelling.serial, "serial_for_url",
                        MagicMock(return_value=obj.grbl_ser_port))
    monkeypatch.setattr(levelling.time, "sleep", lambda _: None)
    return obj


@pytest.mark.parametrize("reply,connected", [
    ([], False),
    ([b"Grbl 1.1h ['$' for help]\r\n"], True),
    ([b"ok\r\n"], True),
    ([b"random bytes\xff\r\n"], False),
    ([b"not ok\r\n"], False),
])
def test_connect_requires_real_grbl_response(tool, reply, connected):
    tool.grbl_ser_port.readlines.return_value = reply
    tool.on_grbl_connect()
    if connected:
        tool.ui.com_connect_button.setText.assert_called_once_with("Connected")
        tool.grbl_ser_port.close.assert_not_called()
    else:
        tool.grbl_ser_port.close.assert_called_once()
        assert tool.app.inform.emit.call_args.args[0].startswith("[ERROR_NOTCL]")
        tool.ui.com_connect_button.setText.assert_not_called()


def test_wake_decodes_bytes_with_replacement(tool):
    tool.grbl_ser_port.readlines.return_value = [b"ok\r\n", b"bad\xff\n"]
    assert tool.on_grbl_wake() == ["ok", "bad\ufffd"]


@pytest.mark.parametrize("reply,expected", [
    ([], ""), ([b"ok\r\n"], "ok"),
    ([b"first\n", b"bad\xff\n", b"ok\n"], "first\nbad\ufffd\nok"),
])
def test_command_returns_text(tool, reply, expected):
    tool.grbl_ser_port.readlines.return_value = reply
    result = tool.send_grbl_command("$G", echo=False)
    assert isinstance(result, str)
    assert result == expected
    tool.grbl_ser_port.write.assert_called_once_with(b"$G\n")


def test_probe_returns_text_on_result(tool, monkeypatch):
    monkeypatch.setattr(levelling.time, "monotonic", lambda: 0.0)
    tool.grbl_ser_port.readline.side_effect = [b"ok\n", b"[PRB:1,2,3:1]\n"]
    result = tool._send_grbl_probe_command("G38.2 Z-1 F10", echo=False)
    assert isinstance(result, str)
    assert result == "ok\n[PRB:1,2,3:1]"


def test_probe_returns_none_on_timeout(tool, monkeypatch):
    ticks = iter([0.0, 0.0, 10.1])
    monkeypatch.setattr(levelling.time, "monotonic", lambda: next(ticks))
    tool.grbl_ser_port.readline.return_value = b""
    assert tool._send_grbl_probe_command("G38.2 Z-1 F10", echo=False) is None
    assert tool.app.inform.emit.call_args.args[0].startswith("[ERROR_NOTCL]")


@pytest.mark.parametrize("direction,axis", [
    ("xplus", "X5.0"), ("xminus", "X-5.0"),
    ("yplus", "Y5.0"), ("yminus", "Y-5.0"),
    ("zplus", "Z5.0"), ("zminus", "Z-5.0"),
])
def test_jog_writes_numeric_step(tool, direction, axis):
    tool.ui.jog_step_entry.get_value.return_value = "5"
    tool.ui.jog_fr_entry.get_value.return_value = "100"
    tool.on_grbl_jog(direction)
    tool.grbl_ser_port.write.assert_called_once_with(
        f"$J=G91 G21 {axis} F100.0\n".encode())


@pytest.mark.parametrize("entry", ["jog_step_entry", "jog_fr_entry"])
@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), "bad", None])
def test_jog_rejects_invalid_step_or_feed(tool, entry, value):
    tool.ui.jog_step_entry.get_value.return_value = 5
    tool.ui.jog_fr_entry.get_value.return_value = 100
    getattr(tool.ui, entry).get_value.return_value = value
    tool.on_grbl_jog("xplus")
    tool.grbl_ser_port.write.assert_not_called()
    assert tool.app.inform.emit.call_args.args[0].startswith("[ERROR_NOTCL]")


@pytest.mark.parametrize("axis,command", [
    ("x", b"G10 L20 P1 X0\n"), ("y", b"G10 L20 P1 Y0\n"),
    ("z", b"G10 L20 P1 Z0\n"), ("all", b"G10 L20 P1 X0 Y0 Z0\n"),
])
def test_zero_uses_current_position_without_changing_settings(tool, axis, command):
    tool.on_grbl_get_parameter = MagicMock(return_value=3)
    tool.on_grbl_zero(axis)
    tool.grbl_ser_port.write.assert_called_once_with(command)
    tool.on_grbl_get_parameter.assert_not_called()


@pytest.mark.parametrize("checked,command", [(True, b"!"), (False, b"~")])
def test_pause_resume_writes_only_realtime_byte(tool, checked, command):
    tool.on_grbl_pause_resume(checked)
    tool.grbl_ser_port.write.assert_called_once_with(command)
    tool.grbl_ser_port.readlines.assert_not_called()


@pytest.mark.parametrize("command", [b"?", b"!", b"~", b"\x18"])
def test_realtime_allowed_bytes_do_not_read(tool, command):
    tool.send_grbl_realtime(command)
    tool.grbl_ser_port.write.assert_called_once_with(command)
    tool.grbl_ser_port.readlines.assert_not_called()


@pytest.mark.parametrize("command", [b"", b"!\n", b"!!", b"G", b"\x85", "!", 33])
def test_realtime_rejects_other_values(tool, command):
    with pytest.raises(ValueError):
        tool.send_grbl_realtime(command)
    tool.grbl_ser_port.write.assert_not_called()


def test_reset_writes_reset_before_waiting_for_greeting(tool):
    events = []
    tool.grbl_ser_port.write.side_effect = lambda data: events.append(("write", data))
    tool.grbl_ser_port.readlines.side_effect = lambda: events.append(("read", None)) or [b"Grbl 1.1h\n"]
    tool.on_grbl_reset()
    assert events == [("write", b"\x18"), ("read", None)]
