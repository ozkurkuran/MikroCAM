"""grblHAL boards use every GRBL 1.1 flow on the single controller (spec 043, US1/US2)."""
import pytest

from mikrocam.core.dry_run import prepare_dry_run
from mikrocam.machine.console_models import ConsoleRequest
from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.firmware import FirmwareFamily, IdentificationPhase
from mikrocam.machine.job_models import JobPhase, StartJobRequest, StreamingMode
from mikrocam.machine.manual_models import JogRequest, SelectG54Request, ZeroRequest
from mikrocam.machine.models import MachineState, ManualPhase
from mikrocam.machine.probe_models import ProbePhase, StartProbeGridRequest
from mikrocam.machine.queue_models import QueuePhase
from test_dry_run_execution import reviewed
from test_job_control import prepared
from test_probe_controller import plan
from test_queue_control import queued

MOTION = (b'$J=', b'G10', b'G54\n', b'G21', b'M5 M9')
HAL_BUILD = (b'[VER:1.1f.20250101:]\r\n[OPT:VNMSL,35,1024,3,0]\r\n[AXS:3:XYZ]\r\n'
             b'[NEWOPT:ENUMS,RT+,HOME,SED]\r\n[FIRMWARE:grblHAL]\r\n[SIGNALS:XYZ]\r\n'
             b'[DRIVER:FakeHAL@168MHz]\r\n[BOARD:Fake board]\r\nok\r\n')


class Clock:
    now = 0.

    def __call__(self):
        return self.now


def session(**kwargs):
    clock = Clock()
    fake = FakeGRBL(firmware='grblhal', **kwargs)
    controller = MachineController(fake, clock)
    controller.connect()
    steps(controller, clock, 8)
    return controller, fake, clock


def steps(controller, clock, count=1, seconds=.1):
    for _ in range(count):
        clock.now += seconds
        controller.tick()
    return controller.snapshot()


def until(controller, clock, predicate, count=600, seconds=.1):
    for _ in range(count):
        snap = steps(controller, clock, 1, seconds)
        if predicate(snap):
            return snap
    pytest.fail(f'Condition not reached: {controller.snapshot()}')


def manual_done(snap):
    return snap.manual.phase in (ManualPhase.COMPLETE, ManualPhase.FAILED, ManualPhase.ABORTED)


def job_done(snap):
    return snap.job.phase in (JobPhase.COMPLETE, JobPhase.FAILED, JobPhase.ABORTED)


def rx(snap):
    return b''.join(record.payload for record in snap.wire.records if record.direction == 'RX')


def test_identified_three_axis_board_enables_every_motion_owner():
    controller, fake, clock = session()
    snap = controller.snapshot()
    assert snap.firmware.phase is IdentificationPhase.IDENTIFIED
    assert snap.firmware.capabilities.family is FirmwareFamily.GRBLHAL and snap.firmware.motion_allowed
    assert snap.firmware.capabilities.streaming_rx_budget == 128
    assert snap.state is MachineState.IDLE and snap.report_units == 'mm' and not snap.stale
    assert snap.manual.can_jog and snap.manual.can_zero and snap.manual.can_select_g54
    assert snap.job.can_start and snap.probe.can_start and snap.queue.can_start and snap.console.can_query
    assert b'|Bf:35,1023|FS:0,0' in rx(snap)


def test_jog_g54_select_and_zero_use_grblhal_query_formats_with_vector_tlo():
    controller, fake, clock = session(tlo=1.5, g92=(.5, 0., 0.), machine_position=(1., 2., -3.))
    controller.request_manual(JogRequest('X', 1, 100))
    snap = until(controller, clock, manual_done)
    assert snap.manual.phase is ManualPhase.COMPLETE, snap.manual.diagnostic
    assert snap.machine_position_mm == pytest.approx((2., 2., -3.))
    controller.request_manual(SelectG54Request())
    snap = until(controller, clock, manual_done)
    assert snap.manual.phase is ManualPhase.COMPLETE, snap.manual.diagnostic
    controller.request_manual(ZeroRequest(('X', 'Y', 'Z')))
    snap = until(controller, clock, manual_done)
    assert snap.manual.phase is ManualPhase.COMPLETE, snap.manual.diagnostic
    assert snap.work_position_mm == pytest.approx((0., 0., 0.), abs=.005)
    raw = rx(snap)
    assert b'[TLO:0,0,1.5]' in raw and b'[G59.1:' in raw and b'G98 G50' in raw
    assert b'$J=G21 G91 X1 F100\n' in fake.writes and b'G10 L20 P1 X0 Y0 Z0\n' in fake.writes


def test_jog_cancel_uses_grbl_byte_and_is_verified():
    controller, fake, clock = session()
    controller.request_manual(JogRequest('Y', 10, 100))
    until(controller, clock, lambda snap: controller._manual.jog_sent and snap.state is MachineState.JOG)
    controller.cancel_jog()
    snap = until(controller, clock, manual_done)
    assert snap.manual.phase is ManualPhase.COMPLETE and b'\x85' in fake.writes
    assert not any(byte in fake.writes for byte in (b'\x87', b'\x80', b'\x19', b'\x9f'))


