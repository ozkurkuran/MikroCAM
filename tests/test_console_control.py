"""Read-only query ownership, wire evidence and quarantine regressions."""
import pytest

from mikrocam.machine.console_models import CONSOLE_COMMANDS, ConsolePhase, ConsoleRequest
from mikrocam.machine.manual_models import JogRequest
from mikrocam.machine.job_models import StartJobRequest
from mikrocam.machine.models import ConnectionState
from test_job_control import connected, step, until, prepared


def begin(command='$I'):
    controller, fake, clock = connected()
    controller.request_console(ConsoleRequest(command))
    step(controller, clock)
    return controller, fake, clock


@pytest.mark.parametrize('command', CONSOLE_COMMANDS)
def test_query_runs_on_existing_owner_and_unlocks_after_complete_batch(command):
    controller, fake, clock = connected()
    before = len(fake.writes)
    controller.request_console(ConsoleRequest(command))
    assert len(fake.writes) == before  # Admission lock cannot perform I/O.
    assert not controller.snapshot().manual.can_jog
    assert not controller.snapshot().job.can_start
    until(controller, clock, lambda: controller.snapshot().console.phase is ConsolePhase.COMPLETE)
    assert controller.snapshot().console.can_query
    assert controller.snapshot().manual.can_jog
    assert controller.snapshot().job.can_start
    if command != '?':
        assert (command + '\n').encode() in fake.writes[before:]
    assert fake.open_count == 1


@pytest.mark.parametrize('intent', [JogRequest('X', 1., 100.), StartJobRequest(prepared(), True)])
def test_query_reservation_blocks_manual_and_job(intent):
    controller, fake, clock = connected()
    controller.request_console(ConsoleRequest('$G'))
    with pytest.raises(ValueError):
        (controller.request_job if isinstance(intent, StartJobRequest) else controller.request_manual)(intent)
    with pytest.raises(ValueError):
        controller.request_console(ConsoleRequest('$N'))


@pytest.mark.parametrize('wire', [b'ok\r\nok\r\n', b'error:3\r\n', b'ALARM:2\r\n',
                                 b'Grbl 1.1h\r\n', b'\x00\r\n', b'<Idle|MPos:bad>\r\n'])
def test_fault_quarantines_without_invented_stop_and_late_ack_cannot_unlock(wire):
    controller, fake, clock = connected()
    fake.auto_respond = False
    controller.request_console(ConsoleRequest('$G'))
    step(controller, clock)
    before = len(fake.writes)
    fake.inject(wire)
    step(controller, clock)
    assert controller.snapshot().console.phase is ConsolePhase.FAILED
    diagnostic = controller.snapshot().console.diagnostic
    fake.inject(b'ok\r\n<Idle|MPos:0,0,0|WCO:0,0,0>\r\n')
    step(controller, clock)
    assert not controller.snapshot().console.can_query
    assert not controller.snapshot().manual.can_jog
    assert not controller.snapshot().job.can_start
    assert controller.snapshot().console.diagnostic == diagnostic
    assert not set(fake.writes[before:]) & {b'\x18', b'\x84', b'\x85', b'!', b'~'}


@pytest.mark.parametrize('rows', [b'ok\n', b'$13=1\nok\n', b'$13=0\n$13=0\nok\n',
                                  b'$13=no\nok\n', b'$13=0\nok\n$13=0\n'])
def test_settings_query_requires_unique_matching_units(rows):
    controller, fake, clock = connected()
    fake.auto_respond = False
    controller.request_console(ConsoleRequest('$$'))
    step(controller, clock)
    fake.inject(rows)
    step(controller, clock)
    assert controller.snapshot().console.phase is ConsolePhase.FAILED
    assert controller.snapshot().report_units is None
    assert controller.snapshot().machine_position_mm is None


def test_status_query_waits_for_new_causal_poll_without_duplicate_outstanding():
    controller, fake, clock = connected()
    fake.auto_respond = False
    controller._request_status()
    count = fake.writes.count(b'?')
    controller.request_console(ConsoleRequest('?'))
    fake.inject(b'<Idle|MPos:0,0,0|WCO:0,0,0>\n')
    step(controller, clock, .01)
    assert controller.snapshot().console.phase is ConsolePhase.PENDING
    assert fake.writes.count(b'?') == count
    step(controller, clock, .3)
    assert fake.writes.count(b'?') == count + 1
    fake.inject(b'<Idle|MPos:0,0,0|WCO:0,0,0>\n')
    step(controller, clock, .01)
    assert controller.snapshot().console.phase is ConsolePhase.COMPLETE


