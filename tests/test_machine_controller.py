"""Read-only GRBL lifecycle and coordinate evidence, without Qt or hardware."""
import pytest

from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.models import ConnectionState, MachineState


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


# Spec 042 (UA-1): the read-only $I identification precedes $$; settle it before settings.
IDENTIFIED = b'[VER:1.1h.20190830:]\r\n[OPT:V,15,128]\r\nok\r\n'


def session(auto=False):
    clock = Clock()
    fake = FakeGRBL(auto_respond=auto)
    controller = MachineController(fake, clock)
    controller.connect()
    if not auto:
        receive(controller, fake, IDENTIFIED)
    return controller, fake, clock


def receive(controller, fake, data):
    fake.inject(data)
    controller.tick()
    return controller.snapshot()


def units(controller, fake, inches=False):
    receive(controller, fake, b'$13=1\r\nok\r\n' if inches else b'$13=0\r\nok\r\n')


def test_explicit_lifecycle_exact_allowlist_and_clean_reconnect():
    clock = Clock()
    fake = FakeGRBL()
    controller = MachineController(fake, clock)
    assert fake.writes == [] and not fake.is_open
    assert controller.snapshot().connection is ConnectionState.DISCONNECTED
    controller.connect()
    controller.tick()
    assert controller.snapshot().connection is ConnectionState.CONNECTED
    assert controller.snapshot().state is MachineState.IDLE
    assert fake.writes == [b'$I\n', b'$$\n', b'?']  # Identification first (042, UA-1).
    with pytest.raises(ValueError):
        controller.connect()
    controller.disconnect()
    assert not fake.is_open
    assert controller.snapshot().machine_position_mm is None
    controller.disconnect()
    controller.connect()
    assert controller.snapshot().report_units is None
    controller.tick()
    controller.disconnect()
    assert set(fake.writes) == {b'$I\n', b'$$\n', b'?'}


@pytest.mark.parametrize('inches', [False, True])
@pytest.mark.parametrize('direct', ['MPos', 'WPos'])
def test_units_and_both_coordinate_systems(inches, direct):
    controller, fake, _ = session()
    units(controller, fake, inches)
    state = receive(controller, fake, f'<Run|{direct}:1,2,3|WCO:0.1,-0.2,0.3>\n'.encode())
    scale = 25.4 if inches else 1.0
    actual = state.machine_position_mm if direct == 'MPos' else state.work_position_mm
    derived = state.work_position_mm if direct == 'MPos' else state.machine_position_mm
    expected = (0.9, 2.2, 2.7) if direct == 'MPos' else (1.1, 1.8, 3.3)
    assert actual == pytest.approx(tuple(x * scale for x in (1, 2, 3)), abs=1e-9)
    assert derived == pytest.approx(tuple(x * scale for x in expected), abs=1e-9)
    assert state.state is MachineState.RUNNING and not state.stale


def test_units_require_fresh_status_and_never_reinterpret_old_report():
    controller, fake, _ = session()
    state = receive(controller, fake, b'<Idle|MPos:1,2,3|WCO:1,1,1>\n')
    assert state.machine_position_mm is None
    units(controller, fake)
    assert controller.snapshot().machine_position_mm is None
    state = receive(controller, fake, b'<Idle|MPos:4,5,6>\n')
    assert state.machine_position_mm == (4, 5, 6)
    assert state.work_position_mm is None


def test_intermittent_offset_is_session_scoped_and_units_change_clears_it():
    controller, fake, _ = session()
    units(controller, fake)
    receive(controller, fake, b'<Idle|MPos:1,2,3|WCO:1,1,1>\n')
    state = receive(controller, fake, b'<Idle|MPos:3,4,5>\n')
    assert state.work_position_mm == (2, 3, 4)
    receive(controller, fake, b'$13=1\n')
    assert controller.snapshot().machine_position_mm is None
    state = receive(controller, fake, b'<Idle|MPos:1,2,3>\n')
    assert state.work_offset_mm is None and state.work_position_mm is None


def test_stale_invalidates_offset_and_unknown_state_is_not_idle():
    controller, fake, clock = session()
    units(controller, fake)
    receive(controller, fake, b'<Idle|MPos:1,2,3|WCO:1,1,1>\n')
    clock.now = 2.0
    controller.tick()
    state = controller.snapshot()
    assert state.stale and state.machine_position_mm is None
    assert state.work_offset_mm is None and state.state is MachineState.UNKNOWN
    state = receive(controller, fake, b'<Future:7|MPos:4,5,6>\n')
    assert state.state is MachineState.UNKNOWN and state.raw_state == 'Future:7'
    assert state.machine_position_mm == (4, 5, 6) and state.work_position_mm is None


def test_reset_reacquires_units_without_overlapping_old_settings():
    controller, fake, _ = session()
    units(controller, fake)
    receive(controller, fake, b'<Idle|MPos:1,2,3|WCO:1,1,1>\n')
    state = receive(controller, fake, b"Grbl 1.1h ['$' for help]\n")
    assert state.report_units is None and state.machine_position_mm is None
    assert fake.writes.count(b'$$\n') == 2
    units(controller, fake, True)
    state = receive(controller, fake, b'<Idle|MPos:1,0,0>\n')
    assert state.machine_position_mm == (25.4, 0, 0) and state.work_offset_mm is None


