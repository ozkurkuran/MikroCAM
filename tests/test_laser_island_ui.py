"""Thin Laser CAM island controls: request options, invalidation and visible errors."""
import pytest
from PyQt6 import QtCore

from test_laser_cam_ui import FakeHost, recipe


@pytest.fixture
def panel(qtbot):
    from mikrocam.ui.laser_cam import LaserCamPanel
    host = FakeHost()
    value = LaserCamPanel(host)
    host.window.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, value)
    qtbot.addWidget(host.window)
    yield value, host
    value.shutdown()


def test_island_controls_start_disabled_and_map_to_plan_options(panel, qtbot):
    from mikrocam.core.laser_paths import IslandSettings
    value, host = panel
    assert not value.island_enabled.isChecked()
    assert [value.island_order.itemData(i) for i in range(value.island_order.count())] == ['checkerboard', 'raster']
    value.set_recipe(recipe())
    value.hatch_enabled.setChecked(True)
    value.hatch_spacing.setValue(0.2)
    value.island_enabled.setChecked(True)
    value.island_tile.setValue(0.75)
    value.island_overlap.setValue(0.1)
    value.island_angle_step.setValue(45)
    value.island_order.setCurrentIndex(value.island_order.findData('raster'))
    value.generate()
    qtbot.waitUntil(lambda: not value.busy)
    plan = value.last_plan
    assert plan is not None and plan is host.publications[0], value.status_label.text()
    assert plan.options.island == IslandSettings(0.75, 0.1, 45, 'raster')
    assert {path.role for path in plan.paths} == {'contour', 'hatch'}


def test_island_settings_change_invalidates_preview_and_export(panel, qtbot):
    value, host = panel
    value.set_recipe(recipe())
    value.hatch_enabled.setChecked(True)
    value.island_enabled.setChecked(True)
    value.island_tile.setValue(1)
    value.generate()
    qtbot.waitUntil(lambda: not value.busy)
    assert value.last_plan is not None
    for control, change in ((value.island_tile, lambda: value.island_tile.setValue(0.5)),
                            (value.island_overlap, lambda: value.island_overlap.setValue(0.2)),
                            (value.island_angle_step, lambda: value.island_angle_step.setValue(30)),
                            (value.island_order, lambda: value.island_order.setCurrentIndex(1)),
                            (value.island_enabled, lambda: value.island_enabled.setChecked(False))):
        value.generate()
        qtbot.waitUntil(lambda: not value.busy)
        assert value.last_plan is not None
        change()
        assert value.last_plan is None and control in value._inputs


def test_island_without_hatch_or_with_tile_below_spacing_is_a_visible_error(panel):
    value, host = panel
    value.set_recipe(recipe())
    value.island_enabled.setChecked(True)
    value.generate()
    assert 'hatch' in value.status_label.text().lower() and not host.snapshots
    value.hatch_enabled.setChecked(True)
    value.hatch_spacing.setValue(2)
    value.island_tile.setValue(1)
    value.generate()
    assert 'spacing' in value.status_label.text().lower() and value.last_plan is None
