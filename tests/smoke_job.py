"""Desktop reviewed-job transfer and simulated physical completion; never hardware."""
from pathlib import Path


SHORT_SOURCE = 'G21G90G17G94\nG1X1F60\nG1X2\nM2\n'
LONG_SOURCE = 'G21G90G17G94\nF60\n' + ''.join(
    f'G1X{1+i%2}\n' for i in range(160)) + 'M2\n'


def _connect_fake(panel, qapp, errors, pump_until):
    from mikrocam.machine.controller import MachineController
    from mikrocam.machine.fake import FakeGRBL
    panel.disconnect_machine()
    pump_until(qapp, lambda: not panel.busy, errors, 'job previous session join')
    fake = FakeGRBL(machine_position=(0., 0., 5.))
    panel.controller_factory = lambda port: MachineController(fake)
    panel.connect_machine()
    pump_until(qapp, lambda: panel.last_snapshot.job.can_start, errors, 'job fresh Fake Idle')
    return fake


def _transfer(preflight, machine, text, qapp, errors, pump_until):
    from mikrocam.core.gcode_models import SourceSnapshot
    preflight.cancel()
    pump_until(qapp, lambda: not preflight.busy, errors, 'previous preflight cancellation')
    preflight.load_source(SourceSnapshot('mechanical-smoke.nc', text))
    for key, field in preflight.setup_widget.fields.items():
        field.setText('0')
    values = dict(initial_z='5', safe_z='5', min_x='-10', min_y='-10', min_z='-10',
                  max_x='10', max_y='10', max_z='10', rapid_x='600', rapid_y='600', rapid_z='600')
    for key, value in values.items():
        preflight.setup_widget.fields[key].setText(value)
    preflight.analyze_button.click()
    pump_until(qapp, lambda: not preflight.busy and preflight.report is not None,
               errors, 'streaming preflight')
    assert preflight.report.allowed, preflight.report.findings
    assert preflight.transfer_button.isEnabled()
    preflight.transfer_button.click()
    pump_until(qapp, lambda: machine.job_controls.prepared_job is not None
               and machine._prepare_worker is None, errors, 'reviewed job preparation')
    job = machine.job_controls.prepared_job
    assert job.source is preflight.source and job.report is preflight.report
    machine.job_controls.confirm_checkbox.setChecked(True)
    pump_until(qapp, lambda: machine.job_controls.start_button.isEnabled(), errors, 'explicit job admission')
    machine.job_controls.start_button.click()
    assert not machine.job_controls.confirm_checkbox.isChecked()
    return job


def job_journey(app, qapp, errors, pump_until, root):
    from mikrocam.machine.job_models import JobPhase
    preflight, panel = app._mikrocam_preflight_panel, app._mikrocam_machine_panel
    fake = _connect_fake(panel, qapp, errors, pump_until)
    job = _transfer(preflight, panel, SHORT_SOURCE, qapp, errors, pump_until)
    pump_until(qapp, lambda: panel.last_snapshot.job.phase is JobPhase.COMPLETE,
               errors, 'job physical completion')
    assert fake.machine_position == (2., 0., 5.)
    assert fake.job_writes == [block.wire for block in job.blocks]
    assert panel.last_snapshot.job.acknowledged == len(job.blocks)
    print('JOB_TRANSFER_COMPLETE_OK', len(job.blocks), flush=True)
    fake = _connect_fake(panel, qapp, errors, pump_until)
    _transfer(preflight, panel, LONG_SOURCE, qapp, errors, pump_until)
    pump_until(qapp, lambda: panel.last_snapshot.job.can_pause and len(fake.job_writes) > 3,
               errors, 'long job running')
    panel.job_controls.pause_button.click()
    pump_until(qapp, lambda: panel.last_snapshot.job.phase is JobPhase.PAUSED,
               errors, 'causal stopped hold')
    assert fake.state == 'Hold:0' and b'!' in fake.writes
    panel.job_controls.resume_button.click()
    pump_until(qapp, lambda: b'~' in fake.writes and panel.last_snapshot.job.can_pause,
               errors, 'explicit job resume')
    panel.job_controls.stop_button.click()
    pump_until(qapp, lambda: panel.last_snapshot.job.phase is JobPhase.ABORTED,
               errors, 'job unverified stop')
    assert panel.last_snapshot.job.stop_unverified and b'\x18' in fake.writes
    assert not panel.last_snapshot.job.can_start
    print('JOB_PAUSE_RESUME_STOP_OK', flush=True)
    fake = _connect_fake(panel, qapp, errors, pump_until)
    _transfer(preflight, panel, LONG_SOURCE, qapp, errors, pump_until)
    pump_until(qapp, lambda: panel.last_snapshot.job.can_pause and len(fake.job_writes) > 3,
               errors, 'active job for application shutdown')
    panel.show()
    panel.raise_()
    qapp.processEvents()
    screenshot = Path(root) / '.venv/job-smoke.png'
    assert app.ui.grab().save(str(screenshot))
    print('JOB_ACTIVE_SHUTDOWN_READY', screenshot, flush=True)
    return fake
