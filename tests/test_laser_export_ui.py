"""Export worker commit boundary and GUI controls, without target software or hardware."""
from pathlib import Path
import threading

import pytest
from PyQt6 import QtCore, QtWidgets
from shapely.geometry import box


def plan():
    from mikrocam.core.laser_job import LaserJob, LaserPass, LaserRecipe, PlanarRegion
    from mikrocam.core.laser_paths import LaserPath, LaserPlan, PlanOptions
    job = LaserJob('job', PlanarRegion.from_geometry(box(0, 0, 2, 2)),
                   LaserRecipe('recipe', (LaserPass('first', 20, 250, 30, 100),)))
    return LaserPlan(job, PlanOptions(), (LaserPath(((0, 0), (2, 0)), 'contour'),))


@pytest.fixture
def controls(qtbot):
    from mikrocam.ui.laser_export import LaserExportControls
    value = LaserExportControls()
    qtbot.addWidget(value)
    messages = []
    def status(message):
        assert QtCore.QThread.currentThread() == value.thread()
        messages.append(message)
    value.status_changed.connect(status)
    yield value, messages
    value.shutdown()


def choose(monkeypatch, path):
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName', lambda *a, **k: (str(path), ''))


def test_no_plan_and_dirty_plan_cannot_export_or_open_dialog(controls, monkeypatch):
    value, messages = controls
    def unexpected(*args):
        pytest.fail('Unavailable export opened a dialog')
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName', unexpected)
    assert not value.export_button.isEnabled()
    value.export_zip()
    assert not value.busy
    value.set_plan(plan())
    assert value.export_button.isEnabled()
    value.set_plan(None)
    assert not value.export_button.isEnabled()
    value.export_zip()


def test_cancelled_dialog_changes_neither_plan_status_nor_busy_state(controls, monkeypatch):
    value, messages = controls
    current = plan()
    value.set_plan(current)
    choose(monkeypatch, '')
    value.export_zip()
    assert not value.busy and value.export_button.isEnabled()
    assert not messages


def test_plan_changed_inside_modal_dialog_cannot_export_a_different_plan(controls, monkeypatch, tmp_path):
    value, _messages = controls
    value.set_plan(plan())
    def dialog(*args, **kwargs):
        value.set_plan(plan())
        return str(tmp_path / 'unexpected.zip'), ''
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName', dialog)
    value.export_zip()
    assert not value.busy
    assert not (tmp_path / 'unexpected.zip').exists()


@pytest.mark.parametrize('format', ['svg', 'dxf'])
def test_live_worker_snapshots_format_plan_and_reports_path_on_gui(controls, qtbot, monkeypatch, tmp_path, format):
    import mikrocam.ui.laser_export as ui
    value, messages = controls
    current, target = plan(), tmp_path / 'export.zip'
    calls = []
    def export(snapshot, destination, selected, cancelled):
        assert QtCore.QThread.currentThread() != QtWidgets.QApplication.instance().thread()
        calls.append((snapshot, Path(destination), selected))
        return Path(destination)
    monkeypatch.setattr(ui, 'export_plan', export)
    choose(monkeypatch, target)
    value.set_plan(current)
    value.format_combo.setCurrentIndex(value.format_combo.findData(format))
    changes = []
    value.busy_changed.connect(changes.append)
    value.export_zip()
    qtbot.waitUntil(lambda: not value.busy)
    assert calls == [(current, target, format)] and calls[0][0] is current
    assert changes == [True, False]
    assert 'Saved' in messages[-1] and str(target) in messages[-1]


def test_no_overlap_early_cancel_and_invalidation(controls, qtbot, monkeypatch, tmp_path):
    import mikrocam.ui.laser_export as ui
    from mikrocam.core.laser_paths import PlanningCancelled
    value, messages = controls
    entered = threading.Event()
    calls = []
    def export(snapshot, destination, selected, cancelled):
        calls.append(snapshot)
        entered.set()
        while not cancelled():
            threading.Event().wait(0.001)
        raise PlanningCancelled()
    monkeypatch.setattr(ui, 'export_plan', export)
    choose(monkeypatch, tmp_path / 'export.zip')
    value.set_plan(plan())
    value.export_zip()
    qtbot.waitUntil(entered.is_set)
    assert not value.export_button.isEnabled() and not value.format_combo.isEnabled()
    value.export_zip()
    assert len(calls) == 1
    value.set_plan(None)
    qtbot.waitUntil(lambda: not value.busy)
    assert 'Cancelled' in messages[-1] and not value.export_button.isEnabled()
    assert not (tmp_path / 'export.zip').exists()


