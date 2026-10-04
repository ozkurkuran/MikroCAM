"""Finite manual jog transactions against real domain parsing and a scripted fake."""
import pytest

from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.manual_models import JogRequest
from mikrocam.machine.models import ConnectionState, MachineState, ManualPhase


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


def connected(**kwargs):
    clock = Clock()
    fake = FakeGRBL(**kwargs)
    controller = MachineController(fake, clock)
    controller.connect()
    controller.tick()
    return controller, fake, clock


def drive(controller, clock, predicate, steps=160):
    for _ in range(steps):
        if predicate(controller.snapshot()):
            return controller.snapshot()
        clock.now += .25
        controller.tick()
    pytest.fail(f'Operation did not reach expected phase: {controller.snapshot()}')


def complete(controller, clock):
    result = drive(controller, clock, lambda snap: snap.manual.phase in (
        ManualPhase.COMPLETE, ManualPhase.FAILED, ManualPhase.ABORTED))
    assert result.manual.phase is ManualPhase.COMPLETE, result.manual.diagnostic
    return result


@pytest.mark.parametrize('axis', ['X', 'Y', 'Z'])
@pytest.mark.parametrize('distance', [-10., -.1, .1, 10.])
@pytest.mark.parametrize('report_units', ['mm', 'inch'])
def test_one_jog_has_explicit_mm_modes_off_preparation_and_verified_endpoint(axis, distance, report_units):
    controller, fake, clock = connected(report_units=report_units)
    before = controller.snapshot().machine_position_mm
    controller.request_manual(JogRequest(axis, distance, 100))
    assert not controller.snapshot().manual.can_jog
    result = complete(controller, clock)
    target = list(before)
    target['XYZ'.index(axis)] += distance
    assert result.machine_position_mm == pytest.approx(target, abs=.005)
    jogs = [item for item in fake.writes if item.startswith(b'$J=')]
    assert jogs == [f'$J=G21 G91 {axis}{distance:g} F100\n'.encode()]
    assert fake.writes.index(b'$N\n') < fake.writes.index(b'M5 M9\n') < fake.writes.index(jogs[0])
    assert b'$G\n' in fake.writes
    assert all(not item.startswith((b'M3', b'M4', b'$N0=', b'$N1=')) for item in fake.writes)
    assert result.manual.can_jog


@pytest.mark.parametrize('state', ['Run', 'Jog', 'Hold:0', 'Hold:1', 'Alarm', 'Door:0',
                                  'Home', 'Check', 'Sleep', 'Unknown', 'Vendor:9'])
def test_nonidle_state_cannot_start_manual_action(state):
    controller, fake, _ = connected(status=f'<{state}|MPos:0,0,0|WCO:0,0,0>\n'.encode())
    before = tuple(fake.writes)
    with pytest.raises(ValueError):
        controller.request_manual(JogRequest('X', 1, 100))
    assert tuple(fake.writes) == before
    assert not controller.snapshot().manual.can_jog


def test_stale_timestamp_rechecked_on_request_without_waiting_for_poll():
    controller, fake, clock = connected()
    clock.now = 2
    before = tuple(fake.writes)
    with pytest.raises(ValueError):
        controller.request_manual(JogRequest('X', 1, 100))
    assert tuple(fake.writes) == before


def test_duplicate_request_cannot_queue_a_second_jog():
    controller, fake, clock = connected()
    controller.request_manual(JogRequest('X', 1, 100))
    with pytest.raises(ValueError):
        controller.request_manual(JogRequest('Y', 1, 100))
    complete(controller, clock)
    assert len([line for line in fake.writes if line.startswith(b'$J=')]) == 1


@pytest.mark.parametrize('blocks', [('G21', ''), ('', 'M3S1000'), ('G0X10', 'M5')])
def test_nonempty_startup_blocks_block_all_motion_and_are_never_overwritten(blocks):
    controller, fake, clock = connected(startup_blocks=blocks)
    controller.request_manual(JogRequest('X', 1, 100))
    result = drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.FAILED)
    assert 'startup' in result.manual.diagnostic.lower()
    assert not any(line.startswith((b'$J=', b'$N0=', b'$N1=')) for line in fake.writes)
    assert b'\x18' not in fake.writes


