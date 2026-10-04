"""Offscreen Laser CAM workflow, detached workers and stale-result prevention."""
import tempfile
import threading
from pathlib import Path

import pytest
from PyQt6 import QtCore, QtWidgets
from shapely.geometry import box


class FakeHost:
    def __init__(self):
        from mikrocam.core.laser_job import PlanarRegion
        from mikrocam.core.laser_paths import CopperFeatures
        self.window = QtWidgets.QMainWindow()
        self.features = CopperFeatures(PlanarRegion.from_geometry(box(0, 0, 2, 2)))
        self.snapshots = []
        self.publications = []
        self.panel = None
        # Never created unless a test saves; keeps the host independent of user data.
        self.database_path = Path(tempfile.gettempdir()) / f'mikrocam-db-{id(self)}' / 'laser_recipe_db.json'

    def recipe_database_path(self):
        return self.database_path

    def source_names(self):
        return ('copper', 'outline')

    def active_name(self):
        return 'copper'

    def snapshot(self, source_name, outline_name=None):
        assert QtCore.QThread.currentThread() == self.window.thread()
        self.snapshots.append((source_name, outline_name))
        return self.features

    def publish_preview(self, plan):
        assert QtCore.QThread.currentThread() == self.window.thread()
        self.publications.append(plan)
        return 'Laser preview'

    def parent_widget(self):
        return self.window

    def existing_panel(self):
        return self.panel

    def remember_panel(self, panel):
        self.panel = panel


@pytest.fixture
def panel(qtbot):
    from mikrocam.ui.laser_cam import LaserCamPanel
    host = FakeHost()
    value = LaserCamPanel(host)
    host.window.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, value)
    qtbot.addWidget(host.window)
    yield value, host
    value.shutdown()


def recipe():
    from mikrocam.core.laser_job import LaserPass, LaserRecipe
    return LaserRecipe('explicit', (LaserPass('first', 20, 250, 30, 100),))


def completed_plan(job, options, features, cancelled):
    from mikrocam.core.laser_paths import LaserPath, LaserPlan
    assert QtCore.QThread.currentThread() != QtWidgets.QApplication.instance().thread()
    return LaserPlan(job, options, (LaserPath(((0, 0), (2, 0)), 'contour'),))


def test_explicit_recipe_required_and_visible_errors(panel):
    value, host = panel
    value.generate()
    assert not value.busy and not host.snapshots
    assert 'cihaz türü seçin' in value.status_label.text().lower()
    assert value.last_plan is None


def test_generation_snapshots_gui_inputs_and_publishes_on_gui(panel, qtbot, monkeypatch):
    import mikrocam.ui.laser_worker as worker
    monkeypatch.setattr(worker, 'plan_laser', completed_plan)
    value, host = panel
    value.set_recipe(recipe())
    value.outline_combo.setCurrentText('outline')
    value.origin_x.setValue(1)
    value.translation_y.setValue(12)
    value.rotation.setValue(90)
    value.mirror_x.setChecked(True)
    value.hatch_enabled.setChecked(True)
    value.hatch_spacing.setValue(0.25)
    value.hatch_angle.setValue(30)
    value.cross_hatch.setChecked(True)
    value.generate()
    qtbot.waitUntil(lambda: not value.busy)
    assert host.snapshots == [('copper', 'outline')]
    assert len(host.publications) == 1
    assert value.last_plan is host.publications[0]
    assert value.last_plan.job.recipe == recipe()
    assert value.last_plan.job.placement.origin == (1, 0)
    assert value.last_plan.job.placement.translation == (0, 12)
    assert value.last_plan.job.placement.rotation_deg == 90
    assert value.last_plan.job.placement.mirror_x
    assert value.last_plan.options.spacing_mm == 0.25
    assert value.last_plan.options.angle_deg == 30 and value.last_plan.options.cross_hatch
    assert 'Laser preview' in value.status_label.text()


def test_real_planner_workflow_uses_detached_source_and_shared_placement(panel, qtbot):
    value, host = panel
    source_hex = host.features.copper.wkb_hex
    value.set_recipe(recipe())
    value.origin_x.setValue(1)
    value.translation_y.setValue(12)
    value.rotation.setValue(90)
    value.mirror_x.setChecked(True)
    value.hatch_enabled.setChecked(True)
    value.hatch_spacing.setValue(0.5)
    value.hatch_angle.setValue(45)
    value.cross_hatch.setChecked(True)
    value.generate()
    qtbot.waitUntil(lambda: not value.busy)
    assert len(host.publications) == 1
    plan = value.last_plan
    assert plan is host.publications[0]
    assert {path.role for path in plan.paths} == {'contour', 'hatch'}
    assert {path.hatch_family for path in plan.paths if path.role == 'hatch'} == {0, 1}
    assert plan.job.region.wkb_hex == source_hex == host.features.copper.wkb_hex
    source_bounds = plan.job.placement.inverse().apply_points(plan.paths[0].points)
    assert min(point[0] for point in source_bounds) == pytest.approx(0)
    assert max(point[0] for point in source_bounds) == pytest.approx(2)


