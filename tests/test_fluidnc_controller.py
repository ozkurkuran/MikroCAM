"""FluidNC over USB serial on the single controller with FakeGRBL profiles (spec 044)."""
import pytest

from mikrocam.machine.console_models import ConsolePhase, ConsoleRequest
from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.firmware import FirmwareFamily, IdentificationPhase
from mikrocam.machine.fluidnc import STARTUP_QUERIES
from mikrocam.machine.job_models import JobPhase, StartJobRequest, StreamingMode
from mikrocam.machine.manual_models import JogRequest, SelectG54Request, ZeroRequest
from mikrocam.machine.models import ConnectionState, ManualPhase
from mikrocam.machine.probe_models import ProbePhase, StartProbeGridRequest
from mikrocam.machine.queue_models import QueueDraft, QueuePhase
from test_job_control import Clock, prepared, step, until
from test_probe_controller import plan

PROFILES = ('fluidnc', 'fluidnc3')
MOTION = (b'$J=', b'G10', b'G54\n', b'G38.2', b'G1', b'G0', b'\x18')
MACRO_BYTES = (b'\x87', b'\x88', b'\x89', b'\x8a')


def connected(firmware='fluidnc', **kwargs):
    fake, clock = FakeGRBL(firmware=firmware, **kwargs), Clock()
    controller = MachineController(fake, clock)
    controller.connect()
    for _ in range(8):
        step(controller, clock)
    return controller, fake, clock


def no_macro_bytes(fake):
    return not any(byte in write for write in fake.writes for byte in MACRO_BYTES)


@pytest.mark.parametrize('firmware,version', [('fluidnc', '4.1.1'), ('fluidnc3', '3.9.9')])
def test_identified_fluidnc_enables_every_motion_owner(firmware, version):
    controller, fake, clock = connected(firmware)
    snap = controller.snapshot()
    assert snap.firmware.phase is IdentificationPhase.IDENTIFIED and snap.firmware.motion_allowed
    assert snap.firmware.capabilities.family is FirmwareFamily.FLUIDNC
    assert snap.firmware.capabilities.version == version
    assert snap.report_units == 'mm' and not snap.stale
    assert snap.manual.can_jog and snap.manual.can_zero and snap.job.can_start
    assert snap.probe.can_start and snap.queue.can_start and snap.console.can_query
    assert fake.writes[:3] == [b'$I\n', b'$$\n', b'?']


@pytest.mark.parametrize('firmware', PROFILES)
def test_jog_verifies_macros_and_auto_report_instead_of_n(firmware):
    controller, fake, clock = connected(firmware)
    controller.request_manual(JogRequest('X', 1., 100.))
    until(controller, clock, lambda: controller.snapshot().manual.phase is ManualPhase.COMPLETE)
    writes = [write for write in fake.writes if write != b'?']  # Status polls interleave.
    assert b'$N\n' not in writes
    start = writes.index(STARTUP_QUERIES[0])
    assert writes[start:start + 4] == list(STARTUP_QUERIES)
    assert writes.index(b'M5 M9\n') > start + 3 and b'$J=G21 G91 X1 F100\n' in writes
    assert controller.snapshot().machine_position_mm == (1., 0., 0.)
    assert no_macro_bytes(fake)


@pytest.mark.parametrize('firmware', PROFILES)
def test_zero_and_select_g54_complete_with_fluidnc_parameters(firmware):
    controller, fake, clock = connected(firmware, machine_position=(3., 4., 5.), work_system='G55')
    controller.request_manual(SelectG54Request())
    until(controller, clock, lambda: controller.snapshot().manual.phase is ManualPhase.COMPLETE)
    controller.request_manual(ZeroRequest(('X', 'Y', 'Z')))
    until(controller, clock, lambda: controller.snapshot().manual.phase is ManualPhase.COMPLETE
          and controller.snapshot().manual.action == 'zero')
    assert controller.snapshot().work_position_mm == (0., 0., 0.)
    assert fake.offsets['G54'] == (3., 4., 5.)


@pytest.mark.parametrize('macro', ['startup_line0', 'startup_line1', 'after_reset'])
def test_filled_macro_refuses_motion_and_never_authorizes_reset(macro):
    controller, fake, clock = connected()
    fake.fluidnc.macros[macro] = 'G0 Z10'
    controller.request_manual(JogRequest('Z', 1., 100.))
    until(controller, clock, lambda: controller.snapshot().manual.phase is ManualPhase.FAILED)
    assert macro in controller.snapshot().manual.diagnostic
    assert not any(write.startswith(MOTION) for write in fake.writes)
    assert not controller._manual.startup_verified


