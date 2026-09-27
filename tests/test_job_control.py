"""Single-owner CNC acceptance, physical completion and priority fault scenarios."""
from dataclasses import replace

import pytest

from mikrocam.core.cnc_job import PreparedJob
from mikrocam.core.gcode_models import SourceSnapshot, PreflightSetup
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.core.placement import Placement
from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.job_models import StartJobRequest, JobPhase
from mikrocam.machine.manual_models import JogRequest
from mikrocam.machine.models import ConnectionState


class Clock:
    value = 0.

    def __call__(self):
        return self.value


def prepared(text='G21 G90 G17 G94\nG1 X1 F60\nG1 X2\nM2\n'):
    setup = PreflightSetup((0., 0., 0.), Placement(), 0., (-10., -10., -10.),
                           (10., 10., 10.), 0., (600., 600., 600.))
    source = SourceSnapshot('fixture.nc', text)
    return PreparedJob(source, analyze_gcode(source, setup))


def connected(fake=None):
    fake = fake or FakeGRBL()
    clock = Clock()
    controller = MachineController(fake, clock)
    controller.connect()
    for _ in range(8):
        step(controller, clock)
    assert controller.snapshot().manual.can_jog
    return controller, fake, clock


def step(controller, clock, seconds=.1):
    clock.value += seconds
    controller.tick()


def until(controller, clock, predicate, count=250):
    for _ in range(count):
        step(controller, clock)
        if predicate():
            return
    pytest.fail(f'Condition not reached: {controller.snapshot()}')


def start(controller, job=None):
    controller.request_job(StartJobRequest(job or prepared(), True))


def test_exact_source_order_and_completion_requires_idle_endpoint():
    controller, fake, clock = connected()
    job = prepared()
    start(controller, job)
    assert not controller.snapshot().manual.can_jog
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.COMPLETE)
    assert fake.job_writes == [block.wire for block in job.blocks]
    result = controller.snapshot().job
    assert result.acknowledged == result.total == len(job.blocks)
    assert not result.stop_unverified
    assert fake.machine_position == (2., 0., 0.)
    assert fake.writes[-1] == b'?'
    assert controller.snapshot().manual.can_jog


@pytest.mark.parametrize('kwargs', [dict(startup_blocks=('G0X3', '')), dict(g92=(1.,0.,0.)),
                                   dict(tlo=1.), dict(work_system='G55'),
                                   dict(offsets={'G54':(1.,0.,0.)}), dict(machine_position=(1.,0.,0.))])
def test_live_mismatch_sends_no_job_block(kwargs):
    controller, fake, clock = connected(FakeGRBL(**kwargs))
    start(controller)
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.FAILED)
    assert fake.job_writes == []
    assert not controller.snapshot().job.can_start


@pytest.mark.parametrize('settings', [{32:1}, {30:0}, {31:1000,30:500}, {13:1}])
def test_live_settings_fail_before_source(settings):
    controller, fake, clock = connected()
    fake.job_settings.update(settings)
    start(controller)
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.FAILED)
    assert fake.job_writes == []


def test_spindle_speed_must_fit_actual_mechanical_configuration():
    controller, fake, clock = connected()
    start(controller, prepared('G21G90G17G94\nS1200M3\nG1X1F60\nM2\n'))
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.FAILED)
    assert fake.job_writes == []


def running_scripted():
    controller, fake, clock = connected()
    start(controller)
    until(controller, clock, lambda: len(fake.job_writes) == 1)
    fake.auto_respond = False
    fake.read(4096)  # Hold the first source ACK for explicit ownership tests.
    return controller, fake, clock


def test_duplicate_ack_in_one_batch_never_releases_next_block():
    controller, fake, clock = running_scripted()
    fake.inject(b'ok\r\nok\r\n')
    step(controller, clock)
    assert len(fake.job_writes) == 1
    assert controller.snapshot().job.phase is JobPhase.FAILED
    assert controller.snapshot().job.stop_unverified


def test_long_source_ack_wait_keeps_polling_without_three_second_query_timeout():
    controller, fake, clock = running_scripted()
    for _ in range(50):
        fake.inject(b'<Run|MPos:0,0,0|WCO:0,0,0>\r\n')
        step(controller, clock)
    assert controller.snapshot().job.phase is JobPhase.RUNNING
    assert len(fake.job_writes) == 1
    assert fake.writes.count(b'?') > 10


def test_pause_during_pending_dwell_ack_can_resume_without_resend():
    controller, fake, clock = running_scripted()
    controller.pause_job()
    for state in (b'Hold:1', b'Hold:0'):
        step(controller, clock, .3)
        fake.inject(b'<' + state + b'|MPos:0,0,0|WCO:0,0,0>\r\n')
        step(controller, clock)
    assert controller.snapshot().job.phase is JobPhase.PAUSED
    assert controller.snapshot().job.acknowledged == 0
    controller.resume_job()
    assert b'~' in fake.writes
    step(controller, clock, .3)
    fake.inject(b'<Run|MPos:0,0,0|WCO:0,0,0>\r\n')
    step(controller, clock)
    assert len(fake.job_writes) == 1
    fake.inject(b'ok\r\n')
    step(controller, clock)
    assert len(fake.job_writes) == 2


@pytest.mark.parametrize('fault', [b'error:2\r\n', b'ALARM:1\r\n',
                                  b"Grbl 1.1h ['$' for help]\r\n", b'<garbage>\r\n'])