@pytest.mark.parametrize('mode', [StreamingMode.SEND_RESPONSE, StreamingMode.CHARACTER_COUNTING])
def test_job_completes_in_both_streaming_modes(mode):
    controller, fake, clock = session()
    job = prepared()
    controller.request_job(StartJobRequest(job, True, mode))
    snap = until(controller, clock, job_done)
    assert snap.job.phase is JobPhase.COMPLETE, snap.job.diagnostic
    assert fake.job_writes == [block.wire for block in job.blocks]
    if mode is StreamingMode.CHARACTER_COUNTING:
        assert controller._job.stream is None or controller._job.stream.capacity == 128
        assert fake.writes.count(b'$I\n') == 2
    assert b'$300=grblHAL' in rx(snap) and snap.manual.can_jog


def test_character_counting_rejects_changed_opt_evidence_without_source():
    controller, fake, clock = session()
    fake.build_reply = fake.build_reply.replace(b'1024,3,0', b'512,3,0')
    controller.request_job(StartJobRequest(prepared(), True, StreamingMode.CHARACTER_COUNTING))
    snap = until(controller, clock, job_done)
    assert snap.job.phase is JobPhase.FAILED and 'changed' in snap.job.diagnostic
    assert fake.job_writes == []


def test_pause_resume_and_completion_with_hold_substates():
    controller, fake, clock = session()
    job = prepared('G21 G90 G17 G94\n' + ''.join(f'G1 X{i % 5} F600\n' for i in range(1, 30)) + 'M2\n')
    controller.request_job(StartJobRequest(job, True))
    until(controller, clock, lambda snap: len(fake.job_writes) > 3)
    controller.pause_job()
    snap = until(controller, clock, lambda snap: snap.job.phase is JobPhase.PAUSED)
    assert snap.raw_state == 'Hold:0' and b'!' in fake.writes
    controller.resume_job()
    snap = until(controller, clock, job_done)
    assert snap.job.phase is JobPhase.COMPLETE, snap.job.diagnostic
    assert b'~' in fake.writes and fake.job_writes[-1] == job.blocks[-1].wire


def test_stop_resets_and_consistent_grblhal_banner_rereads_only_settings():
    controller, fake, clock = session()
    controller.request_job(StartJobRequest(prepared(), True))
    until(controller, clock, lambda snap: bool(fake.job_writes))
    controller.stop_job()
    snap = steps(controller, clock, 3)
    assert snap.job.phase in (JobPhase.ABORTED, JobPhase.FAILED) and b'\x18' in fake.writes
    assert b'GrblHAL 1.1f' in rx(snap)
    index = len(fake.writes) - fake.writes[::-1].index(b'\x18')
    assert b'$$\n' in fake.writes[index:] and b'$I\n' not in fake.writes[index:]
    assert snap.firmware.phase is IdentificationPhase.IDENTIFIED


def test_probe_grid_completes():
    controller, fake, clock = session(machine_position=(0., 0., 2.))
    controller.request_probe(StartProbeGridRequest(plan(controller)))
    snap = until(controller, clock, lambda s: s.probe.phase in (
        ProbePhase.COMPLETE, ProbePhase.FAILED, ProbePhase.ABORTED), seconds=.25)
    assert snap.probe.phase is ProbePhase.COMPLETE, snap.probe.diagnostic
    assert snap.probe.map.heights_mm == pytest.approx((0., .01, .02, .02, .03, .04), abs=.005)


def test_queue_completes_three_jobs():
    controller, fake, clock = session()
    queued(controller)
    snap = until(controller, clock, lambda s: s.queue.phase is QueuePhase.COMPLETE, count=2000)
    assert all(result.job.phase is JobPhase.COMPLETE for result in snap.queue.entries)


def test_dry_run_job_completes_without_outputs():
    source, report = reviewed()
    result = prepare_dry_run(source, report, 10.)
    controller, fake, clock = session(machine_position=result.prepared_job.initial_machine_mm)
    controller.request_job(StartJobRequest(result.prepared_job, True))
    snap = until(controller, clock, job_done)
    assert snap.job.phase is JobPhase.COMPLETE, snap.job.diagnostic
    assert fake.spindle == 'M5' and fake.coolant == ('M9',)


@pytest.mark.parametrize('command', ['?', '$$', '$G', '$#', '$N', '$I'])
def test_console_queries_complete_with_raw_grblhal_records(command):
    controller, fake, clock = session()
    controller.request_console(ConsoleRequest(command))
    snap = until(controller, clock, lambda s: s.console.phase.value in ('complete', 'failed'))
    assert snap.console.phase.value == 'complete', snap.console.diagnostic


@pytest.mark.parametrize('words', [('M6',), ('M53',), ('G51:XY',), ('G7',), ('G43',), ('G95',)])
def test_non_neutral_modal_words_block_jog_before_motion(words):
    controller, fake, clock = session()
    fake.hal_modal_words = words
    controller.request_manual(JogRequest('X', 1, 100))
    snap = until(controller, clock, manual_done)
    assert snap.manual.phase is ManualPhase.FAILED
    assert not any(write.startswith(b'$J=') for write in fake.writes)


