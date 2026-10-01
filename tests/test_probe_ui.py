from dataclasses import replace
from types import SimpleNamespace
import pytest
from PyQt6 import QtWidgets
from mikrocam.machine.models import MachineSnapshot, ConnectionState, MachineState
from mikrocam.machine.probe_models import ProbeObservation, ProbePhase
from mikrocam.ui.probe_controls import ProbeDialog


def make_dialog(qtbot):
    snapshot = MachineSnapshot(
        connection=ConnectionState.CONNECTED,
        state=MachineState.IDLE,
        machine_position_mm=(0.0, 0.0, 5.0),
        work_offset_mm=(0.0, 0.0, 0.0),
        stale=False,
        probe=ProbeObservation(can_start=True),
    )
    calls = []
    panel = SimpleNamespace(
        last_snapshot=snapshot,
        submit_probe=lambda r: calls.append(r) or True,
        stop_probe=lambda: calls.append("stop"),
    )
    dialog = ProbeDialog(panel)
    qtbot.addWidget(dialog)
    return dialog, panel, calls


def fill(dialog):
    values = dict(
        x_min=0,
        x_max=1,
        nx=2,
        y_min=0,
        y_max=1,
        ny=2,
        safe_z=5,
        min_z=-1,
        probe_feed=50,
        travel_feed=100,
        timeout=30,
    )
    for axis in "xyz":
        values["machine_min_" + axis] = -10
        values["machine_max_" + axis] = 10
    for key, value in values.items():
        dialog.fields[key].setText(str(value))


def test_explicit_review_edit_invalidation_and_typed_start(qtbot):
    dialog, panel, calls = make_dialog(qtbot)
    assert all(not field.text() for field in dialog.fields.values())
    dialog.review_grid()
    assert dialog.plan is None and not calls
    fill(dialog)
    dialog.review_grid()
    assert dialog.plan.initial_machine_mm == (0.0, 0.0, 5.0)
    assert dialog.viewer.map is None and dialog.viewer.table.columnCount() == 2
    assert not dialog.viewer.save_button.isEnabled()
    assert dialog.start_button.isEnabled()
    dialog.fields["nx"].setText("3")
    assert dialog.plan is None and not dialog.start_button.isEnabled()
    dialog.review_grid()
    dialog.start_grid()
    assert len(calls) == 1 and calls[0].plan.grid.count == 6
    assert not dialog.close() and not dialog.fields["nx"].isEnabled()
    dialog.stop_button.click()
    assert calls[-1] == "stop"


def test_changed_live_binding_and_busy_terminal_unlock(qtbot):
    dialog, panel, calls = make_dialog(qtbot)
    fill(dialog)
    dialog.review_grid()
    changed = replace(panel.last_snapshot, machine_position_mm=(1.0, 0.0, 5.0))
    dialog.update_snapshot(changed)
    assert dialog.plan is None and not dialog.start_button.isEnabled()
    dialog.update_snapshot(
        replace(
            changed,
            probe=ProbeObservation(
                phase=ProbePhase.PROBING, completed=0, total=4, can_stop=True
            ),
        )
    )
    assert not dialog.close()
    assert not dialog.review_button.isEnabled()
    dialog.update_snapshot(
        replace(changed, probe=ProbeObservation(phase=ProbePhase.ABORTED))
    )
    assert dialog.close() and not calls


@pytest.mark.parametrize(
    "key,text",
    [
        ("nx", "2.5"),
        ("safe_z", "nan"),
        ("probe_feed", "0"),
        ("min_z", "-200"),
        ("machine_max_z", "4"),
    ],
)
def test_invalid_explicit_inputs_never_submit(qtbot, key, text):
    dialog, panel, calls = make_dialog(qtbot)
    fill(dialog)
    dialog.fields[key].setText(text)
    dialog.review_grid()
    dialog.start_grid()
    assert dialog.plan is None and not calls