def test_recipe_load_and_changed_inputs_invalidate_success(panel, qtbot, monkeypatch, tmp_path):
    import mikrocam.ui.laser_worker as worker
    from mikrocam.core.laser_json import recipe_to_json
    monkeypatch.setattr(worker, 'plan_laser', completed_plan)
    value, host = panel
    path = tmp_path / 'recipe.json'
    path.write_text(recipe_to_json(recipe()), encoding='utf-8')
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileName', lambda *a, **k: (str(path), ''))
    value.recipe_button.click()
    assert 'explicit' in value.recipe_label.text()
    value.generate()
    qtbot.waitUntil(lambda: not value.busy)
    assert value.last_plan is not None
    value.rotation.setValue(15)
    assert value.last_plan is None
    value.generate()
    qtbot.waitUntil(lambda: not value.busy)
    value.set_recipe(recipe())
    assert value.last_plan is None
    path.write_text('{invalid', encoding='utf-8')
    value.recipe_button.click()
    assert 'error' in value.status_label.text().lower()


@pytest.mark.parametrize('action', ['cancel', 'close', 'hide', 'change', 'shutdown'])
def test_cancel_close_change_and_shutdown_discard_late_success(panel, qtbot, monkeypatch, action):
    import mikrocam.ui.laser_worker as worker
    entered, release = threading.Event(), threading.Event()
    calls = []
    def late(job, options, features, cancelled):
        calls.append(job)
        entered.set()
        assert release.wait(2)
        return completed_plan(job, options, features, cancelled)
    monkeypatch.setattr(worker, 'plan_laser', late)
    value, host = panel
    value.set_recipe(recipe())
    value.generate()
    qtbot.waitUntil(entered.is_set)
    assert value.busy and value.cancel_button.isEnabled()
    assert not value.generate_button.isEnabled() and not value.source_combo.isEnabled()
    value.generate()
    assert len(calls) == 1
    if action == 'cancel':
        value.cancel_button.click()
    elif action == 'close':
        value.close()
    elif action == 'hide':
        host.window.show()
        value.hide()
    elif action == 'change':
        value.rotation.setValue(10)  # programmatic change still invalidates a disabled control
    else:
        release.set()
        value.shutdown()
    release.set()
    qtbot.waitUntil(lambda: not value.busy)
    assert not host.publications and value.last_plan is None
    assert value._worker is None


def test_worker_error_is_visible_and_allows_retry(panel, qtbot, monkeypatch):
    import mikrocam.ui.laser_worker as worker
    value, host = panel
    value.set_recipe(recipe())
    def fail(*args):
        raise ValueError('Explicit board required')
    monkeypatch.setattr(worker, 'plan_laser', fail)
    value.generate()
    qtbot.waitUntil(lambda: not value.busy)
    assert 'Explicit board required' in value.status_label.text()
    assert value.generate_button.isEnabled() and not host.publications
    monkeypatch.setattr(worker, 'plan_laser', completed_plan)
    value.generate()
    qtbot.waitUntil(lambda: not value.busy)
    assert len(host.publications) == 1


def test_joined_workers_queued_signals_cannot_release_a_new_worker(panel, qtbot, monkeypatch):
    import mikrocam.ui.laser_worker as worker
    first_entered, second_entered = threading.Event(), threading.Event()
    first_release, second_release = threading.Event(), threading.Event()
    calls = []
    def controlled(job, options, features, cancelled):
        calls.append(job)
        entered, release = ((first_entered, first_release) if len(calls) == 1
                            else (second_entered, second_release))
        entered.set()
        assert release.wait(2)
        return completed_plan(job, options, features, cancelled)
    monkeypatch.setattr(worker, 'plan_laser', controlled)
    value, host = panel
    value.set_recipe(recipe())
    value.generate()
    qtbot.waitUntil(first_entered.is_set)
    first_release.set()
    value.shutdown()
    value.generate()
    qtbot.waitUntil(second_entered.is_set)
    assert value.busy and value._worker.isRunning()
    assert not host.publications
    second_release.set()
    qtbot.waitUntil(lambda: not value.busy)
    assert len(host.publications) == 1


