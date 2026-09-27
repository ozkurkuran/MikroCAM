"""Adversarial transaction ownership and physical-completion regressions, without I/O."""
import pytest

from mikrocam.machine.job_models import JobPhase, StartJobRequest
from mikrocam.machine.manual_models import JogRequest
from mikrocam.machine.models import ConnectionState
from test_job_control import connected, prepared, running_scripted, start, step, until


BOUNDARIES = ('begin', 'startup', 'settings', 'off', 'modal', 'parameters',
              'initial', 'source', 'final_off', 'final_modal', 'final', 'pausing', 'paused')


def at_boundary(boundary):
    if boundary in ('pausing', 'paused'):
        controller, fake, clock = running_scripted()
        controller.pause_job()
        if boundary == 'paused':
            step(controller, clock, .3)
            fake.inject(b'<Hold:0|MPos:0,0,0|WCO:0,0,0>\r\n')
            step(controller, clock)
            assert controller.snapshot().job.phase is JobPhase.PAUSED
        return controller, fake, clock
    controller, fake, clock = connected()
    start(controller)
    if boundary != 'begin':
        until(controller, clock, lambda: controller._job.transaction == boundary
              or controller._job.waiting_status == boundary)
    return controller, fake, clock


@pytest.mark.parametrize('boundary', BOUNDARIES)
@pytest.mark.parametrize('action', ['stop', 'disconnect'])
def test_stop_or_disconnect_at_every_transaction_boundary_discards_job(boundary, action):
    controller, fake, clock = at_boundary(boundary)
    count = len(fake.job_writes)
    verified = controller._job.startup_verified
    if action == 'stop':
        controller.stop_job()
    else:
        controller.disconnect()
    result = controller.snapshot().job
    assert result.phase is JobPhase.ABORTED and result.stop_unverified
    assert result.source_sha256 == prepared().source.sha256
    assert fake.writes[-1] == (b'\x18' if verified else b'\x84')
    assert controller._job.transaction is None and not controller._job.active
    assert not result.can_start and not result.can_resume
    assert not controller.snapshot().manual.can_jog
    if action == 'stop':
        fake.inject(b'ok\r\n')
        step(controller, clock)
        with pytest.raises(ValueError):
            controller.request_job(StartJobRequest(prepared(), True))
        with pytest.raises(ValueError):
            controller.request_manual(JogRequest('X', .1, 100))
    else:
        assert controller.snapshot().connection is ConnectionState.DISCONNECTED
    assert len(fake.job_writes) == count


@pytest.mark.parametrize('boundary', ['startup', 'source', 'final_off', 'paused'])
def test_failed_reset_or_door_delivery_retains_uncertainty_and_blocks_restart(boundary):
    controller, fake, clock = at_boundary(boundary)
    fake.write_error = OSError('stop wire unavailable')
    controller.stop_job()
    result = controller.snapshot().job
    assert result.phase is JobPhase.ABORTED and result.stop_unverified
    assert 'stop delivery failed' in result.diagnostic
    assert not result.can_start and not controller.snapshot().manual.can_jog
    assert not controller._job.active


@pytest.mark.parametrize('boundary', ['source', 'final_off'])
def test_partial_ordinary_write_is_not_retried_and_never_completes(boundary):
    controller, fake, clock = at_boundary('initial' if boundary == 'source' else 'source')
    if boundary == 'final_off':
        until(controller, clock, lambda: controller.snapshot().job.acknowledged
              == controller.snapshot().job.total-1)
    if boundary == 'source':
        until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.RUNNING)
    original_write = fake.write
    def selective_write(data):
        fake.short_write = data == b'M5 M9\n'
        return original_write(data)
    if boundary == 'final_off':
        fake.write = selective_write
    else:
        original_job_write = fake.write_job
        def short_source(data):
            fake.short_write = True
            return original_job_write(data)
        fake.write_job = short_source
    count = len(fake.job_writes)
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.FAILED)
    assert controller.snapshot().job.stop_unverified
    assert len(fake.job_writes) <= count+1
    terminal_count = len(fake.job_writes)
    for _ in range(5):
        step(controller, clock)
    assert len(fake.job_writes) == terminal_count


def test_fragmented_source_ack_never_releases_next_block_until_full_line():
    controller, fake, clock = running_scripted()
    fake.inject(b'o')
    step(controller, clock)
    fake.inject(b'k')
    step(controller, clock)
    assert len(fake.job_writes) == 1 and controller.snapshot().job.acknowledged == 0
    fake.inject(b'\r\n')
    step(controller, clock)
    assert len(fake.job_writes) == 2 and controller.snapshot().job.acknowledged == 1


