"""Actual desktop source-to-dry-job transfer, with simulator-only machine ownership."""
from pathlib import Path


def _prepare(app, qapp, errors, pump_until, text):
    from mikrocam.core.gcode_models import SourceSnapshot
    preflight = app._mikrocam_preflight_panel
    preflight.cancel()
    pump_until(qapp, lambda: not preflight.busy, errors, 'previous preflight cancellation')
    preflight.load_source(SourceSnapshot('dry-cutting.nc', text))
    preflight.analyze_button.click()
    pump_until(qapp, lambda: not preflight.busy and preflight.report is not None,
               errors, 'dry source preflight')
    assert preflight.report.allowed, preflight.report.findings
    before = preflight.source
    preflight.open_dry_run()
    panel = preflight._dry_run_panel
    panel.height_edit.setText('8')
    panel.prepare_button.click()
    pump_until(qapp, lambda: panel.result is not None and not panel.busy, errors, 'dry plane preparation')
    assert preflight.source is before
    assert panel.result.prepared_job.report.allowed
    assert panel.result.prepared_job.final_machine_mm[2] == 8.
    panel.transfer_button.click()
    machine = app._mikrocam_machine_panel
    pump_until(qapp, lambda: machine.job_controls.prepared_job is not None,
               errors, 'dry source transfer')
    assert machine.job_controls.prepared_job.source.sha256 == panel.result.prepared_job.source.sha256
    return panel


def dry_run_journey(app, qapp, errors, pump_until, root):
    from mikrocam.core.gcode_lexer import iter_blocks
    from mikrocam.machine.controller import MachineController
    from mikrocam.machine.fake import FakeGRBL
    from mikrocam.machine.job_models import JobPhase
    machine = app._mikrocam_machine_panel
    assert machine.shutdown()
    fake = FakeGRBL(machine_position=(0.,0.,5.))
    machine.controller_factory = lambda port: MachineController(fake)
    machine.connect_machine()
    pump_until(qapp, lambda: machine.last_snapshot.job.can_start, errors, 'dry simulator connection')
    text = 'G21G90G17G94\nM3S500\nG1X1Z-.1F60\nM8\nG3X2Y1Z-.2I0J1\nM30\n'
    panel = _prepare(app, qapp, errors, pump_until, text)
    machine.job_controls.confirm_checkbox.setChecked(True)
    machine.job_controls.start_button.click()
    pump_until(qapp, lambda: machine.last_snapshot.job.phase is JobPhase.COMPLETE,
               errors, 'dry projected job completion')
    assert fake.machine_position == (2.,1.,8.)
    assert all(letter != 'S' and not (letter == 'M' and value in (3,4,7,8))
               for block in iter_blocks(b''.join(fake.job_writes).decode()) for letter, value in block.words)
    assert sum(b'Z' in line for line in fake.job_writes) == 1
    assert fake.spindle == 'M5' and fake.coolant == ('M9',)
    print('DRY_RUN_PROJECTION_COMPLETE_OK', fake.machine_position, flush=True)
    assert machine.shutdown()
    fake = FakeGRBL(machine_position=(0.,0.,5.))
    machine.controller_factory = lambda port: MachineController(fake)
    machine.connect_machine()
    pump_until(qapp, lambda: machine.last_snapshot.job.can_start, errors, 'dry reconnect')
    text = 'G21G90G17G94\nM3S500\nG1F60\n' + 'X1Z-.1\nX2Z-.2\n'*80 + 'M2\n'
    panel = _prepare(app, qapp, errors, pump_until, text)
    machine.job_controls.confirm_checkbox.setChecked(True)
    machine.job_controls.start_button.click()
    pump_until(qapp, lambda: len(fake.job_writes) >= 6, errors, 'active dry job for shutdown')
    app._mikrocam_preflight_panel.hide()
    panel.show()
    machine.show()
    qapp.processEvents()
    screenshot = Path(root) / '.venv/dry-run-smoke.png'
    assert app.ui.grab().save(str(screenshot))
    assert machine.last_snapshot.job.can_stop
    print('DRY_RUN_ACTIVE_SHUTDOWN_READY', screenshot, flush=True)
    return fake
