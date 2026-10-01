"""Actual Qt desktop queue journey on Fake only; no port enumeration or hardware."""
from pathlib import Path


def queue_journey(app, qapp, errors, pump_until, root):
    from mikrocam.machine.controller import MachineController
    from mikrocam.machine.fake import FakeGRBL
    from mikrocam.machine.queue_models import QueuePhase
    from mikrocam.core.gcode_models import SourceSnapshot, PreflightSetup
    from mikrocam.core.gcode_preflight import analyze_gcode
    from mikrocam.core.cnc_job import PreparedJob
    from mikrocam.core.placement import Placement
    panel = app._mikrocam_machine_panel
    panel.disconnect_machine()
    pump_until(qapp, lambda: not panel.busy, errors, 'queue previous owner join')
    fake = FakeGRBL()
    panel.controller_factory = lambda port: MachineController(fake)
    panel.connect_machine()
    pump_until(qapp, lambda: panel.last_snapshot.queue.can_start, errors, 'queue fresh Idle')
    ui = panel.queue_controls
    setup = PreflightSetup((0.,0.,0.), Placement(), 0., (-10.,-10.,-10.),
                           (10.,10.,10.), 0., (600.,600.,600.))
    jobs = []
    # Offline queue model receives already reviewed immutable snapshots. The existing
    # preflight-to-panel journey separately covers the production candidate binding.
    for i in range(3):
        source = SourceSnapshot(f'queue-desktop-{i}.nc', 'G21G90G17G94\nG1X1F60\nG1X0\nM2\n')
        job = PreparedJob(source, analyze_gcode(source, setup))
        jobs.append(job)
        ui.draft.add(job)
    ui._render()
    panel.open_job_queue()
    ui.confirm.setChecked(True)
    assert ui.start_button.isEnabled()
    ui.start_button.click()
    pump_until(qapp, lambda: panel.last_snapshot.queue.phase is QueuePhase.COMPLETE,
               errors, 'three reviewed queue jobs complete', timeout=15)
    assert fake.job_writes == [b.wire for job in jobs for b in job.blocks]
    assert fake.open_count == 1 and not ui.draft.entries
    screenshot = Path(root) / '.venv/queue-smoke.png'
    assert ui.grab().save(str(screenshot))
    print('QUEUE_THREE_COMPLETE_OK', screenshot, flush=True)
    ui.close()
    return fake