@pytest.mark.parametrize('interval,info,needle', [(200, True, '$RI'), (0, False, 'Message/Level')])
def test_auto_report_on_or_unverifiable_refuses_motion(interval, info, needle):
    controller, fake, clock = connected()
    fake.fluidnc.report_interval, fake.fluidnc.message_info = interval, info
    controller.request_job(StartJobRequest(prepared(), True))
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.FAILED)
    assert needle in controller.snapshot().job.diagnostic
    assert fake.job_writes == [] and not any(write.startswith(MOTION) for write in fake.writes)


@pytest.mark.parametrize('firmware', PROFILES)
def test_send_response_job_completes_with_fluidnc_settings_proxies(firmware):
    controller, fake, clock = connected(firmware)
    job = prepared('G21 G90 G17 G94\nM3 S800\nG1 X1 F60\nG1 X2\nM5\nM2\n')
    controller.request_job(StartJobRequest(job, True))
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.COMPLETE, 400)
    assert fake.job_writes == [block.wire for block in job.blocks]
    assert b'$N\n' not in fake.writes and fake.writes.count(b'$$\n') == 2
    assert no_macro_bytes(fake)


@pytest.mark.parametrize('field,value,needle', [('laser_mode', 1, 'laser'), ('max_spindle', 500, 'outside')])
def test_fluidnc_spindle_proxies_gate_job_admission(field, value, needle):
    controller, fake, clock = connected()
    setattr(fake.fluidnc, field, value)
    controller.request_job(StartJobRequest(prepared('G21 G90 G17 G94\nM3 S800\nG1 X1 F60\nM5\nM2\n'), True))
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.FAILED)
    assert needle in controller.snapshot().job.diagnostic and fake.job_writes == []


def test_character_counting_is_refused_without_rx_evidence():
    controller, fake, clock = connected()
    controller.request_job(StartJobRequest(prepared(), True, StreamingMode.CHARACTER_COUNTING))
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.FAILED)
    assert 'RX budget' in controller.snapshot().job.diagnostic and fake.job_writes == []


def test_hold_resume_and_stop_use_the_grbl_realtime_bytes():
    controller, fake, clock = connected()
    text = 'G21G90G17G94\nF60\n' + ''.join(f'G1X{1 + i % 2}\n' for i in range(12)) + 'M2\n'
    controller.request_job(StartJobRequest(prepared(text), True))
    until(controller, clock, lambda: len(fake.job_writes) >= 3)
    controller.pause_job()
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.PAUSED)
    controller.resume_job()
    until(controller, clock, lambda: len(fake.job_writes) >= 6)
    controller.stop_job()
    assert controller.snapshot().job.phase is JobPhase.ABORTED
    assert b'!' in fake.writes and b'~' in fake.writes and fake.writes[-1] == b'\x18'
    assert no_macro_bytes(fake)


def test_queue_runs_each_entry_with_fluidnc_startup_evidence():
    controller, fake, clock = connected()
    draft = QueueDraft()
    for index in range(2):
        draft.add(prepared(f'G21 G90 G17 G94\nG1 X1 F60\nG1 X{index}\nM2\n'))
    controller.request_queue(draft.start_request(True))
    until(controller, clock, lambda: controller.snapshot().queue.phase is QueuePhase.COMPLETE, 600)
    assert fake.writes.count(b'$RI\n') == 2 and b'$N\n' not in fake.writes


@pytest.mark.parametrize('firmware', PROFILES)
def test_probe_grid_completes_and_tlo_vector_is_accepted(firmware):
    controller, fake, clock = connected(firmware, machine_position=(0., 0., 2.))
    controller.request_probe(StartProbeGridRequest(plan(controller)))
    until(controller, clock, lambda: controller.snapshot().probe.phase in (
        ProbePhase.COMPLETE, ProbePhase.FAILED, ProbePhase.ABORTED), 600)
    assert controller.snapshot().probe.phase is ProbePhase.COMPLETE, controller.snapshot().probe
    assert b'$N\n' not in fake.writes


