"""Single-owner firmware identification on the existing controller (spec 042)."""
import pytest

from mikrocam.machine.console_models import ConsoleRequest
from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.firmware import FirmwareFamily, IdentificationPhase
from mikrocam.machine.job_models import JobPhase, StartJobRequest, StreamingMode
from mikrocam.machine.manual_models import JogRequest, SelectG54Request, ZeroRequest
from mikrocam.machine.models import ConnectionState, MachineState, ManualPhase
from mikrocam.machine.probe_models import StartProbeGridRequest
from mikrocam.machine.queue_models import QueueEntry, StartQueueRequest
from test_job_control import prepared
from test_probe_controller import plan

MOTION_PREFIXES = (b'$J=', b'G10', b'G54', b'G21', b'G1', b'G0', b'M5', b'\x85')


class Clock:
    now = 0.

    def __call__(self):
        return self.now


def session(firmware='grbl', auto=True, **kwargs):
    clock = Clock()
    fake = FakeGRBL(auto_respond=auto, firmware=firmware, **kwargs)
    controller = MachineController(fake, clock)
    controller.connect()
    return controller, fake, clock


def steps(controller, clock, count=8, seconds=.1):
    for _ in range(count):
        clock.now += seconds
        controller.tick()
    return controller.snapshot()


def receive(controller, fake, data):
    fake.inject(data)
    controller.tick()
    return controller.snapshot()


def test_connect_sends_identification_before_settings_and_status():
    controller, fake, clock = session(auto=False)
    assert fake.writes == [b'$I\n', b'$$\n', b'?']
    firmware = controller.snapshot().firmware
    assert firmware.phase is IdentificationPhase.PENDING and not firmware.motion_allowed


def test_grbl_profile_is_identified_and_preserves_existing_motion_eligibility():
    controller, fake, clock = session()
    snap = steps(controller, clock, 1)
    assert snap.firmware.phase is IdentificationPhase.IDENTIFIED
    assert snap.firmware.capabilities.family is FirmwareFamily.GRBL
    assert snap.firmware.capabilities.streaming_rx_budget == 128
    assert snap.firmware.evidence == ('[VER:1.1h:FakeGRBL]', '[OPT:V,15,128]')
    assert snap.manual.can_jog and snap.job.can_start and snap.probe.can_start and snap.console.can_query


@pytest.mark.parametrize('profile,family', [('grblhal', FirmwareFamily.GRBLHAL),
                                            ('fluidnc', FirmwareFamily.FLUIDNC),
                                            ('unknown', FirmwareFamily.UNKNOWN)])
def test_unsupported_profiles_disable_every_motion_owner_without_writes(profile, family):
    controller, fake, clock = session(profile)
    snap = steps(controller, clock)
    assert snap.firmware.capabilities.family is family
    expected = IdentificationPhase.FAILED if family is FirmwareFamily.UNKNOWN else IdentificationPhase.IDENTIFIED
    assert snap.firmware.phase is expected and snap.firmware.capabilities.note
    assert snap.connection is ConnectionState.CONNECTED and snap.state is MachineState.IDLE
    assert snap.report_units == 'mm' and not snap.stale
    assert not (snap.manual.can_jog or snap.manual.can_zero or snap.manual.can_select_g54)
    assert not snap.job.can_start and not snap.probe.can_start and not snap.queue.can_start
    assert snap.console.can_query  # Read-only diagnosis remains available (UA-7).
    before = list(fake.writes)
    for request in (JogRequest('X', 1, 100), ZeroRequest(('X', 'Y')), SelectG54Request()):
        with pytest.raises(ValueError):
            controller.request_manual(request)
    with pytest.raises(ValueError):
        controller.request_job(StartJobRequest(prepared(), True))
    with pytest.raises(ValueError):
        controller.request_probe(StartProbeGridRequest(plan(controller)))
    with pytest.raises(ValueError):
        controller.request_queue(StartQueueRequest((QueueEntry('a', prepared()),), True))
    steps(controller, clock, 20)
    assert not any(w.startswith(MOTION_PREFIXES) for w in fake.writes[len(before):])
    controller.request_console(ConsoleRequest('$I'))
    steps(controller, clock, 6)
    assert controller.snapshot().console.phase.value == 'complete'