def test_non_z_tool_offset_vector_blocks_zero_before_write():
    controller, fake, clock = session()
    fake.hal_tlo_xy = (1., 0.)
    controller.request_manual(ZeroRequest(('X', 'Y')))
    snap = until(controller, clock, manual_done)
    assert snap.manual.phase is ManualPhase.FAILED
    assert not any(write.startswith(b'G10') for write in fake.writes)


@pytest.mark.parametrize('build', [
    HAL_BUILD.replace(b'1024,3,0', b'1024,4,0').replace(b'3:XYZ', b'4:XYZA'),
    HAL_BUILD.replace(b'RT+', b'RT-'),
    HAL_BUILD.replace(b'HOME,SED', b'LATHE,SED'),
    HAL_BUILD.replace(b',3,0]', b']'),
])
def test_unsupported_board_configuration_never_writes_motion(build):
    controller, fake, clock = session(build_reply=build)
    snap = controller.snapshot()
    assert snap.firmware.capabilities.family is FirmwareFamily.GRBLHAL and not snap.firmware.motion_allowed
    assert not (snap.manual.can_jog or snap.job.can_start or snap.probe.can_start or snap.queue.can_start)
    before = list(fake.writes)
    for request in (JogRequest('X', 1, 100), ZeroRequest(('X', 'Y')), SelectG54Request()):
        with pytest.raises(ValueError):
            controller.request_manual(request)
    with pytest.raises(ValueError):
        controller.request_job(StartJobRequest(prepared(), True))
    steps(controller, clock, 5)
    assert not any(write.startswith(MOTION) for write in fake.writes[len(before):])


def test_push_parser_state_report_during_job_fails_closed_without_next_source():
    controller, fake, clock = session()
    controller.request_job(StartJobRequest(prepared(), True))
    until(controller, clock, lambda snap: bool(fake.job_writes))
    count = len(fake.job_writes)
    fake.inject(b'[GC:G1 G54 G17 G21 G90 G94 G40 G49 G98 G50 M5 M9 T0 F60 S0]\r\n')
    snap = steps(controller, clock, 3)
    assert snap.job.phase is JobPhase.FAILED and len(fake.job_writes) == count


def test_alarm_substate_and_run_substates_are_interpreted():
    controller, fake, clock = session()
    fake.status = b'<Alarm:11|MPos:0.000,0.000,0.000|Bf:35,1023|FS:0,0>\r\n'
    fake.inject(b'ALARM:11\r\n')
    snap = steps(controller, clock, 3)
    assert snap.state is MachineState.ALARM and snap.raw_state == 'Alarm:11'
    assert not snap.manual.can_jog
    fake.status = b'<Run:1|MPos:0.000,0.000,0.000|FS:0,0>\r\n'
    assert steps(controller, clock, 3).state is MachineState.RUNNING


def test_tool_state_is_never_idle():
    controller, fake, clock = session()
    fake.status = b'<Tool|MPos:0.000,0.000,0.000|A:T>\r\n'
    snap = steps(controller, clock, 3)
    assert snap.state is MachineState.UNKNOWN and snap.raw_state == 'Tool' and not snap.manual.can_jog


def test_unsolicited_stale_report_never_completes_jog_at_wrong_position():
    controller, fake, clock = session()
    controller.request_manual(JogRequest('X', 1, 100))
    until(controller, clock, lambda snap: controller._manual.jog_sent)
    fake.inject(b'<Idle|MPos:0.000,0.000,0.000|FS:0,0>\r\n')
    snap = until(controller, clock, manual_done)
    assert snap.manual.phase is not ManualPhase.COMPLETE or snap.machine_position_mm == pytest.approx(
        (1., 0., 0.))


@pytest.mark.parametrize('owner', ['jog', 'zero', 'job', 'probe', 'console'])
def test_grblhal_reset_banner_interrupts_every_owner_without_replay(owner):
    controller, fake, clock = session(machine_position=(0., 0., 2.))
    start = {'jog': lambda: controller.request_manual(JogRequest('X', 10, 100)),
             'zero': lambda: controller.request_manual(ZeroRequest(('X', 'Y'))),
             'job': lambda: controller.request_job(StartJobRequest(prepared(), True)),
             'probe': lambda: controller.request_probe(StartProbeGridRequest(plan(controller))),
             'console': lambda: controller.request_console(ConsoleRequest('$#'))}
    start[owner]()
    steps(controller, clock, 2)
    fake.auto_respond = False
    before = len(fake.writes)
    fake.inject(fake.banner)
    snap = steps(controller, clock, 3)
    assert b'GrblHAL 1.1f' in rx(snap) and snap.report_units is None
    assert snap.firmware.phase is IdentificationPhase.IDENTIFIED  # Consistent banner: no new $I.
    sent = fake.writes[before:]
    assert b'$I\n' not in sent and not any(write.startswith(MOTION) for write in sent)
    assert not snap.manual.can_jog and not snap.job.can_start
