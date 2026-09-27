"""Dry-run derivation must enter the existing single-owner sender without fallback."""
from dataclasses import replace

import pytest

from mikrocam.core.dry_run import prepare_dry_run
from mikrocam.core.gcode_models import SourceSnapshot, PreflightSetup
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.core.gcode_lexer import iter_blocks
from mikrocam.core.placement import Placement
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.job_models import JobPhase
from test_job_control import connected, step, until, start


def reviewed(text='G21G90G17G94\nS500M3\nG1X1Z-.1F60\nM8\nG1X2Z-.2\nM30\n',
             *, placement=None, z_offset=0.):
    setup = PreflightSetup((0.,0.,5.), placement or Placement(), z_offset,
                           (-100.,-100.,-10.), (100.,100.,30.), 5.+z_offset, (600.,600.,600.))
    source = SourceSnapshot('cutting.nc', text)
    report = analyze_gcode(source, setup)
    assert report.allowed, report.findings
    return source, report


def execute(result, *, fake=None):
    controller, fake, clock = connected(fake or FakeGRBL(machine_position=result.prepared_job.initial_machine_mm))
    start(controller, result.prepared_job)
    until(controller, clock, lambda: controller.snapshot().job.phase in (JobPhase.COMPLETE,JobPhase.FAILED))
    return controller, fake, clock


def test_only_reviewed_derived_blocks_run_with_vertical_clearance_before_xy():
    source, report = reviewed()
    result = prepare_dry_run(source, report, 10.)
    fake = FakeGRBL(machine_position=(0.,0.,5.))
    fake.spindle, fake.coolant = 'M3', ('M8',)
    controller, fake, clock = execute(result, fake=fake)
    assert controller.snapshot().job.phase is JobPhase.COMPLETE
    assert fake.job_writes == [block.wire for block in result.prepared_job.blocks]
    assert fake.machine_position == (2.,0.,10.)
    assert fake.spindle == 'M5' and fake.coolant == ('M9',)
    body = b''.join(fake.job_writes)
    assert all(letter != 'S' and not (letter == 'M' and value in (3,4,7,8))
               for block in iter_blocks(body.decode()) for letter, value in block.words)
    first_z = next(i for i, block in enumerate(fake.job_writes) if b'Z' in block)
    first_xy = next(i for i, block in enumerate(fake.job_writes) if b'X' in block or b'Y' in block)
    assert first_z < first_xy and b'X' not in fake.job_writes[first_z] and b'Y' not in fake.job_writes[first_z]
    assert sum(b'Z' in block for block in fake.job_writes) == 1
    assert result.original_source is source and result.original_report is report
    assert source.text.startswith('G21G90G17G94\nS500M3')
    controller.disconnect()


def test_translated_g54_and_z_offset_use_the_same_machine_plane():
    placement = Placement(origin=(1.,2.), translation=(4.,6.))
    source, report = reviewed(placement=placement, z_offset=3.)
    result = prepare_dry_run(source, report, 12.)
    fake = FakeGRBL(machine_position=(3.,4.,8.), offsets={'G54':(3.,4.,3.)})
    controller, fake, clock = execute(result, fake=fake)
    assert controller.snapshot().job.phase is JobPhase.COMPLETE
    assert fake.machine_position == (5.,4.,12.)
    assert result.prepared_job.report.setup.safe_z_mm == 12.
    assert result.prepared_job.report.setup.placement == report.setup.placement
    controller.disconnect()


def test_inch_incremental_helical_source_projects_to_expected_circle_endpoint():
    source, report = reviewed('G20G91G17G94\nG3X1Y1Z-.01I0J1F10\nG1X1Z-.01\nM2\n')
    result = prepare_dry_run(source, report, 10.)
    controller, fake, clock = execute(result)
    assert controller.snapshot().job.phase is JobPhase.COMPLETE
    assert fake.machine_position == pytest.approx((50.8,25.4,10.))
    assert result.prepared_job.report.arc_count == 1
    assert b'G3X1Y1I0J1F10\n' in fake.job_writes
    controller.disconnect()


@pytest.mark.parametrize('kwargs', [dict(offsets={'G54':(1.,0.,0.)}),dict(machine_position=(1.,0.,5.)),
                                   dict(g92=(1.,0.,0.)),dict(tlo=1.)])
def test_live_mismatch_sends_neither_original_nor_derived_source(kwargs):
    source, report = reviewed()
    result = prepare_dry_run(source, report, 10.)
    options = dict(machine_position=(0.,0.,5.))
    options.update(kwargs)
    controller, fake, clock = execute(result, fake=FakeGRBL(**options))
    assert controller.snapshot().job.phase is JobPhase.FAILED
    assert not fake.job_writes
    controller.disconnect()


def test_stop_after_retract_has_no_cutting_source_fallback():
    source, report = reviewed()
    result = prepare_dry_run(source, report, 10.)
    controller, fake, clock = connected(FakeGRBL(machine_position=(0.,0.,5.)))
    start(controller, result.prepared_job)
    until(controller, clock, lambda: any(b'Z' in line for line in fake.job_writes))
    sent = list(fake.job_writes)
    controller.stop_job()
    for _ in range(10):
        step(controller, clock)
    assert fake.job_writes == sent
    assert controller.snapshot().job.phase is JobPhase.ABORTED
    assert controller.snapshot().job.stop_unverified
    assert b'S500M3\n' not in fake.writes
    controller.disconnect()


def test_active_dry_job_close_keeps_derived_identity_and_stop_uncertainty():
    source, report = reviewed()
    result = prepare_dry_run(source, report, 10.)
    controller, fake, clock = connected(FakeGRBL(machine_position=(0.,0.,5.)))
    start(controller, result.prepared_job)
    until(controller, clock, lambda: bool(fake.job_writes))
    controller.disconnect()
    value = controller.snapshot().job
    assert value.source_sha256 == result.prepared_job.source.sha256
    assert value.source_sha256 != source.sha256
    assert value.phase is JobPhase.ABORTED and value.stop_unverified


def test_dry_job_hold_resume_and_stop_share_the_existing_owner_without_outputs():
    source, report = reviewed('G21G90G17G94\nM3S500\nG1F60\n' + 'X1Z-.1\nX2Z-.2\n'*80 + 'M2\n')
    result = prepare_dry_run(source, report, 10.)
    controller, fake, clock = connected(FakeGRBL(machine_position=(0.,0.,5.)))
    start(controller, result.prepared_job)
    until(controller, clock, lambda: len(fake.job_writes) > 6)
    controller.pause_job()
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.PAUSED)
    count = len(fake.job_writes)
    for _ in range(10):
        step(controller, clock)
    assert len(fake.job_writes) == count and fake.machine_position[2] == 10.
    controller.resume_job()
    until(controller, clock, lambda: len(fake.job_writes) > count)
    assert b'!' in fake.writes and b'~' in fake.writes
    assert fake.spindle == 'M5' and fake.coolant == ('M9',)
    controller.stop_job()
    assert controller.snapshot().job.phase is JobPhase.ABORTED
    assert controller.snapshot().job.stop_unverified
    controller.disconnect()
