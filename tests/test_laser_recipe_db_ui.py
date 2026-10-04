"""Offscreen recipe-library widget: thin catalog management over the core database."""
from dataclasses import replace
from pathlib import Path

from PyQt6 import QtWidgets

from mikrocam.core.laser_device import LaserDeviceProfile
from mikrocam.core.laser_job import LaserPass, LaserRecipe
from mikrocam.core.laser_json import recipe_from_json, recipe_to_json

MOPA = LaserDeviceProfile('mopa', 'MOPA M7 100 W')


def mopa(power=20.0, name='Isolation'):
    return LaserRecipe(name, (LaserPass('outline', power, 250.0, 30.0, 100.0),), MOPA)


def make(qtbot, path):
    from mikrocam.ui.laser_recipe import LaserRecipeEditor
    from mikrocam.ui.laser_recipe_db import LaserRecipeLibrary
    editor = LaserRecipeEditor()
    library = LaserRecipeLibrary(editor, path)
    qtbot.addWidget(editor)
    qtbot.addWidget(library)
    return editor, library


def answers(library, monkeypatch, *values):
    queue = list(values)
    monkeypatch.setattr(library, '_ask_catalog', lambda *args: queue.pop(0))
    return queue


def rows(library):
    return [tuple(library.table.item(row, column).text() for column in range(library.table.columnCount()))
            for row in range(library.table.rowCount())]


def prepared(qtbot, monkeypatch, path):
    editor, library = make(qtbot, path)
    answers(library, monkeypatch, ('FR4 35 µm Cu', 1.6, 'synthetic'), ('F-theta 160', None, ''))
    library.add_material()
    library.add_lens()
    editor.set_recipe(mopa())
    library.save_current()
    return editor, library


def test_empty_library_shows_path_and_creates_no_file(qtbot, tmp_path):
    _, library = make(qtbot, tmp_path / 'db.json')
    assert library.writable and library.table.rowCount() == 0
    assert str(tmp_path / 'db.json') in library.path_label.text()
    assert library.material_combo.currentData() is None and library.lens_combo.currentData() is None
    assert not (tmp_path / 'db.json').exists()


def test_save_lists_four_labels_and_survives_reopen_and_load(qtbot, monkeypatch, tmp_path):
    target = tmp_path / 'db.json'
    _, library = prepared(qtbot, monkeypatch, target)
    assert rows(library) == [('Isolation', 'FR4 35 µm Cu', 'MOPA M7 100 W', 'F-theta 160', '1')]
    assert target.exists()
    editor, reopened = make(qtbot, target)
    assert rows(reopened) == rows(library)
    reopened.material_combo.setCurrentIndex(0)
    reopened.table.selectRow(0)
    reopened.load_selected()
    assert editor.get_recipe() == mopa()
    assert reopened.material_combo.currentText() == 'FR4 35 µm Cu'
    assert reopened.lens_combo.currentText() == 'F-theta 160'


def test_new_material_dialog_cancel_and_values_are_not_invented(qtbot, monkeypatch, tmp_path):
    _, library = make(qtbot, tmp_path / 'db.json')
    answers(library, monkeypatch, None, ('Alu', None, ''))
    library.add_material()
    assert library.material_combo.count() == 1
    library.add_material()
    material = library.database.materials[0]
    assert material.name == 'Alu' and material.thickness_mm is None
    assert library.material_combo.currentText() == 'Alu'


def test_overwrite_requires_confirmation(qtbot, monkeypatch, tmp_path):
    editor, library = prepared(qtbot, monkeypatch, tmp_path / 'db.json')
    editor.set_recipe(mopa(40))
    library.material_combo.setCurrentIndex(1)
    library.lens_combo.setCurrentIndex(1)
    monkeypatch.setattr(library, '_confirm', lambda text: False)
    library.save_current()
    assert library.database.recipes[0].recipe == mopa()
    monkeypatch.setattr(library, '_confirm', lambda text: True)
    library.save_current()
    assert library.database.recipes[0].recipe == mopa(40) and len(library.database.recipes) == 1


def test_search_filters_rows_by_any_label(qtbot, monkeypatch, tmp_path):
    editor, library = prepared(qtbot, monkeypatch, tmp_path / 'db.json')
    library.material_combo.setCurrentIndex(0)
    editor.set_recipe(mopa(name='Cut'))
    library.save_current()
    assert library.table.rowCount() == 2
    library.search_edit.setText('fr4')
    assert [row[0] for row in rows(library)] == ['Isolation']
    library.search_edit.setText('m7')
    assert library.table.rowCount() == 2


def test_used_material_cannot_be_deleted_and_error_is_visible(qtbot, monkeypatch, tmp_path):
    _, library = prepared(qtbot, monkeypatch, tmp_path / 'db.json')
    monkeypatch.setattr(library, '_confirm', lambda text: True)
    library.material_combo.setCurrentIndex(1)
    library.delete_material()
    assert len(library.database.materials) == 1
    assert 'Isolation' in library.status_label.text()


