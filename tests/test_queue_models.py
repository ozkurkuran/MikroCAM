"""Offline queue snapshots and bounded explicit execution approval."""
from dataclasses import FrozenInstanceError
import pytest
from test_job_control import prepared
from mikrocam.machine.queue_models import QueueDraft, QueueEntry, StartQueueRequest


def test_offline_order_identity_and_sealed_source():
    draft = QueueDraft()
    job = prepared()
    first, second, third = (draft.add(job) for _ in range(3))
    assert len({first.key, second.key, third.key}) == 3
    assert first.job is job and first.job.source.sha256 == job.source.sha256
    draft.move(third.key, 0)
    assert draft.entries == (third, first, second)
    draft.remove(first.key)
    assert draft.entries == (third, second)
    with pytest.raises(FrozenInstanceError):
        first.key = "changed"
    draft.clear()
    assert draft.entries == ()
    assert draft.add(job).key not in {first.key, second.key, third.key}


@pytest.mark.parametrize("bad", [None, "G1 X1", True, object()])
def test_raw_or_unvalidated_job_never_enters_queue(bad):
    draft = QueueDraft()
    with pytest.raises(ValueError):
        draft.add(bad)
    assert not draft.entries


def test_queue_bound_and_unique_request_ids():
    draft = QueueDraft()
    for _ in range(32):
        draft.add(prepared())
    with pytest.raises(ValueError):
        draft.add(prepared())
    assert len(draft.entries) == 32
    with pytest.raises(ValueError):
        StartQueueRequest((draft.entries[0], draft.entries[0]), True)


@pytest.mark.parametrize("approval", [False, None, 1, "yes"])
def test_entire_queue_requires_exact_explicit_approval(approval):
    draft = QueueDraft()
    draft.add(prepared())
    with pytest.raises(ValueError):
        draft.start_request(approval)
    assert not draft.locked


def test_empty_queue_cannot_start():
    with pytest.raises(ValueError):
        QueueDraft().start_request(True)


@pytest.mark.parametrize("operation", ["add", "move", "remove", "clear", "start"])
def test_running_draft_is_immutable(operation):
    draft = QueueDraft()
    entry = draft.add(prepared())
    request = draft.start_request(True)
    assert request.entries == (entry,) and draft.locked
    calls = {"add": lambda: draft.add(prepared()), "move": lambda: draft.move(entry.key, 0),
             "remove": lambda: draft.remove(entry.key), "clear": draft.clear,
             "start": lambda: draft.start_request(True)}
    with pytest.raises(ValueError):
        calls[operation]()
    assert draft.entries == (entry,)
    draft.unlock()
    draft.clear()


@pytest.mark.parametrize("key,index", [("missing", 0), ("q1", -1), ("q1", 1), ("q1", True)])
def test_move_rejects_unknown_or_invalid_destination(key, index):
    draft = QueueDraft()
    first = draft.add(prepared())
    with pytest.raises(ValueError):
        draft.move(key, index)
    assert draft.entries == (first,)


@pytest.mark.parametrize("entries", [[], (), (object(),), tuple(QueueEntry(str(i), prepared()) for i in range(33))])
def test_execution_requires_bounded_exact_tuple(entries):
    with pytest.raises(ValueError):
        StartQueueRequest(entries, True)


def test_ready_or_running_evidence_cannot_settle_approved_draft():
    from mikrocam.machine.queue_models import QueueObservation, QueuePhase
    draft = QueueDraft()
    draft.add(prepared())
    draft.start_request(True)
    for phase in (QueuePhase.READY, QueuePhase.RUNNING, QueuePhase.PAUSED):
        with pytest.raises(ValueError): draft.settle(QueueObservation(phase=phase))
        assert draft.locked
