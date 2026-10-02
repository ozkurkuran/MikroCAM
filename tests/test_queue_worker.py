"""Typed queue intents use the existing owner and its priority mailbox."""
import pytest
from test_job_control import connected
from test_queue_control import loop_job
from mikrocam.machine.queue_models import QueueDraft, QueuePhase
from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.ui.machine_worker import MachineWorker


def request():
    draft = QueueDraft()
    for i in range(3):
        draft.add(loop_job(f"worker-{i}.nc"))
    return draft.start_request(True)


def test_typed_queue_reservation_admits_once_without_io(qapp):
    controller, fake, clock = connected()
    worker = MachineWorker(lambda: controller)
    worker._publish(controller.snapshot())
    before = tuple(fake.writes)
    approved = request()
    assert worker.submit(approved)
    assert not worker.submit(approved)
    worker._process_intent(controller)
    assert controller.snapshot().queue.phase is QueuePhase.RUNNING
    assert tuple(fake.writes) == before


@pytest.mark.parametrize("action", ["stop_job", "abort", "cancel_jog", "stop", "pause_job"])
def test_priority_discards_pending_queue_before_source_admission(qapp, action):
    controller, fake, clock = connected()
    worker = MachineWorker(lambda: controller)
    worker._publish(controller.snapshot())
    assert worker.submit(request())
    getattr(worker, action)()
    worker._process_intent(controller)
    assert controller.snapshot().queue.phase is QueuePhase.ABORTED
    assert not fake.job_writes and not controller._queue.active


def test_real_qt_owner_completes_queue_and_joins_with_results(qtbot):
    fake = FakeGRBL()
    worker = MachineWorker(lambda: MachineController(fake))
    seen = []
    worker.snapshot_ready.connect(seen.append)
    worker.start()
    try:
        qtbot.waitUntil(lambda: bool(seen) and seen[-1].queue.can_start, timeout=5000)
        assert worker.submit(request())
        qtbot.waitUntil(lambda: seen[-1].queue.phase is QueuePhase.COMPLETE, timeout=12000)
    finally:
        worker.stop()
        assert worker.wait(4000)
    assert not fake.is_open and fake.open_count == 1
    assert worker.final_snapshot.queue.phase is QueuePhase.COMPLETE
    assert len(worker.final_snapshot.queue.entries) == 3