@pytest.mark.parametrize('boundary,evidence', [
    ('settings', b'$13=0\r\n$13=0\r\nok\r\n'),
    ('startup', b'$N0=\r\n$N0=\r\n$N1=\r\nok\r\n'),
    ('parameters', b'[G54:0,0,0]\r\n[G92:0,0,0]\r\n[TLO:0]\r\nok\r\n'),
    ('modal', b'[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]\r\n'
               b'[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]\r\nok\r\n')])
def test_duplicate_or_incomplete_live_query_inventory_cannot_admit_source(boundary, evidence):
    controller, fake, clock = at_boundary(boundary)
    fake.auto_respond = False
    fake.read(4096)
    fake.inject(evidence)
    step(controller, clock)
    assert controller.snapshot().job.phase is JobPhase.FAILED
    assert not fake.job_writes


def test_last_source_ack_and_off_ack_do_not_prove_physical_completion():
    controller, fake, clock = at_boundary('final_off')
    fake.auto_respond = False
    fake.read(4096)
    assert controller.snapshot().job.acknowledged == controller.snapshot().job.total
    fake.inject(b'ok\r\n')
    step(controller, clock)
    assert controller.snapshot().job.phase is JobPhase.COMPLETING
    fake.inject(b'[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]\r\nok\r\n')
    step(controller, clock)
    for _ in range(5):
        step(controller, clock, .3)
        fake.inject(b'<Run|MPos:1,0,0|WCO:0,0,0>\r\n')
        step(controller, clock)
        assert controller.snapshot().job.phase is JobPhase.COMPLETING
    step(controller, clock, .3)
    fake.inject(b'<Idle|MPos:2,0,0|WCO:0,0,0>\r\n')
    step(controller, clock)
    assert controller.snapshot().job.phase is JobPhase.COMPLETE


def test_real_dwell_pending_ack_survives_long_verified_hold_without_resend():
    controller, fake, clock = connected()
    start(controller, prepared('G21G90G17G94\nG4P10\nG1X1F60'))
    until(controller, clock, lambda: fake.job_writes[-1:] == [b'G4P10\n'])
    fake.auto_respond = False
    fake.read(4096)
    controller.pause_job()
    step(controller, clock, .3)
    fake.inject(b'<Hold:0|MPos:0,0,0|WCO:0,0,0>\r\n')
    step(controller, clock)
    assert controller.snapshot().job.phase is JobPhase.PAUSED
    for _ in range(120):
        step(controller, clock, 1)
        fake.inject(b'<Hold:0|MPos:0,0,0|WCO:0,0,0>\r\n')
        step(controller, clock, 0)
    controller.resume_job()
    step(controller, clock, .3)
    fake.inject(b'<Run|MPos:0,0,0|WCO:0,0,0>\r\n')
    step(controller, clock)
    assert fake.job_writes.count(b'G4P10\n') == 1
    assert controller.snapshot().job.phase is JobPhase.RUNNING
    fake.inject(b'ok\r\n')
    step(controller, clock)
    assert fake.job_writes[-1] == b'G1X1F60\n'


@pytest.mark.parametrize('boundary', ['source', 'final_off'])
@pytest.mark.parametrize('fault', ['read', 'error_reply', 'alarm'])
def test_source_or_final_off_fault_never_reports_completion(boundary, fault):
    controller, fake, clock = at_boundary(boundary)
    fake.auto_respond = False
    fake.read(4096)
    count = len(fake.job_writes)
    if fault == 'read':
        fake.read_error = OSError('link lost while awaiting acknowledgement')
    else:
        fake.inject(b'error:20\r\n' if fault == 'error_reply' else b'ALARM:2\r\n')
    step(controller, clock)
    result = controller.snapshot().job
    assert result.phase is JobPhase.FAILED and result.stop_unverified
    assert len(fake.job_writes) == count
    assert not result.can_start and not result.can_resume
    assert not controller.snapshot().manual.can_jog


def test_ack_after_coordinates_become_stale_does_not_release_next_source():
    controller, fake, clock = running_scripted()
    fake.inject(b'ok\r\n')
    step(controller, clock, 2.1)
    assert controller.snapshot().job.phase is JobPhase.FAILED
    assert controller.snapshot().job.stop_unverified
    assert len(fake.job_writes) == 1
