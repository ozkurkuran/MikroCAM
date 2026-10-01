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