def test_late_cancel_after_committed_return_reports_saved(controls, qtbot, monkeypatch, tmp_path):
    import mikrocam.ui.laser_export as ui
    value, messages = controls
    target = tmp_path / 'export.zip'
    def export(snapshot, destination, selected, cancelled):
        Path(destination).write_bytes(b'committed')
        return Path(destination)
    monkeypatch.setattr(ui, 'export_plan', export)
    choose(monkeypatch, target)
    value.set_plan(plan())
    value.export_zip()
    assert value._worker.wait(2000)
    value.cancel()
    qtbot.waitUntil(lambda: not value.busy)
    assert target.read_bytes() == b'committed'
    assert 'Saved' in messages[-1] and 'Cancelled' not in messages[-1]


def test_worker_error_reports_context_and_allows_retry(controls, qtbot, monkeypatch, tmp_path):
    import mikrocam.ui.laser_export as ui
    value, messages = controls
    target = tmp_path / 'export.zip'
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr(ui, 'export_plan', fail)
    choose(monkeypatch, target)
    value.set_plan(plan())
    value.export_zip()
    qtbot.waitUntil(lambda: not value.busy)
    assert 'Error' in messages[-1] and 'disk full' in messages[-1]
    assert value.export_button.isEnabled() and value._worker is None


def test_shutdown_restart_discards_old_queued_callbacks(controls, qtbot, monkeypatch, tmp_path):
    import mikrocam.ui.laser_export as ui
    value, messages = controls
    first, second = threading.Event(), threading.Event()
    release_first, release_second = threading.Event(), threading.Event()
    calls = []
    def export(snapshot, destination, selected, cancelled):
        calls.append(snapshot)
        entered, release = (first, release_first) if len(calls) == 1 else (second, release_second)
        entered.set()
        assert release.wait(2)
        return Path(destination)
    monkeypatch.setattr(ui, 'export_plan', export)
    choose(monkeypatch, tmp_path / 'export.zip')
    value.set_plan(plan())
    value.export_zip()
    qtbot.waitUntil(first.is_set)
    release_first.set()
    value.shutdown()
    assert not value.busy and 'Saved' in messages[-1]
    value.export_zip()
    qtbot.waitUntil(second.is_set)
    assert value.busy and value._worker.isRunning()
    release_second.set()
    qtbot.waitUntil(lambda: not value.busy)
    assert 'Saved' in messages[-1]


def test_busy_finished_callback_can_start_next_export_without_old_status_overwriting_it(controls, qtbot, monkeypatch, tmp_path):
    import mikrocam.ui.laser_export as ui
    value, messages = controls
    calls = []
    second_entered, second_release = threading.Event(), threading.Event()
    def export(snapshot, destination, selected, cancelled):
        calls.append(snapshot)
        if len(calls) == 2:
            second_entered.set()
            assert second_release.wait(2)
        return Path(destination)
    monkeypatch.setattr(ui, 'export_plan', export)
    choose(monkeypatch, tmp_path / 'export.zip')
    value.set_plan(plan())
    def restart(busy):
        if not busy and len(calls) == 1:
            value.export_zip()
    value.busy_changed.connect(restart)
    value.export_zip()
    qtbot.waitUntil(second_entered.is_set)
    assert value.busy and 'Exporting' in messages[-1]
    second_release.set()
    qtbot.waitUntil(lambda: not value.busy)


@pytest.mark.parametrize('format', ['svg', 'dxf'])
def test_real_domain_export_creates_complete_zip_without_mutating_plan(controls, qtbot, monkeypatch, tmp_path, format):
    import zipfile
    value, messages = controls
    current = plan()
    source_hex = current.job.region.wkb_hex
    target = tmp_path / f'{format}.zip'
    value.set_plan(current)
    value.format_combo.setCurrentIndex(value.format_combo.findData(format))
    choose(monkeypatch, target)
    value.export_zip()
    qtbot.waitUntil(lambda: not value.busy, timeout=5000)
    assert 'Saved' in messages[-1]
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert any(name.endswith(f'.{format}') for name in archive.namelist())
        assert 'recipe.json' in archive.namelist() and 'manifest.json' in archive.namelist()
    assert current.job.region.wkb_hex == source_hex
