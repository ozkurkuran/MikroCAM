"""Cancel/abort failures must never masquerade as a verified physical stop."""
import pytest

from mikrocam.machine.manual_models import JogRequest
from mikrocam.machine.models import ConnectionState, ManualPhase
from test_machine_manual_controller import connected, drive


def moving():
    controller, fake, clock = connected()
    controller.request_manual(JogRequest('X', 10, 100))
    drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.MOVING)
    return controller, fake, clock


def test_cancel_preempts_move_and_waits_for_fresh_terminal_status():
    controller, fake, clock = moving()
    controller.cancel_jog()
    assert fake.writes[-1] == b'\x85'
    assert controller.snapshot().manual.phase is ManualPhase.CANCELLING
    result = drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.COMPLETE)
    assert not result.manual.stop_unverified
    assert result.machine_position_mm[0] < 10
    assert b'!' not in fake.writes and b'~' not in fake.writes


def test_abort_uses_reset_only_after_verified_empty_startup_blocks():
    controller, fake, _ = moving()
    controller.abort()
    assert fake.writes[-1] == b'\x18'
    state = controller.snapshot()
    assert state.manual.phase is ManualPhase.ABORTED
    assert state.manual.stop_unverified and state.machine_position_mm is None
    assert not state.manual.can_jog


def test_abort_without_startup_evidence_uses_door_and_warns_about_parking():
    controller, fake, _ = connected()
    controller.abort()
    assert fake.writes[-1] == b'\x84' and b'\x18' not in fake.writes
    state = controller.snapshot()
    assert state.manual.stop_unverified and 'parking' in state.manual.diagnostic.lower()


def test_cancel_timeout_attempts_reset_and_keeps_stop_unverified():
    controller, fake, clock = moving()
    fake.auto_respond = False
    fake._incoming.clear()
    controller.cancel_jog()
    clock.now += 2
    controller.tick()
    state = controller.snapshot()
    assert b'\x85' in fake.writes and b'\x18' in fake.writes
    assert state.manual.stop_unverified and not state.manual.can_jog
    assert state.manual.phase in (ManualPhase.FAILED, ManualPhase.ABORTED)


@pytest.mark.parametrize('failure', ['read', 'write', 'stale', 'reset', 'alarm', 'corrupt'])
def test_failure_during_owned_move_locks_and_invalidates(failure):
    controller, fake, clock = moving()
    fake.auto_respond = False
    fake._incoming.clear()
    if failure == 'read':
        fake.read_error = OSError('cable unplugged')
    elif failure == 'write':
        fake.write_error = OSError('cable unplugged')
        clock.now += 2
    elif failure == 'stale':
        clock.now += 2
    elif failure == 'reset':
        fake.inject(b"Grbl 1.1h ['$' for help]\n")
    elif failure == 'alarm':
        fake.inject(b'ALARM:1\n')
    else:
        fake.inject(b'x' * 513 + b'\n')
    controller.tick()
    state = controller.snapshot()
    assert not state.manual.can_jog and state.machine_position_mm is None
    assert state.manual.phase in (ManualPhase.FAILED, ManualPhase.ABORTED)
    assert state.manual.stop_unverified


def test_disconnect_cancels_owned_jog_before_closing(monkeypatch):
    controller, fake, clock = moving()
    read = fake.read

    def timed_read(size):
        clock.now += .25
        return read(size)

    monkeypatch.setattr(fake, 'read', timed_read)
    controller.disconnect()
    assert b'\x85' in fake.writes
    assert not fake.is_open and controller.snapshot().connection is ConnectionState.DISCONNECTED
    assert not controller.snapshot().manual.stop_unverified


def test_read_only_disconnect_still_has_no_stop_writes():
    controller, fake, _ = connected()
    before = tuple(fake.writes)
    controller.disconnect()
    assert tuple(fake.writes) == before


def test_failed_abort_delivery_is_visible_after_close():
    controller, fake, _ = moving()
    fake.write_error = OSError('cable unplugged')
    controller.abort()
    controller.disconnect()
    state = controller.snapshot()
    assert state.manual.stop_unverified and 'unplugged' in state.manual.diagnostic
    assert not fake.is_open
