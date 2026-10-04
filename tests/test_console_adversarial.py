"""Query arbitration and raw evidence at adversarial owner/transport boundaries."""
import pytest
from mikrocam.machine.console_models import ConsolePhase, ConsoleRequest
from mikrocam.machine.job_control import _PriorityPending
from mikrocam.machine.manual_models import JogRequest
from mikrocam.machine.models import ConnectionState, ManualPhase
from test_job_control import connected, step, until
from test_job_adversarial import BOUNDARIES, at_boundary

@pytest.mark.parametrize('boundary', BOUNDARIES)
def test_console_cannot_reserve_or_write_through_any_active_job_boundary(boundary):
    controller, fake, clock = at_boundary(boundary)
    before = list(fake.writes)
    assert not controller.snapshot().console.can_query
    with pytest.raises(ValueError):
        controller.request_console(ConsoleRequest('$I'))
    assert fake.writes == before

@pytest.mark.parametrize('phase', [ManualPhase.PREPARING, ManualPhase.VERIFYING, ManualPhase.MOVING, ManualPhase.CANCELLING])
def test_console_cannot_overlap_manual_preparation_motion_or_cancel(phase):
    controller, fake, clock = connected()
    controller.request_manual(JogRequest('X', 1.0, 100.0))
    if phase is ManualPhase.CANCELLING:
        until(controller, clock, lambda: controller.snapshot().manual.phase is ManualPhase.MOVING)
        controller.cancel_jog()
    elif phase is not ManualPhase.PREPARING:
        until(controller, clock, lambda: controller.snapshot().manual.phase is phase)
    before = list(fake.writes)
    with pytest.raises(ValueError):
        controller.request_console(ConsoleRequest('$I'))
    assert fake.writes == before

@pytest.mark.parametrize('outcome', ['success', 'partial', 'boolean', 'exception'])
def test_job_transport_outcomes_log_requested_bytes_without_retry(outcome):
    controller, fake, clock = connected()
    wire = b'G1X1F60\n'
    attempts = []

    def writer(data):
        attempts.append(data)
        if outcome == 'exception':
            raise OSError('job write disconnected')
        return len(data) if outcome == 'success' else True if outcome == 'boolean' else len(data) - 1
    fake.write_job = writer
    if outcome == 'success':
        controller._send_job(wire)
    else:
        with pytest.raises(OSError):
            controller._send_job(wire)
    record = controller.snapshot().wire.records[-1]
    assert record.direction == 'TX' and record.payload == wire
    assert record.outcome == ('complete' if outcome == 'success' else 'uncertain')
    assert attempts == [wire]

@pytest.mark.parametrize('mode', ['invalid', 'stop', 'pause'])
def test_job_rejection_or_priority_deferral_logs_no_transport_attempt(mode):
    controller, fake, clock = connected()
    before = controller.snapshot().wire
    attempts = []
    fake.write_job = lambda data: attempts.append(data) or len(data)
    if mode == 'invalid':
        wire = b'G1 X1\n'
        error = ValueError
    else:
        wire = b'G1X1\n'
        error = _PriorityPending
        (controller.set_interrupt_check if mode == 'stop' else controller.set_pause_check)(lambda: True)
    with pytest.raises(error):
        controller._send_job(wire)
    assert not attempts and controller.snapshot().wire == before

@pytest.mark.parametrize('chunk', [b'x' * 5000, b'\xff\r\n', bytearray(b'ok\r\n'), None, 'ok'])
def test_invalid_read_evidence_is_bounded_and_quarantines_pending_query(chunk):
    controller, fake, clock = connected()
    fake.auto_respond = False
    controller.request_console(ConsoleRequest('$I'))
    step(controller, clock)
    fake.read = lambda size: chunk
    step(controller, clock)
    snapshot = controller.snapshot()
    assert snapshot.console.phase is ConsolePhase.FAILED
    assert snapshot.report_units is None and snapshot.machine_position_mm is None
    records = snapshot.wire.records
    assert all((len(record.payload) <= 4096 for record in records))
    if type(chunk) is bytes:
        received = [record for record in records if record.direction == 'RX'][-1]
        assert received.payload == chunk[:4096]
        assert received.omitted_bytes == max(0, len(chunk) - 4096)
    controller.disconnect()
    assert controller.snapshot().wire.records == records

def test_read_and_failed_close_errors_both_survive_final_snapshot():
    controller, fake, clock = connected()
    controller.request_console(ConsoleRequest('$I'))
    fake.read_error = OSError('read lost')
    fake.close_error = OSError('close lost')
    step(controller, clock)
    result = controller.snapshot()
    assert result.connection is ConnectionState.ERROR
    assert result.console.phase is ConsolePhase.FAILED
    errors = [record.diagnostic for record in result.wire.records if record.direction == 'IO']
    assert any(('read lost' in text for text in errors))
    assert any(('close lost' in text for text in errors))