def test_nonzero_tlo_vector_xy_refuses_probe_before_motion():
    controller, fake, clock = connected(machine_position=(0., 0., 2.))
    fake.fluidnc.tlo_xy = (0.5, 0.)
    controller.request_probe(StartProbeGridRequest(plan(controller)))
    until(controller, clock, lambda: controller.snapshot().probe.phase is ProbePhase.FAILED)
    assert not any(b'G38.2' in write or write.startswith(b'G21 G90 G94 G1') for write in fake.writes)


def test_console_config_dump_only_on_fluidnc_and_n_refused():
    controller, fake, clock = connected()
    controller.request_console(ConsoleRequest('$CD'))
    until(controller, clock, lambda: controller.snapshot().console.phase is ConsolePhase.COMPLETE)
    assert b'$CD\n' in fake.writes and controller.snapshot().manual.can_jog
    before = list(fake.writes)
    with pytest.raises(ValueError, match='FluidNC'):
        controller.request_console(ConsoleRequest('$N'))
    grbl, grbl_fake, grbl_clock = connected('grbl')
    with pytest.raises(ValueError, match='FluidNC'):
        grbl.request_console(ConsoleRequest('$CD'))
    step(controller, clock)
    assert b'$N\n' not in fake.writes[len(before):] and b'$CD\n' not in grbl_fake.writes


def test_unsupported_major_version_is_identified_but_motion_disabled():
    reply = b'[VER:5.0 FluidNC v5.0.1 (esp32-wifi) :]\r\n[OPT:PHSEW]\r\nok\r\n'
    controller, fake, clock = connected(build_reply=reply)
    snap = controller.snapshot()
    assert snap.firmware.capabilities.family is FirmwareFamily.FLUIDNC
    assert not snap.firmware.motion_allowed and not snap.manual.can_jog and not snap.job.can_start


def boot_until_ready(controller, fake, clock, *, custom=None):
    """Port-open style reboot: ROM output, Starting phase, then FluidNC logs and greeting."""
    if custom is not None:
        fake.banner = custom
    fake.fluidnc.power_cycle()
    for _ in range(5):
        step(controller, clock)
    sent_while_booting = [write for write in fake.writes if write in (b'$I\n', b'$$\n')]
    fake.fluidnc.starting()
    for _ in range(5):
        step(controller, clock)
    fake.fluidnc.finish_boot()
    return sent_while_booting


def test_port_open_reboot_waits_for_ready_board_before_identifying():
    fake, clock = FakeGRBL(firmware='fluidnc'), Clock()
    controller = MachineController(fake, clock)
    fake.fluidnc.power_cycle()  # DTR/RTS reset on open: our first $I/$$/? are lost.
    controller.connect()
    assert fake.writes[:2] == [b'$I\n', b'$$\n']
    for _ in range(5):
        step(controller, clock)
    assert controller.snapshot().firmware.phase is IdentificationPhase.FAILED
    assert controller.snapshot().report_units is None
    fake.fluidnc.starting()
    for _ in range(10):
        step(controller, clock)
    assert fake.writes.count(b'$I\n') == 1  # Not ready: Starting state and boot chatter.
    fake.fluidnc.finish_boot()
    until(controller, clock, lambda: controller.snapshot().manual.can_jog, 80)
    snap = controller.snapshot()
    assert snap.firmware.phase is IdentificationPhase.IDENTIFIED and snap.report_units == 'mm'
    assert snap.console.can_query  # A boot-time status timeout does not poison console attribution.


@pytest.mark.parametrize('custom', [None, b'My mill is ready\r\n'])
def test_reboot_while_idle_invalidates_and_reidentifies_after_quiet(custom):
    controller, fake, clock = connected()
    before = fake.writes.count(b'$I\n')
    boot_until_ready(controller, fake, clock, custom=custom)
    snap = controller.snapshot()
    assert not snap.manual.can_jog
    until(controller, clock, lambda: controller.snapshot().manual.can_jog, 80)
    assert fake.writes.count(b'$I\n') == before + 1
    assert controller.snapshot().firmware.motion_allowed


