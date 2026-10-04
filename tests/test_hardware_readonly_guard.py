"""No-hardware tests of the operator-only capture's exact write boundary."""
from collections import deque
from unittest.mock import MagicMock

import pytest

from hardware.test_readonly_grbl import COMMANDS, enabled, read_query


@pytest.mark.parametrize("env,expected", [
    ({}, False), ({"MIKROCAM_HW_PORT": "COM7"}, True),
    ({"MIKROCAM_HW_PORT": "COM7", "CI": "true"}, False),
    ({"MIKROCAM_HW_PORT": "COM7", "GITHUB_ACTIONS": "true"}, False),
])
def test_hardware_capture_requires_port_and_excludes_ci(env, expected):
    assert enabled(env) is expected


@pytest.mark.parametrize("command,reply", [
    (b"?", b"<Idle|MPos:0,0,0>\r\n"),
    (b"$I\n", b"[VER:1.1h:inventor]\r\nok\r\n"),
    (b"$$\n", b"$0=10\r\nok\r\n"),
    (b"$G\n", b"[GC:G0 G54 G17 G21 G90 M5 M9]\r\nok\r\n"),
    (b"$#\n", b"[G54:0,0,0]\r\nok\r\n"),
])
def test_only_readonly_queries_and_fragmented_replies(command, reply):
    transport = MagicMock()
    transport.write.return_value = len(command)
    transport.read.side_effect = [bytes([byte]) for byte in reply]
    lines = read_query(transport, command, [], clock=lambda: 0)
    assert lines
    transport.write.assert_called_once_with(command)
    assert COMMANDS == (b"?", b"$I\n", b"$$\n", b"$G\n", b"$#\n")


@pytest.mark.parametrize("command", [b"$J=G91 X1 F100\n", b"G10 L20 P1 X0\n", b"$10=0\n", b"$H\n", b"\x18", b"M5 M9\n", b"?\n", "?"])
def test_capture_rejects_motion_settings_and_reset_before_writing(command):
    transport = MagicMock()
    with pytest.raises(ValueError):
        read_query(transport, command, [])
    transport.write.assert_not_called()


def test_readonly_timeout_is_bounded():
    transport = MagicMock()
    transport.write.return_value = 1
    transport.read.return_value = b""
    ticks = deque([0, 0, 3.1])
    with pytest.raises(TimeoutError):
        read_query(transport, b"?", [], clock=ticks.popleft)


def test_ack_without_inventory_is_not_success():
    transport = MagicMock()
    transport.write.return_value = 3
    transport.read.return_value = b"ok\n"
    ticks = deque([0, 0, 3.1])
    with pytest.raises(TimeoutError):
        read_query(transport, b"$I\n", [], clock=ticks.popleft)


@pytest.mark.parametrize("reply", [b"error:3\n", b"ALARM:1\n", b"x" * 16385])
def test_capture_rejects_failed_or_unbounded_response(reply):
    transport = MagicMock()
    transport.write.return_value = 3
    transport.read.return_value = reply
    with pytest.raises(ValueError):
        read_query(transport, b"$I\n", [], clock=lambda: 0)