def test_stop_paths_remain_available_for_unknown_firmware():
    controller, fake, clock = session('unknown')
    steps(controller, clock)
    controller.cancel_jog()
    controller.stop_job()
    controller.abort()
    controller.disconnect()
    assert controller.snapshot().connection is ConnectionState.DISCONNECTED and not fake.is_open


def test_settings_row_before_identification_ok_fails_closed():
    controller, fake, clock = session(auto=False)
    receive(controller, fake, b'[VER:1.1h.20190830:]\r\n[OPT:V,15,128]\r\n')
    pending = controller.snapshot()
    assert pending.firmware.phase is IdentificationPhase.PENDING
    assert not pending.console.can_query and not pending.manual.can_jog
    receive(controller, fake, b'$13=0\r\n<Idle|MPos:0,0,0|WCO:0,0,0>\r\n')
    snap = controller.snapshot()
    assert snap.firmware.phase is IdentificationPhase.FAILED  # Settings row before $I ok.
    assert snap.report_units is None and not snap.manual.can_jog
    assert 'order' in snap.firmware.diagnostic


def test_fragmented_identification_reply_keeps_ack_ownership():
    controller, fake, clock = session(auto=False)
    for chunk in (b'[VER:1.1h.2019', b'0830:]\r\n[OPT:V,1', b'5,128]\r\no', b'k\r\n'):
        receive(controller, fake, chunk)
    assert controller.snapshot().firmware.phase is IdentificationPhase.IDENTIFIED
    receive(controller, fake, b'$13=0\r\nok\r\n<Idle|MPos:0,0,0|WCO:0,0,0>\r\n')
    snap = controller.snapshot()
    assert snap.report_units == 'mm' and snap.manual.can_jog


def test_identification_error_is_unknown_but_settings_still_complete():
    controller, fake, clock = session(auto=False)
    receive(controller, fake, b'error:3\r\n$13=0\r\nok\r\n<Idle|MPos:0,0,0|WCO:0,0,0>\r\n')
    snap = controller.snapshot()
    assert snap.firmware.phase is IdentificationPhase.FAILED
    assert snap.firmware.capabilities.family is FirmwareFamily.UNKNOWN
    assert 'error:3' in snap.firmware.diagnostic
    assert snap.report_units == 'mm' and not snap.manual.can_jog and snap.console.can_query


def test_identification_timeout_fails_closed_without_retry():
    controller, fake, clock = session(auto=False)
    clock.now = 2.9
    controller.tick()
    assert controller.snapshot().firmware.phase is IdentificationPhase.PENDING
    clock.now = 3.0
    controller.tick()
    snap = controller.snapshot()
    assert snap.firmware.phase is IdentificationPhase.FAILED and 'timed out' in snap.firmware.diagnostic
    assert snap.report_units is None
    clock.now = 10.
    controller.tick()
    assert fake.writes.count(b'$I\n') == 1


def test_oversized_or_non_ascii_identification_evidence_fails_identification():
    controller, fake, clock = session(auto=False)
    receive(controller, fake, b''.join(b'[AXS:%d]\r\n' % i for i in range(33)) + b'ok\r\n')
    assert controller.snapshot().firmware.phase is IdentificationPhase.FAILED


def test_msg_lines_are_not_identity_evidence_and_keep_existing_diagnosis():
    controller, fake, clock = session(auto=False)
    receive(controller, fake, b"[MSG:'$H'|'$X' to unlock]\r\n[VER:1.1h.20190830:]\r\n[OPT:V,15,128]\r\nok\r\n")
    snap = controller.snapshot()
    assert snap.firmware.phase is IdentificationPhase.IDENTIFIED
    assert snap.firmware.evidence == ('[VER:1.1h.20190830:]', '[OPT:V,15,128]')


def test_reset_on_open_reidentifies_with_banner_evidence():
    controller, fake, clock = session()
    fake._incoming.clear()
    fake.inject(fake.banner)
    snap = steps(controller, clock, 8)
    assert fake.writes[:5] == [b'$I\n', b'$$\n', b'?', b'$I\n', b'$$\n']
    assert snap.firmware.phase is IdentificationPhase.IDENTIFIED
    assert snap.firmware.banner == "Grbl 1.1h ['$' for help]" and snap.manual.can_jog