def test_worker_typed_query_priority_and_final_raw_evidence(qtbot):
    from mikrocam.machine.controller import MachineController
    from mikrocam.machine.fake import FakeGRBL
    from mikrocam.ui.machine_worker import MachineWorker
    fake = FakeGRBL()
    worker = MachineWorker(lambda: MachineController(fake))
    worker.start()
    try:
        qtbot.waitUntil(lambda: worker._latest.console.can_query, timeout=3000)
        assert not worker.submit('$I')
        assert worker.submit(ConsoleRequest('$I'))
        qtbot.waitUntil(lambda: worker._latest.console.phase is ConsolePhase.COMPLETE, timeout=3000)
        fake.auto_respond = False
        assert worker.submit(ConsoleRequest('$G'))
        qtbot.waitUntil(lambda: worker._latest.console.phase is ConsolePhase.PENDING, timeout=3000)
        worker.stop()
        assert worker.wait(4000)
        result = worker.final_snapshot
        assert result.console.phase is ConsolePhase.FAILED and (not result.console.can_query)
        assert sum(record.payload == b'$I\n' and record.outcome == 'complete'
                   for record in result.wire.records) == 2  # One session identification $I precedes settings (spec 042, UA-1).
        assert not fake.is_open
    finally:
        worker.stop()
        assert worker.wait(4000)

@pytest.mark.parametrize('action', ['abort', 'cancel_jog', 'stop_job', 'pause_job'])
def test_worker_pre_admission_priority_publishes_cancelled_query_not_silent_ready(action):
    from mikrocam.ui.machine_worker import MachineWorker
    controller, fake, clock = connected()
    worker = MachineWorker(lambda: pytest.fail('No separate controller expected'))
    worker._publish(controller.snapshot())
    assert worker.submit(ConsoleRequest('$I'))
    getattr(worker, action)()
    worker._process_intent(controller)
    step(controller, clock)
    worker._publish(controller.snapshot())
    result = worker._latest.console
    assert result.phase is ConsolePhase.FAILED and result.command == '$I'
    assert result.diagnostic and fake.writes.count(b'$I\n') == 1  # One session identification $I precedes settings (spec 042, UA-1).

def test_manual_reservation_immediately_closes_console_eligibility():
    controller, fake, clock = connected()
    controller.request_manual(JogRequest('X', 1.0, 100.0))
    assert not controller.snapshot().console.can_query

def test_worker_preserves_later_disconnect_wire_after_controller_failure(qtbot):
    from mikrocam.machine.controller import MachineController
    from mikrocam.machine.fake import FakeGRBL
    from mikrocam.ui.machine_worker import MachineWorker
    fake = FakeGRBL()
    fake.read_error = OSError('first read lost')
    fake.close_error = OSError('close remains broken')
    worker = MachineWorker(lambda: MachineController(fake))
    worker.start()
    try:
        assert worker.wait(4000)
        result = worker.final_snapshot
        assert result.connection is ConnectionState.ERROR
        assert 'first read lost' in result.diagnostic
        assert any((record.direction == 'IO' and 'Disconnect failed' in record.diagnostic for record in result.wire.records))
        assert any((record.direction == 'TX' for record in result.wire.records))
    finally:
        worker.stop()
        assert worker.wait(4000)
        fake.close_error = None
        fake.close()

def test_unexpected_owner_exception_preserves_query_and_existing_wire_evidence(qtbot):
    from mikrocam.machine.controller import MachineController
    from mikrocam.machine.fake import FakeGRBL
    from mikrocam.ui.machine_worker import MachineWorker
    fake = FakeGRBL()

    class BrokenIntentWorker(MachineWorker):

        def _process_intent(self, controller):
            if controller.snapshot().console.can_query:
                controller.request_console(ConsoleRequest('$I'))
                controller.tick()
                raise RuntimeError('unexpected owner intent failure')
    worker = BrokenIntentWorker(lambda: MachineController(fake))
    worker.start()
    try:
        assert worker.wait(4000)
        result = worker.final_snapshot
        assert result.connection is ConnectionState.ERROR
        assert 'unexpected owner intent failure' in result.diagnostic
        assert result.console.command == '$I'
        assert result.console.phase is ConsolePhase.FAILED and not result.console.can_query
        assert sum(record.payload == b'$I\n' and record.outcome == 'complete'
                   for record in result.wire.records) == 2  # One session identification $I precedes settings (spec 042, UA-1).
        assert not fake.is_open
    finally:
        worker.stop()
        assert worker.wait(4000)