@pytest.mark.parametrize("failure", [False, True])
def test_operator_entry_retains_log_and_closes_mock_port(monkeypatch, tmp_path, failure):
    import json
    from hardware import test_readonly_grbl as capture
    log = tmp_path / "readonly.json"
    monkeypatch.setenv("MIKROCAM_HW_PORT", "COM_TEST")
    monkeypatch.setenv("MIKROCAM_HW_LOG", str(log))
    transport = MagicMock()
    transport.read.return_value = b""
    ticks = iter([0, 0, 2.1])
    monkeypatch.setattr(capture.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(capture.subprocess, "check_output", lambda *a, **kw: b"abc123")
    monkeypatch.setattr(capture, "SerialIO", lambda port: transport)
    queries = []
    def query(owner, command, transcript):
        assert owner is transport
        queries.append(command)
        if failure:
            raise TimeoutError("mock failure")
        return ["mock inventory", "ok"]
    monkeypatch.setattr(capture, "read_query", query)
    if failure:
        with pytest.raises(TimeoutError):
            capture.test_readonly_grbl_inventory()
    else:
        capture.test_readonly_grbl_inventory()
    transport.open.assert_called_once()
    transport.close.assert_called_once()
    assert queries == ([b"?"] if failure else list(COMMANDS))
    assert json.loads(log.read_text(encoding="utf-8"))["result"] == ("failed" if failure else "passed")


@pytest.mark.parametrize('command,reply', [
    (b'?', b'<Idle>\n'), (b'?', b'<Idle|MPos:0,nan,0>\n'),
    (b'$I\n', b'[VER:\nok\n'), (b'$I\n', b'[VER:1.1h]\nok\n'),
    (b'$$\n', b'$0=\nok\n'), (b'$$\n', b'$0=nan\nok\n'),
    (b'$G\n', b'[GC:\nok\n'), (b'$G\n', b'[GC:]\nok\n'),
    (b'$#\n', b'[G54:0,0]\nok\n'), (b'$#\n', b'[G54:0,0,nan]\nok\n'),
])
def test_inventory_rejects_structurally_invalid_records(command, reply):
    transport = MagicMock()
    transport.write.return_value = len(command)
    transport.read.return_value = reply
    with pytest.raises(ValueError):
        read_query(transport, command, [], clock=lambda: 0)


@pytest.mark.parametrize('failure', ['short', 'exception'])
def test_transcript_never_claims_successful_tx_when_write_fails(failure):
    transport = MagicMock()
    transport.write.return_value = 1
    if failure == 'exception':
        transport.write.side_effect = OSError('mock uncertain write')
    transcript = []
    with pytest.raises(OSError):
        read_query(transport, b'$I\n', transcript)
    assert transcript and transcript[0]['direction'] == 'tx-attempt'
    assert not any(entry['direction'] == 'tx' for entry in transcript)
    transport.read.assert_not_called()


# --- spec 044: FluidNC readonly inventory additions (operator-only capture, NOT_RUN on hardware) ---
from hardware.test_readonly_grbl import FLUIDNC_COMMANDS, is_fluidnc  # noqa: E402
from mikrocam.machine.fluidnc import STARTUP_QUERIES  # noqa: E402


def test_fluidnc_inventory_adds_only_readonly_macro_report_and_config_queries():
    assert FLUIDNC_COMMANDS == STARTUP_QUERIES + (b"$CD\n",)
    assert is_fluidnc(["[VER:4.1 FluidNC v4.1.1 (esp32-wifi) :]", "ok"])
    assert not is_fluidnc(["[VER:1.1h.20190830:]", "ok"])


@pytest.mark.parametrize("command,reply", [
    (b"$I\n", b"[VER:4.1 FluidNC v4.1.1 (esp32-wifi) :]\r\n[OPT:PHSEW]\r\n[MSG: Machine: x]\r\nok\r\n"),
    (b"$I\n", b"[VER:3.9 FluidNC v3.9.9:]\r\n[OPT:PHSEW]\r\nok\r\n"),
    (b"$$\n", b"$13=0\r\n$20=0\r\n$30=1000\r\n$32=0\r\n$100=80.000\r\n$10=1\r\nok\r\n"),
    (b"$#\n", b"[G54:0.000,0.000,0.000]\r\n[TLO:0.000,0.000,0.000]\r\nok\r\n"),
    (b"$/macros/startup_line0\n", b"$/macros/startup_line0=\r\nok\r\n"),
    (b"$/macros/after_reset\n", b"$/macros/after_reset=G0 Z5\r\nok\r\n"),
    (b"$RI\n", b"[MSG:INFO: uart_channel0 auto reporting is off]\r\nok\r\n"),
    (b"$CD\n", b"board: Fake\r\naxes:\r\n  x:\r\nok\r\n"),
])
def test_fluidnc_readonly_inventory_replies_are_complete(command, reply):
    transport = MagicMock()
    transport.write.return_value = len(command)
    transport.read.side_effect = [bytes([byte]) for byte in reply]
    assert read_query(transport, command, [], clock=lambda: 0)[-1] == "ok"
    transport.write.assert_called_once_with(command)


def test_operator_entry_adds_fluidnc_queries_only_after_fluidnc_identification(monkeypatch, tmp_path):
    from hardware import test_readonly_grbl as capture
    monkeypatch.setenv("MIKROCAM_HW_PORT", "COM_TEST")
    monkeypatch.setenv("MIKROCAM_HW_LOG", str(tmp_path / "readonly.json"))
    transport = MagicMock()
    transport.read.return_value = b""
    ticks = iter([0, 0, 2.1])
    monkeypatch.setattr(capture.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(capture.subprocess, "check_output", lambda *a, **kw: b"abc123")
    monkeypatch.setattr(capture, "SerialIO", lambda port: transport)
    queries = []

    def query(owner, command, transcript):
        queries.append(command)
        return ["[VER:4.1 FluidNC v4.1.1 (esp32-wifi) :]", "ok"] if command == b"$I\n" else ["x", "ok"]
    monkeypatch.setattr(capture, "read_query", query)
    capture.test_readonly_grbl_inventory()
    assert queries == list(COMMANDS) + list(FLUIDNC_COMMANDS)