def test_machine_profile_update_rebinds_recipes_or_rejects_invalid_bounds(qtbot, monkeypatch, tmp_path):
    editor, library = prepared(qtbot, monkeypatch, tmp_path / 'db.json')
    monkeypatch.setattr(library, '_confirm', lambda text: True)
    bounded = replace(MOPA, frequency_range_khz=(1.0, 4000.0))
    editor.device_editor.set_profile(bounded)
    library.save_machine()
    assert library.database.machines[0].device == bounded
    assert library.database.recipes[0].recipe.device == bounded
    editor.device_editor.set_profile(replace(MOPA, frequency_range_khz=(40.0, 50.0)))
    library.save_machine()
    assert library.database.machines[0].device == bounded
    assert 'Isolation' in library.status_label.text()


def test_unused_machine_can_be_deleted(qtbot, monkeypatch, tmp_path):
    editor, library = prepared(qtbot, monkeypatch, tmp_path / 'db.json')
    monkeypatch.setattr(library, '_confirm', lambda text: True)
    library.table.selectRow(0)
    library.delete_selected()
    assert library.table.rowCount() == 0
    library.machine_combo.setCurrentIndex(0)
    library.delete_machine()
    assert library.database.machines == ()


def test_import_many_json_files_all_or_nothing_and_export(qtbot, monkeypatch, tmp_path):
    _, library = make(qtbot, tmp_path / 'db.json')
    good = tmp_path / 'good.json'
    good.write_text(recipe_to_json(mopa()), encoding='utf-8')
    legacy = tmp_path / 'legacy.json'
    legacy.write_text(recipe_to_json(LaserRecipe('Legacy', (LaserPass('a', 1, 2, 3, 4),))), encoding='utf-8')
    bad = tmp_path / 'bad.json'
    bad.write_text('{', encoding='utf-8')
    dialog = QtWidgets.QFileDialog
    monkeypatch.setattr(dialog, 'getOpenFileNames', lambda *args, **kwargs: ([str(good), str(bad)], ''))
    library.import_files()
    assert library.table.rowCount() == 0 and 'bad.json' in library.status_label.text()
    monkeypatch.setattr(dialog, 'getOpenFileNames', lambda *args, **kwargs: ([str(good), str(legacy)], ''))
    library.import_files()
    assert [row[0] for row in rows(library)] == ['Isolation', 'Legacy']
    assert rows(library)[1][2] == ''
    target = tmp_path / 'exported.json'
    library.table.selectRow(1)
    monkeypatch.setattr(dialog, 'getSaveFileName', lambda *args, **kwargs: (str(target), ''))
    library.export_selected()
    assert target.read_text(encoding='utf-8') == legacy.read_text(encoding='utf-8')


def test_corrupt_database_is_read_only_and_untouched(qtbot, monkeypatch, tmp_path):
    target = tmp_path / 'db.json'
    target.write_text('{"kind": "mikrocam.laser-recipe-db", "schema_version": 9}', encoding='utf-8')
    editor, library = make(qtbot, target)
    assert not library.writable and not library.save_button.isEnabled()
    assert 'schema_version' in library.status_label.text()
    editor.set_recipe(mopa())
    library.save_current()
    assert target.read_text(encoding='utf-8').endswith('9}')


def test_external_change_is_rejected_until_reload(qtbot, monkeypatch, tmp_path):
    target = tmp_path / 'db.json'
    editor, library = prepared(qtbot, monkeypatch, target)
    _, other = make(qtbot, target)
    answers(other, monkeypatch, ('Glass', None, ''))
    other.add_material()
    editor.set_recipe(mopa(name='Second'))
    library.save_current()
    assert len(library.database.recipes) == 1 and 'yeniden yükle' in library.status_label.text().lower()
    library.reload()
    assert [value.name for value in library.database.materials] == ['FR4 35 µm Cu', 'Glass']


def test_invalid_editor_draft_is_reported_not_saved(qtbot, monkeypatch, tmp_path):
    editor, library = make(qtbot, tmp_path / 'db.json')
    editor.add_pass()
    library.save_current()
    assert library.database.recipes == () and library.status_label.text()
    assert not (tmp_path / 'db.json').exists()


def test_laser_cam_panel_hosts_library_at_host_path(qtbot, tmp_path):
    from test_laser_cam_ui import FakeHost
    from mikrocam.ui.laser_cam import LaserCamPanel
    host = FakeHost()
    host.database_path = tmp_path / 'host.json'
    panel = LaserCamPanel(host)
    qtbot.addWidget(host.window)
    try:
        assert panel.recipe_library.path == Path(host.database_path)
        assert panel.recipe_library.editor is panel.recipe_editor
    finally:
        panel.shutdown()


def test_bridge_database_path_uses_application_data_directory(tmp_path):
    from mikrocam.bridge.laser_cam import LaserCamHost

    class App:
        data_path = str(tmp_path)

    assert LaserCamHost(App()).recipe_database_path() == tmp_path / 'mikrocam' / 'laser_recipe_db.json'
    assert recipe_from_json(recipe_to_json(mopa())) == mopa()
