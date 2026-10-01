"""Explicit selection is inert and sealed into single-job/queue start intents."""
from mikrocam.ui.job_controls import JobControls
from mikrocam.ui.queue_controls import QueueControls
from mikrocam.machine.job_models import StreamingMode
from test_job_control import connected, prepared
from test_queue_control import loop_job


def test_single_job_mode_selection_requires_start_and_is_locked_pending(qtbot):
    ui = JobControls()
    qtbot.addWidget(ui)
    controller, fake, clock = connected()
    ui.set_snapshot(controller.snapshot(), True)
    ui.set_job(prepared())
    seen = []
    ui.start_requested.connect(seen.append)
    assert ui.mode_combo.currentData() is StreamingMode.SEND_RESPONSE
    ui.mode_combo.setCurrentIndex(1)
    assert not seen and not fake.job_writes
    ui.confirm_checkbox.setChecked(True)
    ui.start_button.click()
    assert seen[0].streaming_mode is StreamingMode.CHARACTER_COUNTING
    assert not ui.mode_combo.isEnabled()


def test_queue_mode_is_immutable_start_intent(qtbot):
    ui = QueueControls()
    qtbot.addWidget(ui)
    controller, fake, clock = connected()
    ui.update_snapshot(controller.snapshot())
    ui.set_candidate(loop_job('queued.nc'))
    ui.add_button.click()
    ui.mode_combo.setCurrentIndex(1)
    seen = []
    ui.start_requested.connect(seen.append)
    ui.confirm.setChecked(True)
    ui.start_button.click()
    assert seen[0].streaming_mode is StreamingMode.CHARACTER_COUNTING
    assert not ui.mode_combo.isEnabled() and not fake.job_writes