def test_no_action_until_settings_read_is_successfully_acknowledged():
    controller, fake, _ = connected(auto_respond=False)
    fake.inject(b'$13=0\n<Idle|MPos:0,0,0|WCO:0,0,0>\n')
    controller.tick()
    with pytest.raises(ValueError):
        controller.request_manual(JogRequest('X', 1, 100))
    assert set(fake.writes) <= {b'?', b'$$\n', b'$I\n'}  # One session identification $I precedes settings (spec 042, UA-1).


class AlterReply(FakeGRBL):
    def __init__(self, trigger, replacement):
        super().__init__()
        self.trigger, self.replacement = trigger, replacement

    def write(self, data):
        if data == self.trigger:
            auto = self.auto_respond
            self.auto_respond = False
            count = super().write(data)
            self.auto_respond = auto
            self.inject(self.replacement)
            return count
        return super().write(data)


def altered(trigger, replacement):
    fake, clock = AlterReply(trigger, replacement), Clock()
    controller = MachineController(fake, clock)
    controller.connect()
    controller.tick()
    return controller, fake, clock


@pytest.mark.parametrize('reply', [b'$N0=\nok\n', b'$N0=\n$N0=\n$N1=\nok\n',
                                  b'error:8\n', b'$N0=\n$N1=\n'])
def test_incomplete_or_rejected_startup_query_never_authorizes_motion(reply):
    controller, fake, clock = altered(b'$N\n', reply)
    controller.request_manual(JogRequest('X', 1, 100))
    result = drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.FAILED)
    assert not result.manual.can_jog
    assert not any(line.startswith(b'$J=') for line in fake.writes)


@pytest.mark.parametrize('reply', [b'error:8\n', b'', b'ok\nok\n'])
def test_output_off_failure_or_duplicate_ack_cannot_advance_to_jog(reply):
    controller, fake, clock = altered(b'M5 M9\n', reply)
    controller.request_manual(JogRequest('X', 1, 100))
    drive(controller, clock, lambda snap: snap.manual.phase in (ManualPhase.FAILED, ManualPhase.ABORTED))
    assert not any(line.startswith(b'$J=') for line in fake.writes)
    assert not controller.snapshot().manual.can_jog


def test_modal_output_on_evidence_prevents_motion_despite_off_ack():
    controller, fake, clock = altered(b'$G\n', b'[GC:G0 G54 G17 G21 G90 G94 M3 M9 T0 F0 S1000]\nok\n')
    controller.request_manual(JogRequest('X', 1, 100))
    drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.FAILED)
    assert not any(line.startswith(b'$J=') for line in fake.writes)


def test_ack_alone_or_old_idle_position_does_not_complete_move():
    controller, fake, clock = altered(b'$J=G21 G91 X1 F100\n', b'ok\n')
    controller.request_manual(JogRequest('X', 1, 100))
    drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.MOVING)
    assert controller.snapshot().manual.phase is not ManualPhase.COMPLETE
    # Simulator did not move, so a later old-position Idle must fail, not authorize another jog.
    result = drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.FAILED)
    assert not result.manual.can_jog


def test_unsolicited_ack_taints_manual_control_and_never_changes_read_only_state_to_idle():
    controller, fake, _ = connected()
    fake.inject(b'ok\n')
    controller.tick()
    assert not controller.snapshot().manual.can_jog
    with pytest.raises(ValueError):
        controller.request_manual(JogRequest('X', 1, 100))


def test_state_change_during_preparation_is_rechecked_before_transmitting_motion():
    controller, fake, clock = altered(b'$G\n',
        b'[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]\nok\n<Run|MPos:0,0,0|WCO:0,0,0>\n')
    controller.request_manual(JogRequest('X', 1, 100))
    drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.FAILED)
    assert not any(line.startswith(b'$J=') for line in fake.writes)