def test_custom_greeting_soft_reset_during_job_stops_and_reidentifies():
    controller, fake, clock = connected()
    fake.banner = b'\r\nMy mill is ready\r\n'
    text = 'G21G90G17G94\nF60\n' + ''.join(f'G1X{1 + i % 2}\n' for i in range(12)) + 'M2\n'
    controller.request_job(StartJobRequest(prepared(text), True))
    until(controller, clock, lambda: len(fake.job_writes) >= 3)
    sent = len(fake.job_writes)
    fake.inject(fake.banner)  # Another channel reset the board; greeting text is not trusted.
    step(controller, clock)
    snap = controller.snapshot()
    assert snap.job.phase in (JobPhase.FAILED, JobPhase.ABORTED) and snap.report_units is None
    assert fake.writes[-1] in (b'\x18', b'\x84')
    for _ in range(40):
        step(controller, clock)
    assert len(fake.job_writes) == sent
    assert controller.snapshot().firmware.phase is IdentificationPhase.IDENTIFIED


def test_boot_marker_during_jog_is_a_reset_without_extra_stop_bytes():
    controller, fake, clock = connected()
    controller.request_manual(JogRequest('Y', 10., 100.))
    until(controller, clock, lambda: any(write.startswith(b'$J=') for write in fake.writes))
    count = len(fake.writes)
    fake.fluidnc.power_cycle()
    step(controller, clock)
    snap = controller.snapshot()
    assert snap.manual.phase is ManualPhase.FAILED and snap.manual.stop_unverified
    assert snap.firmware.phase is IdentificationPhase.FAILED and snap.report_units is None
    assert not any(write in (b'\x18', b'\x84', b'$I\n') for write in fake.writes[count:])


def test_grbl_session_ignores_free_text_as_before():
    controller, fake, clock = connected('grbl')
    fake.inject(b'some vendor chatter\r\n')
    step(controller, clock)
    assert controller.snapshot().manual.can_jog and controller.snapshot().firmware.motion_allowed


@pytest.mark.parametrize('status', ['<Idle|MPos:0.000,0.000,0.000,0.000|FS:0,0>', '<Idle|MPos:0,0,0|A:>'])
def test_four_axis_or_empty_accessory_status_fails_closed(status):
    controller, fake, clock = connected()
    fake.auto_respond = False
    fake.inject(status.encode() + b'\r\n')
    step(controller, clock)
    assert not controller.snapshot().manual.can_jog


def test_parking_override_modal_word_refuses_jog_before_motion():
    controller, fake, clock = connected()
    fake.program_flow = 'M56'
    controller.request_manual(JogRequest('X', 1., 100.))
    until(controller, clock, lambda: controller.snapshot().manual.phase is ManualPhase.FAILED)
    assert not any(write.startswith(b'$J=') for write in fake.writes)


def test_disconnect_and_stop_paths_unchanged_for_fluidnc():
    controller, fake, clock = connected()
    controller.cancel_jog()
    controller.stop_job()
    controller.abort()
    controller.disconnect()
    assert controller.snapshot().connection is ConnectionState.DISCONNECTED and not fake.is_open
    assert no_macro_bytes(fake)


def test_console_settings_query_ignores_130_series_rows():
    """FluidNC $$ always lists $130-$132 after $13 (GRBL regression: test_console_control.py)."""
    controller, fake, clock = connected()
    controller.request_console(ConsoleRequest('$$'))
    until(controller, clock, lambda: controller.snapshot().console.phase is not ConsolePhase.PENDING)
    assert controller.snapshot().console.phase is ConsolePhase.COMPLETE, controller.snapshot().console


@pytest.mark.parametrize('firmware', ['grbl', 'fluidnc'])
def test_priority_race_at_a_startup_step_retries_without_losing_evidence(firmware):
    """A pause/stop intent racing the owner between its tick check and the next write retries."""
    controller, fake, clock = connected(firmware)
    controller.request_job(StartJobRequest(prepared(), True))
    until(controller, clock, lambda: controller._job.transaction == 'startup')
    calls = []

    def racing():
        calls.append(1)
        return len(calls) == 2  # The tick's own check passes; the guard before the write does not.
    controller.set_pause_check(racing)
    step(controller, clock)
    assert len(calls) >= 2 and controller.snapshot().job.phase is not JobPhase.FAILED
    controller.set_pause_check(lambda: False)
    until(controller, clock, lambda: controller.snapshot().job.phase in (JobPhase.COMPLETE, JobPhase.FAILED), 400)
    assert controller.snapshot().job.phase is JobPhase.COMPLETE, controller.snapshot().job.diagnostic