def test_deadline_and_stale_query_fail_without_retry():
    controller, fake, clock = connected()
    fake.auto_respond = False
    controller.request_console(ConsoleRequest('$G'))
    step(controller, clock)
    step(controller, clock, 3.1)
    assert controller.snapshot().console.phase is ConsolePhase.FAILED
    assert fake.writes.count(b'$G\n') == 1


@pytest.mark.parametrize('action', ['disconnect', 'abort', 'cancel_jog', 'stop_job'])
def test_priority_cancels_reserved_query_before_transmission(action):
    controller, fake, clock = connected()
    controller.request_console(ConsoleRequest('$I'))
    getattr(controller, action)()
    step(controller, clock)
    assert b'$I\n' not in fake.writes
    assert controller.snapshot().console.phase is ConsolePhase.FAILED


def test_priority_arriving_during_read_blocks_deferred_query():
    controller, fake, clock = connected()
    stop = [False]
    read = fake.read
    def interrupted_read(size):
        stop[0] = True
        return read(size)
    fake.read = interrupted_read
    controller.set_interrupt_check(lambda: stop[0])
    controller.request_console(ConsoleRequest('$I'))
    step(controller, clock)
    assert b'$I\n' not in fake.writes


def test_raw_fragments_and_final_failure_evidence_survive_disconnect():
    controller, fake, clock = connected()
    fake.auto_respond = False
    fake.inject(b'[MSG:par')
    step(controller, clock)
    fake.inject(b'tial]\r\n')
    step(controller, clock)
    chunks = [r.payload for r in controller.snapshot().wire.records if r.direction == 'RX']
    assert chunks[-2:] == [b'[MSG:par', b'tial]\r\n']
    controller.request_console(ConsoleRequest('$G'))
    fake.write_error = OSError('cable gone')
    step(controller, clock)
    snapshot = controller.snapshot()
    assert snapshot.connection is ConnectionState.ERROR
    assert snapshot.console.phase is ConsolePhase.FAILED
    assert any(r.payload == b'$G\n' and r.outcome == 'uncertain' for r in snapshot.wire.records)
    assert any(r.direction == 'IO' for r in snapshot.wire.records)
    controller.disconnect()
    assert controller.snapshot().console.diagnostic == snapshot.console.diagnostic
    assert controller.snapshot().wire.records == snapshot.wire.records


@pytest.mark.parametrize('count', [True, 1.0, 0, 2])
def test_write_count_must_be_exact_integer_and_is_logged_uncertain(count):
    controller, fake, clock = connected()
    fake.write = lambda data: count
    with pytest.raises(OSError):
        controller._send(b'?')
    record = controller.snapshot().wire.records[-1]
    assert record.payload == b'?' and record.outcome == 'uncertain'


def test_validation_rejection_logs_no_attempt_and_reconnect_resets_log():
    controller, fake, clock = connected()
    old = controller.snapshot().wire
    with pytest.raises(ValueError):
        controller._send(b'G0X100\n')
    assert controller.snapshot().wire == old
    controller.disconnect()
    assert controller.snapshot().wire == old
    controller.connect()
    assert controller.snapshot().wire.records[0].sequence == 1
    assert len(controller.snapshot().wire.records) == 2


def test_old_poll_timeout_cannot_be_relabelled_as_causal_console_response():
    controller, fake, clock = connected()
    fake.auto_respond = False
    controller._request_status()
    step(controller, clock, 2.01)
    # The normal monitor may retry, but its delayed old reply has no request identifier.
    fake.inject(b'<Idle|MPos:0,0,0|WCO:0,0,0>\n')
    step(controller, clock, .01)
    assert not controller.snapshot().console.can_query
    with pytest.raises(ValueError):
        controller.request_console(ConsoleRequest('?'))


def test_settings_deadline_even_when_status_remains_fresh():
    controller, fake, clock = connected()
    fake.auto_respond = False
    controller.request_console(ConsoleRequest('$G'))
    step(controller, clock)
    for _ in range(16):
        fake.inject(b'<Idle|MPos:0,0,0|WCO:0,0,0>\n')
        step(controller, clock, .2)
    assert controller.snapshot().console.phase is ConsolePhase.FAILED
    assert 'timed out' in controller.snapshot().console.diagnostic


@pytest.mark.parametrize('kind', ['manual', 'job'])
def test_operation_reservation_immediately_closes_console_eligibility(kind):
    controller, fake, clock = connected()
    if kind == 'manual':
        controller.request_manual(JogRequest('X', 1., 100.))
    else:
        controller.request_job(StartJobRequest(prepared(), True))
    assert not controller.snapshot().console.can_query
