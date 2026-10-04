"""Desktop fiducial fit, aligned job and simulated completion; FakeGRBL only, never hardware."""
from pathlib import Path


SOURCE = 'G21G90G17G94\nG0Z2\nG1Z-.1F60\nG1X10Y0\nG2X10Y10I0J5\nG1X0Y10\nG0Z5\nM2\n'
G54 = (-50., -30., 0.)


def _connect(machine, qapp, errors, pump_until, position):
    from mikrocam.machine.controller import MachineController
    from mikrocam.machine.fake import FakeGRBL
    machine.disconnect_machine()
    pump_until(qapp, lambda: not machine.busy, errors, 'fiducial previous session join')
    fake = FakeGRBL(machine_position=position, offsets={'G54': G54})
    machine.controller_factory = lambda port: MachineController(fake)
    machine.connect_machine()
    pump_until(qapp, lambda: machine.last_snapshot.job.can_start, errors, 'fiducial fresh Fake Idle')
    return fake


def _fit(preflight, truth):
    from mikrocam.core.fiducial import FiducialPair
    panel = preflight.open_fiducial()
    design = ((0., 0.), (80., 0.), (80., 60.), (0., 60.))
    panel.set_pairs(tuple(FiducialPair(f'F{i + 1}', p, truth.apply_point(p)) for i, p in enumerate(design)))
    panel.fit_button.click()
    assert panel.fit_result is not None and panel.fit_result.accepted, panel.report_label.text()
    panel.accept_button.click()
    return panel


def fiducial_journey(app, qapp, errors, pump_until, root):
    from mikrocam.core.gcode_models import SourceSnapshot
    from mikrocam.core.placement import Placement
    from mikrocam.machine.job_models import JobPhase
    preflight, machine = app._mikrocam_preflight_panel, app._mikrocam_machine_panel
    truth = Placement(affine=(.9995, -.0262, .0259, 1.0003, -60., -40.))
    fake = _connect(machine, qapp, errors, pump_until, (*truth.apply_point((0., 0.)), 5.))
    preflight.cancel()
    pump_until(qapp, lambda: not preflight.busy, errors, 'previous preflight cancellation')
    preflight.load_source(SourceSnapshot('fiducial-board.nc', SOURCE))
    for key, value in dict(initial_x='0', initial_y='0', initial_z='5', safe_z='2', z_offset='0',
                           min_x='-200', min_y='-200', min_z='-10', max_x='200', max_y='200',
                           max_z='30', rapid_x='600', rapid_y='600', rapid_z='600').items():
        preflight.setup_widget.fields[key].setText(value)
    fiducial = _fit(preflight, truth)
    preflight.analyze_button.click()
    pump_until(qapp, lambda: not preflight.busy and preflight.report is not None, errors, 'aligned preflight')
    assert preflight.report.allowed and preflight.report.setup.placement.affine is not None
    assert preflight.aligned_button.isEnabled()
    preflight.aligned_button.click()
    aligned = preflight._aligned_panel
    aligned.use_machine_button.click()
    assert (aligned.g54_x_edit.text(), aligned.g54_y_edit.text()) == ('-50', '-30')
    aligned.prepare_button.click()
    pump_until(qapp, lambda: aligned.result is not None and not aligned.busy, errors, 'aligned preparation')
    aligned.transfer_button.click()
    pump_until(qapp, lambda: machine.job_controls.prepared_job is not None
               and machine._prepare_worker is None, errors, 'aligned job transfer')
    assert machine.job_controls.prepared_job.source.sha256 == aligned.result.prepared_job.source.sha256
    machine.job_controls.confirm_checkbox.setChecked(True)
    pump_until(qapp, lambda: machine.job_controls.start_button.isEnabled(), errors, 'aligned admission')
    machine.job_controls.start_button.click()
    pump_until(qapp, lambda: machine.last_snapshot.job.phase is JobPhase.COMPLETE, errors, 'aligned completion')
    expected = (*truth.apply_point((0., 10.)), 5.)
    assert all(abs(a - b) < .005 for a, b in zip(fake.machine_position, expected)), fake.machine_position
    fiducial.show()
    aligned.show()
    qapp.processEvents()
    screenshot = Path(root) / '.venv/fiducial-smoke.png'
    assert app.ui.grab().save(str(screenshot))
    print('FIDUCIAL_ALIGNED_JOB_COMPLETE_OK', fake.machine_position, screenshot, flush=True)
    preflight.setup_widget.clear_alignment()
    fiducial.hide()
    aligned.hide()
    return fake