def test_unavailable_or_stale_binding_never_reviews(qtbot):
    dialog, panel, calls = make_dialog(qtbot)
    fill(dialog)
    for changes in (
        {"stale": True},
        {"work_offset_mm": None},
        {"machine_position_mm": None},
    ):
        dialog.update_snapshot(replace(panel.last_snapshot, **changes))
        dialog.review_grid()
        assert dialog.plan is None and not calls


def test_rejected_submission_needs_new_review(qtbot):
    dialog, panel, calls = make_dialog(qtbot)
    fill(dialog)
    dialog.review_grid()
    panel.submit_probe = lambda request: False
    dialog.start_grid()
    assert not dialog.busy and dialog.plan is None
    assert "rejected" in dialog.status_label.text().lower()


def test_old_snapshot_does_not_unlock_pending_and_offline_map_does_not_arm(qtbot):
    from test_probe_view import sample

    dialog, panel, calls = make_dialog(qtbot)
    dialog.set_map(sample("aborted"))
    assert not dialog.start_button.isEnabled() and not calls
    fill(dialog)
    dialog.review_grid()
    dialog.start_grid()
    dialog.update_snapshot(panel.last_snapshot)
    assert dialog.busy and not dialog.close()
    dialog.update_snapshot(
        replace(panel.last_snapshot, connection=ConnectionState.DISCONNECTED)
    )
    assert not dialog.busy and not dialog.start_button.isEnabled()


def test_offline_historical_map_survives_unchanged_live_snapshot(qtbot):
    from test_probe_view import sample

    dialog, panel, calls = make_dialog(qtbot)
    live = sample()
    snapshot = replace(
        panel.last_snapshot,
        probe=ProbeObservation(
            phase=ProbePhase.COMPLETE, completed=4, total=4, map=live
        ),
    )
    dialog.update_snapshot(snapshot)
    historical = sample("aborted")
    dialog.set_map(historical)
    dialog.update_snapshot(snapshot)
    assert dialog.viewer.map == historical and not calls
    new = replace(live, heights_mm=(2.0, 3.0, 4.0, 5.0))
    dialog.update_snapshot(replace(snapshot, probe=replace(snapshot.probe, map=new)))
    assert dialog.viewer.map == new


@pytest.mark.parametrize('phase', [ProbePhase.PREPARING, ProbePhase.PROBING])
def test_modal_file_controls_disabled_while_acquiring(qtbot, phase):
    from mikrocam.core.probe_map import ProbeGrid, ProbeMap
    dialog, panel, calls = make_dialog(qtbot)
    partial = ProbeMap(ProbeGrid((0., 1.), (0., 1.)), (0., None, None, None),
                       (0., 0., 0.), 'incomplete', 'simulated')
    dialog.update_snapshot(replace(panel.last_snapshot, probe=ProbeObservation(
        phase=phase, map=partial, completed=1, total=4, can_stop=True)))
    assert dialog.stop_button.isEnabled()
    assert not dialog.viewer.load_button.isEnabled()
    assert not dialog.viewer.save_button.isEnabled()
    dialog.update_snapshot(replace(panel.last_snapshot, probe=ProbeObservation(
        phase=ProbePhase.ABORTED, map=partial, completed=1, total=4)))
    assert dialog.viewer.save_button.isEnabled()


def test_modal_save_disabled_while_start_request_pending(qtbot):
    from mikrocam.core.probe_map import ProbeGrid, ProbeMap
    dialog, panel, calls = make_dialog(qtbot)
    dialog.set_map(ProbeMap(ProbeGrid((0., 1.), (0., 1.)), (0., 0., 0., 0.),
                            (0., 0., 0.), 'complete', 'simulated'))
    fill(dialog)
    dialog.review_grid()
    dialog.set_map(ProbeMap(ProbeGrid((0., 1.), (0., 1.)), (0., 0., 0., 0.),
                            (0., 0., 0.), 'complete', 'simulated'))
    dialog.start_grid()
    assert dialog.busy and dialog.stop_button.isEnabled()
    assert not dialog.viewer.save_button.isEnabled()