@pytest.mark.parametrize('invalid', [b'<Idle|MPos:NaN,2,3>\n', b'<Idle|MPos:1,2>\n',
                                    b'<Idle|MPos:1,2,3|WPos:0,0,0>\n', b'<' + b'x' * 600 + b'\n'])
def test_invalid_status_removes_authoritative_coordinates(invalid):
    controller, fake, _ = session()
    units(controller, fake)
    receive(controller, fake, b'<Idle|MPos:1,2,3|WCO:1,1,1>\n')
    state = receive(controller, fake, invalid)
    assert state.machine_position_mm is None and state.work_offset_mm is None
    assert state.state is MachineState.UNKNOWN and state.diagnostic


def test_one_outstanding_status_timeout_retries_without_reopen():
    controller, fake, clock = session()
    clock.now = 0.25
    controller.tick()
    assert fake.writes.count(b'?') == 1
    clock.now = 2
    controller.tick()
    assert fake.writes.count(b'?') == 2
    assert controller.snapshot().stale and fake.open_count == 1
    clock.now = 3
    controller.tick()
    assert 'settings' in controller.snapshot().diagnostic.lower()
    assert controller.snapshot().report_units is None
    controller.disconnect()
    assert not fake.is_open


@pytest.mark.parametrize('failure', ['open', 'read', 'write', 'short', 'close'])
def test_io_failure_invalidates_and_closes(failure):
    fake = FakeGRBL()
    if failure == 'open':
        fake.open_error = OSError('busy')
    if failure == 'write':
        fake.write_error = OSError('unplugged')
    if failure == 'short':
        fake.short_write = True
    controller = MachineController(fake, Clock())
    controller.connect()
    if failure == 'read':
        controller.tick()
        fake.read_error = OSError('unplugged')
        controller.tick()
    if failure == 'close':
        fake.close_error = OSError('close failure')
        controller.disconnect()
    state = controller.snapshot()
    assert state.connection is ConnectionState.ERROR
    assert state.machine_position_mm is None and not fake.is_open
    assert state.diagnostic


@pytest.mark.parametrize('line', [b'error:8\n', b'ALARM:1\n', b'$13=NaN\n'])
def test_errors_do_not_leave_safe_state_or_unknown_units_as_zero(line):
    controller, fake, _ = session()
    state = receive(controller, fake, line)
    assert state.state is not MachineState.IDLE
    assert state.machine_position_mm is None and state.report_units is None
    assert state.diagnostic


def test_settings_partial_response_timeout_discards_unit_evidence():
    controller, fake, clock = session()
    receive(controller, fake, b'$13=0\n<Idle|MPos:1,2,3>\n')
    clock.now = 3.0
    controller.tick()
    assert controller.snapshot().report_units is None
    assert controller.snapshot().machine_position_mm is None


def test_axis_travel_settings_do_not_overwrite_report_units():
    controller, fake, _ = session()
    state = receive(controller, fake, b'$13=0\n$130=200.000\n$131=200.000\n$132=100.000\nok\n')
    assert state.report_units == 'mm'
    state = receive(controller, fake, b'<Idle|MPos:1,2,3>\n')
    assert state.machine_position_mm == (1, 2, 3)


@pytest.mark.parametrize('expire_before_read', [True, False])
def test_expired_settings_cannot_be_revived_by_late_rows(expire_before_read):
    controller, fake, clock = session()
    clock.now = 3.0
    if expire_before_read:
        controller.tick()
    state = receive(controller, fake, b'$13=0\nok\n<Idle|MPos:1,2,3>\n')
    assert state.report_units is None and state.machine_position_mm is None


def test_delayed_report_does_not_reuse_expired_offset_on_same_tick():
    controller, fake, clock = session()
    units(controller, fake)
    receive(controller, fake, b'<Idle|MPos:1,2,3|WCO:1,1,1>\n')
    clock.now = 2.0
    state = receive(controller, fake, b'<Idle|MPos:4,5,6>\n')
    assert state.machine_position_mm == (4, 5, 6)
    assert state.work_position_mm is None and state.work_offset_mm is None
    assert not state.stale and 'stale' not in state.diagnostic.lower()


def test_settings_units_remain_provisional_until_successful_ack():
    controller, fake, _ = session()
    state = receive(controller, fake, b'$13=0\n<Idle|MPos:1,2,3>\n')
    assert state.report_units is None and state.machine_position_mm is None
    state = receive(controller, fake, b'error:8\n')
    assert state.report_units is None and state.machine_position_mm is None


def test_corrupt_chunk_cannot_hide_reset_and_keep_old_unit_evidence():
    controller, fake, _ = session()
    units(controller, fake)
    receive(controller, fake, b'<Idle|MPos:1,2,3|WCO:1,1,1>\n')
    receive(controller, fake, b"Grbl 1.1h ['$' for help]\n" + b'x' * 600 + b'\n')
    state = receive(controller, fake, b'<Idle|MPos:1,2,3>\n')
    assert state.report_units is None and state.machine_position_mm is None


def test_bounded_diagnostic_and_chunk_processing():
    controller, fake, _ = session()
    units(controller, fake)
    receive(controller, fake, b'<Idle|MPos:')
    assert controller.snapshot().machine_position_mm is None
    state = receive(controller, fake, b'1,2,3>\r\n')
    assert state.machine_position_mm == (1, 2, 3)
    state = receive(controller, fake, b'[MSG:' + b'a' * 400 + b']\n')
    assert len(state.diagnostic) <= 256
