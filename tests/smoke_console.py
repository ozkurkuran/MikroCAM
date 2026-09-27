"""Desktop read-only console evidence against the owned FakeGRBL session."""
from pathlib import Path


def console_journey(app, qapp, errors, pump_until, root):
    from PyQt6 import QtCore, QtWidgets
    from mikrocam.machine.controller import MachineController
    from mikrocam.machine.fake import FakeGRBL
    from mikrocam.machine.console_models import CONSOLE_COMMANDS, ConsolePhase

    panel = app._mikrocam_machine_panel
    panel.disconnect_machine()
    pump_until(qapp, lambda: not panel.busy, errors, 'console previous session closure')
    fake = FakeGRBL()
    panel.controller_factory = lambda port: MachineController(fake)
    panel.connect_machine()
    controls = panel.console_controls
    pump_until(qapp, lambda: controls.send_button.isEnabled(), errors, 'console fresh Idle')
    assert not controls.toggle_button.isChecked()
    controls.toggle_button.click()
    assert isinstance(controls.log_view, QtWidgets.QPlainTextEdit)
    assert controls.diagnostic_label.textFormat() == QtCore.Qt.TextFormat.PlainText
    for command in CONSOLE_COMMANDS:
        controls.query_combo.setCurrentText(command)
        controls.send_button.click()
        assert not controls.send_button.isEnabled()
        pump_until(qapp, lambda: panel.last_snapshot.console.phase is ConsolePhase.COMPLETE
                   and panel.last_snapshot.console.command == command, errors, f'console {command}')
    assert '[VER:' in controls.log_view.toPlainText()
    assert "b'$I\\n'" in controls.log_view.toPlainText()
    raw = b'[MSG:<b>plain</b>\x1b[31m\x00]\r\n'
    fake.inject(raw)
    pump_until(qapp, lambda: repr(raw) in controls.log_view.toPlainText(), errors, 'escaped raw console bytes')
    assert '\x1b' not in controls.log_view.toPlainText() and '\x00' not in controls.log_view.toPlainText()
    old_sequence = panel.last_snapshot.wire.records[-1].sequence
    controls.clear_button.click()
    assert '[VER:' not in controls.log_view.toPlainText()
    assert all(record.sequence <= old_sequence for record in panel.last_snapshot.wire.records)
    controls.query_combo.setCurrentText('$G')
    controls.send_button.click()
    pump_until(qapp, lambda: panel.last_snapshot.console.command == '$G'
               and panel.last_snapshot.console.phase is ConsolePhase.COMPLETE, errors, 'console after Clear')
    assert '[GC:' in controls.log_view.toPlainText()
    assert "b'$I\\n'" not in controls.log_view.toPlainText()
    assert old_sequence < panel.last_snapshot.wire.records[-1].sequence
    panel.show()
    panel.raise_()
    qapp.processEvents()
    screenshot = Path(root) / '.venv/console-smoke.png'
    assert app.ui.grab().save(str(screenshot))
    print('CONSOLE_READ_ONLY_CLEAR_OK', screenshot, flush=True)
    # A query already sent but not acknowledged must retain failure evidence on close.
    fake.auto_respond = False
    controls.query_combo.setCurrentText('$I')
    previous_count = fake.writes.count(b'$I\n')
    controls.send_button.click()
    pump_until(qapp, lambda: panel.last_snapshot.console.phase is ConsolePhase.PENDING
               and fake.writes.count(b'$I\n') == previous_count + 1, errors, 'console pending query')
    panel.disconnect_machine()
    pump_until(qapp, lambda: not panel.busy, errors, 'console pending disconnect')
    assert panel.last_snapshot.console.phase is ConsolePhase.FAILED
    assert 'Disconnected' in panel.last_snapshot.console.diagnostic
    assert "b'$I\\n'" in controls.log_view.toPlainText()
    assert not fake.is_open and not controls.send_button.isEnabled()
    assert set(fake.writes) <= {b'?', b'$$\n', b'$G\n', b'$#\n', b'$N\n', b'$I\n'}
    print('CONSOLE_DISCONNECT_EVIDENCE_OK', flush=True)
