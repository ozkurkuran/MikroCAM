"""Explicit snapshot Add/approval and transparent ordered queue results."""
from dataclasses import replace
import pytest
from test_job_control import connected
from test_queue_control import loop_job
from mikrocam.machine.queue_models import QueueObservation, QueuePhase, QueueResult
from mikrocam.machine.job_models import JobObservation, JobPhase
from mikrocam.ui.queue_controls import QueueControls


@pytest.fixture
def controls(qtbot):
    value = QueueControls()
    qtbot.addWidget(value)
    controller, fake, clock = connected()
    value.update_snapshot(controller.snapshot())
    return value, controller, fake


def test_candidate_changes_do_not_invalidate_added_snapshot(controls):
    ui, controller, fake = controls
    first = loop_job("first.nc")
    ui.set_candidate(first)
    before = tuple(fake.writes)
    ui.add_button.click()
    sealed = ui.draft.entries[0]
    ui.set_candidate(None)
    assert not ui.add_button.isEnabled()
    ui.set_candidate(loop_job("second.nc"))
    ui.add_button.click()
    assert ui.draft.entries[0] is sealed and sealed.job is first
    assert ui.table.rowCount() == 2
    assert "first.nc" in ui.table.item(0, 0).text()
    assert first.source.sha256 in ui.table.item(0, 0).toolTip()
    assert tuple(fake.writes) == before


def test_offline_move_remove_and_clear(controls):
    ui, controller, fake = controls
    for name in ("a.nc", "b.nc"):
        ui.set_candidate(loop_job(name))
        ui.add_button.click()
    ui.table.selectRow(1)
    ui.up_button.click()
    assert ui.draft.entries[0].job.source.name == "b.nc"
    ui.table.selectRow(0)
    ui.remove_button.click()
    assert len(ui.draft.entries) == 1
    ui.clear_button.click()
    assert not ui.draft.entries and ui.table.rowCount() == 0


def test_start_requires_whole_queue_approval_and_locks_pending(controls):
    ui, controller, fake = controls
    ui.set_candidate(loop_job("approved.nc"))
    ui.add_button.click()
    assert not ui.start_button.isEnabled()
    seen = []
    ui.start_requested.connect(seen.append)
    ui.confirm.setChecked(True)
    assert ui.start_button.isEnabled()
    ui.start_button.click()
    assert len(seen) == 1 and seen[0].mechanical_confirmed is True
    assert ui.draft.locked and not ui.confirm.isChecked()
    assert not any(b.isEnabled() for b in (ui.start_button, ui.add_button, ui.clear_button))
    assert ui.stop_button.isEnabled()
    ui.start_rejected("Admission changed before owner reservation")
    assert not ui.draft.locked
    assert "Admission changed" in ui.status_label.text()


def test_terminal_results_retire_ids_and_require_explicit_new_add(controls):
    ui, controller, fake = controls
    ui.set_candidate(loop_job("completed.nc"))
    ui.add_button.click()
    entry = ui.draft.entries[0]
    ui.confirm.setChecked(True)
    ui.start_button.click()
    result = QueueResult(entry, JobObservation(phase=JobPhase.COMPLETE,
                         source_name=entry.job.source.name, source_sha256=entry.job.source.sha256))
    state = replace(controller.snapshot(), queue=QueueObservation(
                    phase=QueuePhase.COMPLETE, entries=(result,), can_start=True))
    ui.update_snapshot(state)
    assert not ui.draft.entries and not ui.draft.locked
    assert ui.table.rowCount() == 1 and "complete" in ui.table.item(0, 1).text().lower()
    ui.add_button.click()
    assert ui.draft.entries[0].key != entry.key


def test_escape_cannot_hide_pending_queue_controls(controls):
    ui, controller, fake = controls
    ui.set_candidate(loop_job("pending.nc"))
    ui.add_button.click()
    ui.confirm.setChecked(True)
    ui.start_button.click()
    ui.show()
    ui.reject()
    assert ui.isVisible()
    ui.start_rejected("Cancelled before admission")
    ui.reject()
    assert not ui.isVisible()


def test_changed_live_candidate_cannot_be_added(controls):
    ui, controller, fake = controls
    ui.set_candidate(loop_job("stale.nc"))
    ui._validator = lambda job: False
    ui.add_button.click()
    assert not ui.draft.entries


def test_disconnect_placeholder_cannot_unlock_admitted_queue(controls):
    from mikrocam.machine.models import MachineSnapshot
    ui, controller, fake = controls
    ui.set_candidate(loop_job("shutdown.nc"))
    ui.add_button.click()
    entry = ui.draft.entries[0]
    ui.confirm.setChecked(True)
    ui.start_button.click()
    running = replace(controller.snapshot(), queue=QueueObservation(
        phase=QueuePhase.RUNNING, entries=(QueueResult(entry),), active_key=entry.key, can_stop=True))
    ui.update_snapshot(running)
    assert ui.draft.locked and not ui._pending_keys
    ui.update_snapshot(MachineSnapshot())
    assert ui.draft.locked and not ui.add_button.isEnabled()
    ui.update_snapshot(replace(MachineSnapshot(), queue=QueueObservation(
        phase=QueuePhase.ABORTED, entries=(QueueResult(entry),))))
    assert not ui.draft.locked


def test_pending_disconnect_waits_for_owner_cancellation_evidence(controls):
    from mikrocam.machine.models import MachineSnapshot
    ui, controller, fake = controls
    ui.set_candidate(loop_job("pending-close.nc"))
    ui.add_button.click()
    ui.confirm.setChecked(True)
    ui.start_button.click()
    entry = ui.draft.entries[0]
    ui.update_snapshot(MachineSnapshot())
    assert ui.draft.locked and ui._pending_keys
    ui.update_snapshot(replace(MachineSnapshot(), queue=QueueObservation(
        phase=QueuePhase.ABORTED, entries=(QueueResult(entry),))))
    assert not ui.draft.locked and not ui._pending_keys
