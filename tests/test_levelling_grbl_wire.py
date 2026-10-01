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