def test_consistent_mid_session_reset_keeps_identity_and_sends_only_settings():
    controller, fake, clock = session()
    steps(controller, clock)
    count = fake.writes.count(b'$I\n')
    fake.inject(fake.banner)
    snap = steps(controller, clock)
    assert fake.writes.count(b'$I\n') == count and fake.writes.count(b'$$\n') == 2
    assert snap.firmware.phase is IdentificationPhase.IDENTIFIED and snap.manual.can_jog


def test_reset_to_different_firmware_reidentifies_and_disables_motion():
    controller, fake, clock = session()
    steps(controller, clock)
    replacement = FakeGRBL(firmware='grblhal')
    fake.build_reply, fake.banner = replacement.build_reply, replacement.banner
    fake.inject(fake.banner)
    controller.tick()
    assert controller.snapshot().firmware.phase is IdentificationPhase.PENDING
    assert not controller.snapshot().manual.can_jog
    snap = steps(controller, clock)
    assert fake.writes.count(b'$I\n') == 2
    assert snap.firmware.capabilities.family is FirmwareFamily.GRBLHAL and not snap.manual.can_jog


def test_grblhal_reset_banner_interrupts_an_owned_job():
    controller, fake, clock = session()
    steps(controller, clock)
    controller.request_job(StartJobRequest(prepared(), True))
    steps(controller, clock, 3)
    fake.inject(b"GrblHAL 1.1f ['$' or '$HELP' for help]\r\n")
    snap = steps(controller, clock, 1)
    assert snap.job.phase is JobPhase.FAILED and 'reset' in snap.job.diagnostic.lower()


def test_disconnect_and_failure_clear_the_identity():
    controller, fake, clock = session()
    steps(controller, clock)
    controller.disconnect()
    assert controller.snapshot().firmware.phase is IdentificationPhase.NONE
    controller.connect()
    steps(controller, clock)
    fake.read_error = OSError('unplugged')
    snap = steps(controller, clock, 1)
    assert snap.connection is ConnectionState.ERROR
    assert snap.firmware.phase is IdentificationPhase.NONE


def test_identification_exchange_is_in_the_wire_log():
    controller, fake, clock = session()
    snap = steps(controller, clock, 1)
    tx = [record.payload for record in snap.wire.records if record.direction == 'TX']
    rx = b''.join(record.payload for record in snap.wire.records if record.direction == 'RX')
    assert tx[:3] == [b'$I\n', b'$$\n', b'?'] and b'[VER:1.1h:FakeGRBL]' in rx


def test_character_counting_requires_session_budget():
    controller, fake, clock = session(build_reply=b'[VER:1.1h.20190830:]\r\nok\r\n')
    snap = steps(controller, clock)
    assert snap.firmware.capabilities.streaming_rx_budget is None and snap.manual.can_jog
    controller.request_job(StartJobRequest(prepared(), True, StreamingMode.CHARACTER_COUNTING))
    snap = steps(controller, clock, 40)
    assert snap.job.phase is JobPhase.FAILED and 'budget' in snap.job.diagnostic
    assert fake.job_writes == []


def test_character_counting_rejects_changed_build_evidence():
    controller, fake, clock = session()
    steps(controller, clock)
    fake.build_reply = b'[VER:1.1h.20190830:]\r\n[OPT:V,15,128]\r\nok\r\n'
    controller.request_job(StartJobRequest(prepared(), True, StreamingMode.CHARACTER_COUNTING))
    snap = steps(controller, clock, 40)
    assert snap.job.phase is JobPhase.FAILED and 'changed' in snap.job.diagnostic
    assert fake.job_writes == []


def test_character_counting_uses_identified_grbl_budget():
    controller, fake, clock = session()
    steps(controller, clock)
    controller.request_job(StartJobRequest(prepared(), True, StreamingMode.CHARACTER_COUNTING))
    for _ in range(80):
        steps(controller, clock, 1)
        if controller._job.stream is not None:
            break
    assert controller._job.stream.capacity == 128


def test_manual_phase_unchanged_when_motion_refused():
    controller, fake, clock = session('fluidnc')
    steps(controller, clock)
    with pytest.raises(ValueError):
        controller.request_manual(JogRequest('X', 1, 100))
    assert controller.snapshot().manual.phase in (ManualPhase.FAILED, ManualPhase.READY)