def test_cooperative_cancellation_exception_leaves_no_preview(panel, qtbot, monkeypatch):
    import mikrocam.ui.laser_worker as worker
    from mikrocam.core.laser_paths import PlanningCancelled
    entered = threading.Event()
    def cooperate(job, options, features, cancelled):
        entered.set()
        while not cancelled():
            threading.Event().wait(0.001)
        raise PlanningCancelled()
    monkeypatch.setattr(worker, 'plan_laser', cooperate)
    value, host = panel
    value.set_recipe(recipe())
    value.generate()
    qtbot.waitUntil(entered.is_set)
    value.cancel()
    qtbot.waitUntil(lambda: not value.busy)
    assert 'Cancelled' in value.status_label.text()
    assert not host.publications


def test_cancel_after_completion_before_queued_delivery_finishes_cancelled(panel, qtbot, monkeypatch):
    import mikrocam.ui.laser_worker as worker
    monkeypatch.setattr(worker, 'plan_laser', completed_plan)
    value, host = panel
    value.set_recipe(recipe())
    value.generate()
    assert value._worker.wait(2000)  # completed is queued, not delivered on GUI yet
    value.cancel()
    qtbot.waitUntil(lambda: not value.busy)
    assert not host.publications and value.last_plan is None
    assert value.status_label.text() == 'Cancelled.'


def test_short_window_keeps_generate_cancel_and_status_outside_scrolling_inputs(panel, qtbot):
    value, host = panel
    host.window.resize(480, 300)
    host.window.show()
    qtbot.waitUntil(value.isVisible)
    assert isinstance(value.input_scroll, QtWidgets.QScrollArea)
    assert value.input_scroll.widget() is value.input_controls
    assert value.input_scroll.verticalScrollBar().maximum() > 0
    for control in (value.generate_button, value.cancel_button, value.status_label):
        assert not value.input_scroll.isAncestorOf(control)
        assert host.window.rect().contains(control.mapTo(host.window, control.rect().bottomRight()))


def test_snapshot_and_publication_errors_do_not_retain_a_plan(panel, qtbot, monkeypatch):
    import mikrocam.ui.laser_worker as worker
    monkeypatch.setattr(worker, 'plan_laser', completed_plan)
    value, host = panel
    value.set_recipe(recipe())
    def fail(*args):
        raise ValueError('source unavailable')
    original = host.snapshot
    monkeypatch.setattr(host, 'snapshot', fail)
    value.generate()
    assert not value.busy and 'source unavailable' in value.status_label.text()
    monkeypatch.setattr(host, 'snapshot', original)
    monkeypatch.setattr(host, 'publish_preview', fail)
    value.generate()
    qtbot.waitUntil(lambda: not value.busy)
    assert value.last_plan is None and 'source unavailable' in value.status_label.text()


def test_open_reuses_dock_after_close(qtbot, monkeypatch):
    import mikrocam.ui.laser_cam as ui
    host = FakeHost()
    monkeypatch.setattr(ui, 'LaserCamHost', lambda app: host)
    qtbot.addWidget(host.window)
    first = ui.open_laser_cam(object())
    first.close()
    second = ui.open_laser_cam(object())
    assert first is second is host.panel
    assert not second.isHidden()
    second.shutdown()


def test_editor_draft_and_interlace_are_used_without_stale_recipe_fallback(panel, qtbot):
    from mikrocam.core.laser_job import LaserPass, LaserRecipe
    value, host = panel
    value.set_recipe(recipe())
    editor = value.recipe_editor
    editor.table.item(0, 2).setText('123.45678901234567')
    editor.add_pass()
    for column, text in enumerate(('second', '40', '500', '60', '200')):
        editor.table.item(1, column).setText(text)
    value.interlace_n.setValue(3)
    value.hatch_enabled.setChecked(True)
    value.generate()
    qtbot.waitUntil(lambda: not value.busy)
    expected = LaserRecipe('explicit', (LaserPass('first', 20, 123.45678901234567, 30, 100),
                                        LaserPass('second', 40, 500, 60, 200)))
    assert value.last_plan.job.recipe == expected
    assert value.last_plan.options.interlace_n == 3
    assert len(value.last_plan.pass_plans) == 2
    assert '2 passes' in value.status_label.text()
    assert len(host.publications) == 1
    editor.table.item(0, 1).setText('')
    assert value.last_plan is None and value.recipe is None
    value.generate()
    assert not value.busy and len(host.publications) == 1
    assert 'error' in value.status_label.text().lower()