def test_controller_faults_discard_queue_and_never_retry(fault):
    controller, fake, clock = running_scripted()
    fake.inject(fault)
    step(controller, clock)
    result = controller.snapshot().job
    assert result.phase is JobPhase.FAILED and result.stop_unverified
    assert len(fake.job_writes) == 1
    assert not controller.snapshot().manual.can_jog
    controller.disconnect()
    assert controller.snapshot().job == result


def test_stop_inside_read_prevents_next_source_write():
    controller, fake, clock = running_scripted()
    flag = [False]
    controller.set_interrupt_check(lambda: flag[0])
    original = fake.read
    def read(size):
        value = original(size)
        flag[0] = True
        return value
    fake.read = read
    fake.inject(b'ok\r\n')
    step(controller, clock)
    assert len(fake.job_writes) == 1
    controller.stop_job()
    assert fake.writes[-1] == b'\x18'
    assert controller.snapshot().job.phase is JobPhase.ABORTED


def test_disconnect_active_retains_job_identity_and_uncertainty():
    controller, fake, clock = running_scripted()
    controller.disconnect()
    result = controller.snapshot()
    assert result.connection is ConnectionState.DISCONNECTED
    assert result.job.phase is JobPhase.ABORTED
    assert result.job.source_name == 'fixture.nc' and result.job.stop_unverified
    assert fake.writes[-1] == b'\x18'


def test_active_job_rejects_manual_without_writing_jog():
    controller, fake, clock = running_scripted()
    with pytest.raises(ValueError):
        controller.request_manual(JogRequest('X', .1, 100))
    assert not any(line.startswith(b'$J') for line in fake.writes)


def test_stop_before_startup_proof_uses_door_and_never_unverified_reset():
    controller, fake, clock = connected()
    start(controller)
    controller.stop_job()
    assert fake.writes[-1] == b'\x84'
    assert 'parking' in controller.snapshot().job.diagnostic


@pytest.mark.parametrize('state', [b'Door:0', b'Alarm', b'Hold:1'])
def test_resume_never_releases_wrong_machine_state(state):
    controller, fake, clock = running_scripted()
    controller.pause_job()
    step(controller, clock, .3)
    fake.inject(b'<' + state + b'|MPos:0,0,0|WCO:0,0,0>\r\n')
    step(controller, clock)
    with pytest.raises(ValueError):
        controller.resume_job()
    assert b'~' not in fake.writes


def test_initial_position_is_rechecked_at_actual_first_source_write():
    controller, fake, clock = connected()
    start(controller)
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.RUNNING)
    assert fake.job_writes == []
    fake.machine_position = (3.,0.,0.)
    fake.inject(b'<Idle|MPos:3,0,0|WCO:0,0,0>\r\n')
    step(controller, clock)
    assert fake.job_writes == []
    assert controller.snapshot().job.phase is JobPhase.FAILED


def test_late_wco_change_prevents_next_source_block():
    controller, fake, clock = running_scripted()
    fake.inject(b'<Run|MPos:0,0,0|WCO:1,0,0>\r\nok\r\n')
    step(controller, clock)
    assert len(fake.job_writes) == 1
    assert controller.snapshot().job.phase is JobPhase.FAILED


def test_pending_pause_between_guard_and_wire_defers_without_losing_block():
    controller, fake, clock = running_scripted()
    calls = [0]
    def pause_check():
        calls[0] += 1
        return calls[0] >= 3
    controller.set_pause_check(pause_check)
    fake.inject(b'ok\r\n')
    step(controller, clock)
    assert len(fake.job_writes) == 1
    assert controller.snapshot().job.phase is JobPhase.RUNNING
    assert controller._job.transaction is None
    assert controller._job.completed is not None


@pytest.mark.parametrize('status', [b'<Run|MPos:0,0,0|WCO:0,0,0>\r\n',
                                    b'<Hold:0|MPos:0,0,0|WCO:1,0,0>\r\n'])
def test_unsolicited_resume_or_offset_change_during_pause_aborts(status):
    controller, fake, clock = running_scripted()
    controller.pause_job()
    step(controller, clock, .3)
    fake.inject(b'<Hold:0|MPos:0,0,0|WCO:0,0,0>\r\n')
    step(controller, clock)
    assert controller.snapshot().job.phase is JobPhase.PAUSED
    fake.inject(status)
    step(controller, clock)
    assert controller.snapshot().job.phase is JobPhase.FAILED
    assert controller.snapshot().job.stop_unverified and b'~' not in fake.writes


@pytest.mark.parametrize('action', ['pause', 'resume'])
def test_hold_resume_write_failure_preserves_job_progress_and_stop_uncertainty(action):
    controller, fake, clock = running_scripted()
    if action == 'resume':
        controller.pause_job()
        step(controller, clock, .3)
        fake.inject(b'<Hold:0|MPos:0,0,0|WCO:0,0,0>\r\n')
        step(controller, clock)
    fake.write_error = OSError('cable removed during realtime command')
    (controller.pause_job if action == 'pause' else controller.resume_job)()
    result = controller.snapshot()
    assert result.connection is ConnectionState.ERROR
    assert result.job.phase is JobPhase.FAILED and result.job.stop_unverified
    assert result.job.source_name == 'fixture.nc'
    assert 'cable removed' in result.job.diagnostic


def test_failed_units_evidence_cannot_repopulate_dro_using_the_old_unit_scale():
    controller, fake, clock = connected()
    fake.job_settings[13] = 1
    start(controller)
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.FAILED)
    fake.report_units = 'inch'
    fake.machine_position = (25.4,0.,0.)
    for _ in range(5):
        step(controller, clock)
    assert controller.snapshot().report_units is None
    assert controller.snapshot().machine_position_mm is None
