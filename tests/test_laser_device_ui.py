"""Both existing panels share device-aware drafts with no invented numbers."""
from PyQt6 import QtWidgets
import pytest
from mikrocam.ui.laser_recipe import LaserRecipeEditor


def test_new_editor_requires_explicit_device_selection(qtbot):
    editor=LaserRecipeEditor(); qtbot.addWidget(editor)
    editor.name_edit.setText('draft'); editor.add_pass()
    for column,text in enumerate(('one','20','100','30','100')):
        editor.table.item(0,column).setText(text)
    with pytest.raises(ValueError,match='device|cihaz|Cihaz'): editor.get_recipe()


def test_switching_device_preserves_drafts_and_emits_changed(qtbot):
    editor=LaserRecipeEditor();qtbot.addWidget(editor);editor.name_edit.setText('draft');editor.add_pass()
    for column,text in enumerate(('one','20','100','30','100')):editor.table.item(0,column).setText(text)
    with qtbot.waitSignal(editor.changed): editor.device_editor.kind.setCurrentIndex(editor.device_editor.kind.findData('mopa'))
    editor.device_editor.name.setText('MOPA M7 100 W')
    assert editor.get_recipe().device.name=='MOPA M7 100 W'
    editor.device_editor.kind.setCurrentIndex(editor.device_editor.kind.findData('fiber'))
    assert editor.table.isColumnHidden(4) and not editor.table.isColumnHidden(3)
    assert editor.get_recipe().passes[0].pulse_width_ns is None
    editor.device_editor.kind.setCurrentIndex(editor.device_editor.kind.findData('diode'))
    assert editor.table.isColumnHidden(3) and editor.table.isColumnHidden(4)
    assert editor.get_recipe().passes[0].frequency_khz is None
    editor.device_editor.kind.setCurrentIndex(editor.device_editor.kind.findData('mopa'))
    assert editor.table.item(0,4).text()=='100' and editor.get_recipe().passes[0].pulse_width_ns==100


@pytest.mark.parametrize('kind',['diode','co2','fiber','mopa','uv','ruida_rf_co2'])
def test_loaded_device_recipe_and_limits_roundtrip_in_shared_editor(qtbot,kind):
    from test_laser_devices import recipe
    from dataclasses import replace
    original=recipe(kind)
    if kind=='mopa': original=replace(original,device=replace(original.device,frequency_range_khz=(20,100),pulse_widths_ns=(50,100)))
    editor=LaserRecipeEditor();qtbot.addWidget(editor);editor.set_recipe(original)
    assert editor.get_recipe()==original
    if kind=='uv': assert editor.table.isColumnHidden(1)
    if kind=='ruida_rf_co2': assert not editor.table.isColumnHidden(6)


def test_loaded_schema_one_remains_unspecified_and_unchanged(qtbot):
    from test_laser_job import recipe
    original=recipe();editor=LaserRecipeEditor();qtbot.addWidget(editor);editor.set_recipe(original)
    assert editor.get_recipe()==original
    assert editor.device_editor.kind.currentData() is None
    assert 'Eski' in editor.device_editor.kind.currentText()


def test_manufacturer_bounds_are_explicit_and_invalid_values_reported(qtbot):
    from test_laser_devices import recipe
    editor=LaserRecipeEditor();qtbot.addWidget(editor);editor.set_recipe(recipe('mopa'))
    editor.device_editor.limits.setChecked(True)
    editor.device_editor.frequency.setText('20:100')
    editor.device_editor.pulses.setText('50, 100, 200')
    assert editor.get_recipe().device.frequency_range_khz==(20,100)
    editor.table.item(0,4).setText('75')
    with pytest.raises(ValueError,match='pulse_width_ns'): editor.get_recipe()
    editor.device_editor.frequency.setText('bad')
    with pytest.raises(ValueError): editor.get_recipe()


def test_visual_device_change_invalidates_job_and_reprepares_with_applicable_values(qtbot,tmp_path):
    from test_visual_ui import Host,image_file
    from test_laser_devices import recipe
    from mikrocam.ui.visual_interlace_panel import VisualInterlacePanel
    panel=VisualInterlacePanel(Host()); qtbot.addWidget(panel)
    panel.recipe_group.setChecked(True);panel.recipe_editor.set_recipe(recipe('mopa'))
    panel.open_source(image_file(tmp_path));qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    panel.prepare();qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert panel.job is not None
    before=panel.job.mask.sha256
    kind=panel.recipe_editor.device_editor.kind;kind.setCurrentIndex(kind.findData('diode'))
    assert not panel._current_job() and not panel.save_button.isEnabled()
    assert not panel.png_button.isEnabled() and not panel.project_button.isEnabled()
    panel.prepare();qtbot.waitUntil(lambda:panel.worker is None,timeout=10000)
    assert panel.job.laser_recipe.device.kind=='diode' and panel.job.laser_recipe.passes[0].frequency_khz is None
    assert panel.job.mask.sha256==before
    panel.shutdown()