@pytest.mark.parametrize('change', ['recipe', 'interlace', 'device'])
def test_programmatic_editor_or_interlace_edits_cancel_immutable_running_request(panel, qtbot, monkeypatch, change):
    import mikrocam.ui.laser_worker as worker
    entered, release = threading.Event(), threading.Event()
    requests = []
    def delayed(job, options, features, cancelled):
        requests.append(job)
        entered.set()
        assert release.wait(2)
        return completed_plan(job, options, features, cancelled)
    monkeypatch.setattr(worker, 'plan_laser', delayed)
    value, host = panel
    value.set_recipe(recipe())
    value.generate()
    qtbot.waitUntil(entered.is_set)
    assert not value.recipe_editor.isEnabled()
    if change == 'recipe':
        value.recipe_editor.table.item(0, 1).setText('50')
    elif change == 'device':
        value.recipe_editor.device_editor.kind.setCurrentIndex(value.recipe_editor.device_editor.kind.findData('diode'))
    else:
        value.interlace_n.setValue(4)
    release.set()
    qtbot.waitUntil(lambda: not value.busy)
    assert requests[0].recipe == recipe()
    assert value.last_plan is None and not host.publications


def test_panel_save_cancel_and_failure_preserve_draft_and_existing_file(panel, monkeypatch, tmp_path):
    import mikrocam.ui.laser_cam as ui
    from mikrocam.core.laser_json import recipe_from_json
    value, _host = panel
    value.set_recipe(recipe())
    value.recipe_editor.table.item(0, 2).setText('321.1234567890123')
    current = value.recipe_editor.get_recipe()
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName', lambda *a, **k: ('', ''))
    value.save_recipe_button.click()
    assert value.recipe_editor.get_recipe() == current
    target = tmp_path / 'recipe.json'
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName', lambda *a, **k: (str(target), ''))
    value.save_recipe_button.click()
    assert recipe_from_json(target.read_text(encoding='utf-8')) == current
    previous = target.read_bytes()
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr(ui, 'save_recipe_file', fail)
    value.save_recipe_button.click()
    assert target.read_bytes() == previous
    assert value.recipe_editor.get_recipe() == current
    assert 'disk full' in value.status_label.text()


def test_cancel_load_dialog_preserves_current_editor_draft(panel, monkeypatch):
    value, _host = panel
    value.set_recipe(recipe())
    value.recipe_editor.name_edit.setText('unsaved draft')
    before = value.recipe_editor.get_recipe()
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileName', lambda *a, **k: ('', ''))
    value.recipe_button.click()
    assert value.recipe_editor.get_recipe() == before


def test_export_tracks_only_current_successful_plan(panel, qtbot):
    value, _host = panel
    assert not value.export_controls.export_button.isEnabled()
    value.set_recipe(recipe())
    value.generate()
    assert not value.export_controls.isEnabled()
    qtbot.waitUntil(lambda: not value.busy)
    assert value.export_controls.export_button.isEnabled()
    value.rotation.setValue(5)
    assert value.last_plan is None and not value.export_controls.export_button.isEnabled()


@pytest.mark.parametrize('action', ['cancel', 'close', 'hide', 'change', 'shutdown'])
def test_export_busy_disables_inputs_and_generation_and_routes_lifecycle(panel, qtbot, monkeypatch, tmp_path, action):
    import mikrocam.ui.laser_export as ui
    from mikrocam.core.laser_paths import PlanningCancelled
    value, host = panel
    entered = threading.Event()
    def exporting(snapshot, destination, selected, cancelled):
        entered.set()
        while not cancelled():
            threading.Event().wait(0.001)
        raise PlanningCancelled()
    monkeypatch.setattr(ui, 'export_plan', exporting)
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName',
                        lambda *a, **k: (str(tmp_path / 'export.zip'), ''))
    value.set_recipe(recipe())
    value.generate()
    qtbot.waitUntil(lambda: not value.busy)
    snapshots = len(host.snapshots)
    value.export_controls.export_zip()
    qtbot.waitUntil(entered.is_set)
    assert value.busy and value.cancel_button.isEnabled()
    assert not value.generate_button.isEnabled() and not value.recipe_editor.isEnabled()
    value.generate()
    assert len(host.snapshots) == snapshots
    if action == 'cancel':
        value.cancel_button.click()
    elif action == 'close':
        value.close()
    elif action == 'hide':
        host.window.show()
        value.hide()
    elif action == 'change':
        value.rotation.setValue(10)
    else:
        value.shutdown()
    qtbot.waitUntil(lambda: not value.busy)
    assert value.export_controls._worker is None and value.generate_button.isEnabled()
    assert 'Cancelled' in value.status_label.text()
