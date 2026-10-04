"""Console presentation uses immutable owner snapshots and typed requests only."""
from dataclasses import replace

import pytest
from PyQt6 import QtCore, QtWidgets

from mikrocam.machine.console_models import CONSOLE_COMMANDS, ConsoleObservation, ConsolePhase, ConsoleRequest
from mikrocam.machine.models import ConnectionState, MachineSnapshot
from mikrocam.machine.wire_log import WireRecord, WireSnapshot
from mikrocam.ui.console_controls import ConsoleControls


def record(sequence=1, payload=b'<b>\x1b[31m\r\nok\x00', **kwargs):
    return WireRecord(sequence, float(sequence), 'RX', payload, 'received', **kwargs)


def snapshot(records=(), **kwargs):
    return MachineSnapshot(connection=ConnectionState.CONNECTED,
                           console=ConsoleObservation(can_query=True),
                           wire=WireSnapshot(tuple(records)), **kwargs)


@pytest.fixture
def controls(qtbot):
    widget = ConsoleControls()
    qtbot.addWidget(widget)
    return widget


def test_collapsed_inert_exact_query_choices(controls):
    assert not controls.toggle_button.isChecked()
    assert controls.body.isHidden()
    assert isinstance(controls.log_view, QtWidgets.QPlainTextEdit)
    assert controls.log_view.isReadOnly()
    assert not controls.query_combo.isEditable()
    assert tuple(controls.query_combo.itemText(i) for i in range(controls.query_combo.count())) == (
        CONSOLE_COMMANDS + ('$CD',))  # $CD: FluidNC-only, refused by the owner elsewhere (044)
    assert not controls.send_button.isEnabled()
    controls.toggle_button.click()
    assert not controls.body.isHidden()


@pytest.mark.parametrize('command', CONSOLE_COMMANDS)
def test_typed_request_and_local_pending_gate(controls, command):
    current = snapshot()
    controls.set_snapshot(current, True)
    controls.query_combo.setCurrentText(command)
    emitted = []
    controls.query_requested.connect(emitted.append)
    controls.send_button.click()
    controls.send_button.click()
    assert emitted == [ConsoleRequest(command)]
    assert not controls.send_button.isEnabled()
    controls.set_snapshot(current, True)
    assert not controls.send_button.isEnabled()
    controls.set_snapshot(replace(current, console=ConsoleObservation(
        ConsolePhase.COMPLETE, command, 'Query complete', True)), True)
    assert controls.send_button.isEnabled()


@pytest.mark.parametrize('worker,eligible', [(False, True), (True, False)])
def test_owner_eligibility_is_authoritative(controls, worker, eligible):
    current = replace(snapshot(), console=ConsoleObservation(can_query=eligible))
    controls.set_snapshot(current, worker)
    assert not controls.send_button.isEnabled()


def test_escaped_plain_bytes_metadata_and_omissions(controls):
    item = record(7, omitted_bytes=19, diagnostic='<b>not markup</b>')
    current = replace(snapshot([item]), wire=WireSnapshot((item,), 3, 21))
    controls.set_snapshot(current, False)
    text = controls.log_view.toPlainText()
    assert repr(item.payload) in text
    assert '\x1b' not in text and '\x00' not in text
    assert '#7' in text and 'RX' in text and 'received' in text and '7.000' in text
    assert '19' in text and '3' in text and '21' in text
    assert '<b>not markup</b>' in text
    assert controls.diagnostic_label.textFormat() == QtCore.Qt.TextFormat.PlainText


def test_clear_is_local_cursor_and_only_new_events_appear(controls):
    first, second = record(1, b'old'), record(2, b'new')
    current = snapshot([first])
    controls.set_snapshot(current, True)
    controls.clear_button.click()
    assert 'old' not in controls.log_view.toPlainText()
    controls.set_snapshot(current, True)
    assert 'old' not in controls.log_view.toPlainText()
    controls.set_snapshot(snapshot([first, second]), True)
    assert 'old' not in controls.log_view.toPlainText()
    assert "b'new'" in controls.log_view.toPlainText()
    assert current.wire.records == (first,)


def test_new_session_resets_clear_cursor_final_failure_keeps_log(controls):
    controls.set_snapshot(snapshot([record(9, b'old')]), True)
    controls.clear_button.click()
    controls.set_snapshot(MachineSnapshot(connection=ConnectionState.CONNECTING), False)
    current = replace(snapshot([record(1, b'new session')]), connection=ConnectionState.ERROR,
                      console=ConsoleObservation(ConsolePhase.FAILED, '$I', '<b>port failed</b>'))
    controls.set_snapshot(current, False)
    assert "b'new session'" in controls.log_view.toPlainText()
    assert '<b>port failed</b>' in controls.diagnostic_label.text()
    controls.set_snapshot(replace(current, connection=ConnectionState.DISCONNECTED), False)
    assert "b'new session'" in controls.log_view.toPlainText()


def test_maximum_ring_replaced_instead_of_appended(controls):
    current = snapshot([record(i, b'x' * 512) for i in range(1, 513)])
    for _ in range(10):
        controls.set_snapshot(current, False)
    assert controls.log_view.toPlainText().count('received') == 512
    assert len(controls.log_view.toPlainText()) < 300000
    controls.set_snapshot(snapshot([record(513, b'latest')]), False)
    assert controls.log_view.toPlainText().count('received') == 1
