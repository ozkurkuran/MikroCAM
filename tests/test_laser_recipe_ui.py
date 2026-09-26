"""Explicit recipe editing and schema-1 atomic persistence, without device defaults."""
import pytest

from mikrocam.core.laser_job import LaserPass, LaserRecipe
from mikrocam.core.laser_json import recipe_from_json


def example():
    return LaserRecipe('precise μ recipe', (
        LaserPass('first', 20.123456789012345, 250.00000000000003, 30.123456789012345, 100.00000000000001),
        LaserPass('second', 40, 500, 60, 200)))


@pytest.fixture
def editor(qtbot):
    from mikrocam.ui.laser_recipe import LaserRecipeEditor
    value = LaserRecipeEditor()
    qtbot.addWidget(value)
    return value


def test_loaded_values_preserve_precision_and_emit_one_change(editor, qtbot):
    with qtbot.waitSignal(editor.changed):
        editor.set_recipe(example())
    assert editor.name_edit.text() == example().name
    assert editor.table.columnCount() == 5
    assert editor.table.item(0, 1).text() == repr(example().passes[0].power_percent)
    assert editor.get_recipe() == example()


def test_added_pass_has_no_numeric_defaults_and_requires_explicit_values(editor, qtbot):
    with qtbot.waitSignal(editor.changed):
        editor.add_pass()
    assert editor.table.rowCount() == 1
    assert all(editor.table.item(0, column).text() == '' for column in range(5))
    with pytest.raises(ValueError):
        editor.get_recipe()
    editor.name_edit.setText('new recipe')
    for column, value in enumerate(('named', '20', '250', '30', '100')):
        editor.table.item(0, column).setText(value)
    assert editor.get_recipe() == LaserRecipe('new recipe', (LaserPass('named', 20, 250, 30, 100),))


def test_reorder_remove_and_edit_keep_row_values_together(editor, qtbot):
    editor.set_recipe(example())
    editor.table.setCurrentCell(1, 0)
    with qtbot.waitSignal(editor.changed):
        editor.move_pass(-1)
    assert editor.get_recipe().passes == tuple(reversed(example().passes))
    editor.move_pass(-1)  # cannot move above first row
    assert editor.get_recipe().passes == tuple(reversed(example().passes))
    editor.move_pass(1)
    assert editor.get_recipe() == example()
    editor.table.setCurrentCell(0, 2)
    with qtbot.waitSignal(editor.changed):
        editor.table.item(0, 2).setText('123.45678901234567')
    assert editor.get_recipe().passes[0].speed_mm_s == 123.45678901234567
    editor.table.setCurrentCell(1, 0)
    with qtbot.waitSignal(editor.changed):
        editor.remove_pass()
    assert editor.table.rowCount() == 1
    editor.remove_pass()
    assert editor.table.rowCount() == 0
    with pytest.raises(ValueError):
        editor.get_recipe()


@pytest.mark.parametrize('column,text', [(0, ''), (1, ''), (1, '101'), (1, '0'), (2, '-1'),
    (2, 'True'), (3, 'NaN'), (4, 'Infinity'), (4, 'not a number')])
def test_editor_uses_strict_required_core_validation(editor, column, text):
    editor.set_recipe(example())
    editor.table.item(0, column).setText(text)
    with pytest.raises(ValueError):
        editor.get_recipe()


def test_duplicate_pass_names_and_blank_recipe_name_fail(editor):
    editor.set_recipe(example())
    editor.table.item(1, 0).setText('first')
    with pytest.raises(ValueError, match='duplicate'):
        editor.get_recipe()
    editor.set_recipe(example())
    editor.name_edit.setText(' ')
    with pytest.raises(ValueError, match='name'):
        editor.get_recipe()


def test_move_multiple_rows_preserves_the_order_of_intervening_passes(editor):
    third = LaserPass('third', 60, 750, 90, 300)
    original = LaserRecipe('three passes', example().passes + (third,))
    editor.set_recipe(original)
    editor.table.setCurrentCell(0, 0)
    editor.move_pass(2)
    assert editor.get_recipe().passes == (original.passes[1], third, original.passes[0])


def test_atomic_save_roundtrip_retains_precision_and_no_temporary_files(tmp_path):
    from mikrocam.ui.laser_recipe import save_recipe_file
    target = tmp_path / 'recipe.json'
    target.write_text('previous', encoding='utf-8')
    save_recipe_file(target, example())
    assert recipe_from_json(target.read_text(encoding='utf-8')) == example()
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize('failure', ['replace', 'fsync', 'write'])
def test_failed_atomic_save_preserves_previous_file_and_cleans_temp(tmp_path, monkeypatch, failure):
    import mikrocam.ui.laser_recipe as ui
    target = tmp_path / 'recipe.json'
    previous = b'previous exact bytes\r\n'
    target.write_bytes(previous)
    def fail(*args):
        raise OSError('simulated disk failure')
    if failure == 'write':
        original = ui.tempfile.NamedTemporaryFile
        def failing_stream(**kwargs):
            stream = original(**kwargs)
            stream.write = fail
            return stream
        monkeypatch.setattr(ui.tempfile, 'NamedTemporaryFile', failing_stream)
    else:
        monkeypatch.setattr(ui.os, failure, fail)
    with pytest.raises(OSError, match='simulated disk failure'):
        ui.save_recipe_file(target, example())
    assert target.read_bytes() == previous
    assert list(tmp_path.iterdir()) == [target]
