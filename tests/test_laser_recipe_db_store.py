"""Atomic recipe-database file store with revision checks and corrupt-file protection."""
import os
from pathlib import Path

import pytest

from mikrocam.core.laser_device import LaserDeviceProfile
from mikrocam.core.laser_job import LaserPass, LaserRecipe


def parts():
    from mikrocam.core import laser_recipe_db as m
    from mikrocam.core.laser_recipe_db_json import database_to_json
    from mikrocam.laser import recipe_db_store as store
    return m, database_to_json, store


def filled():
    m, _, _ = parts()
    recipe = LaserRecipe('Isolation', (LaserPass('a', 20, 250, 30, 100),), LaserDeviceProfile('mopa', 'M7'))
    counter = iter(range(100))
    database, _, _ = m.store_recipe(m.LaserRecipeDatabase((m.Material('fr4', 'FR4'),)), recipe, 'fr4', None,
                                    lambda: f'n{next(counter)}')
    return database


def test_missing_file_is_empty_database_without_creating_it(tmp_path):
    m, _, store = parts()
    target = tmp_path / 'nested' / 'db.json'
    database, revision = store.load_database(target)
    assert database == m.LaserRecipeDatabase() and revision is None
    assert not target.parent.exists()


def test_save_creates_parent_writes_canonical_text_and_reopens(tmp_path):
    _, dump, store = parts()
    target = tmp_path / 'nested' / 'db.json'
    revision = store.save_database(target, filled(), None)
    assert target.read_text(encoding='utf-8') == dump(filled())
    database, loaded = store.load_database(target)
    assert database == filled() and loaded == revision
    assert [path.name for path in target.parent.iterdir()] == ['db.json']


def test_save_rejects_external_change_creation_and_deletion(tmp_path):
    m, _, store = parts()
    target = tmp_path / 'db.json'
    revision = store.save_database(target, filled(), None)
    target.write_text(target.read_text(encoding='utf-8') + ' ', encoding='utf-8')
    with pytest.raises(ValueError, match='changed'):
        store.save_database(target, m.LaserRecipeDatabase(), revision)
    assert target.read_text(encoding='utf-8').endswith(' ')
    with pytest.raises(ValueError, match='changed'):
        store.save_database(tmp_path / 'other.json', m.LaserRecipeDatabase(), revision)
    other = tmp_path / 'created.json'
    other.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='changed'):
        store.save_database(other, m.LaserRecipeDatabase(), None)
    assert other.read_text(encoding='utf-8') == '{}'


@pytest.mark.parametrize('content', [b'{"kind": "mikrocam.laser-recipe-db", "schema_version": 2}', b'\xff\xfe', b'not json'])
def test_corrupt_or_future_file_is_reported_and_left_untouched(tmp_path, content):
    _, _, store = parts()
    target = tmp_path / 'db.json'
    target.write_bytes(content)
    with pytest.raises(ValueError):
        store.load_database(target)
    assert target.read_bytes() == content


def test_oversized_file_is_rejected_before_parsing(tmp_path, monkeypatch):
    _, _, store = parts()
    target = tmp_path / 'db.json'
    target.write_bytes(b' ' * 32)
    monkeypatch.setattr(store, 'MAX_DATABASE_BYTES', 16)
    with pytest.raises(ValueError, match='size'):
        store.load_database(target)


def test_failed_atomic_write_keeps_previous_file_and_no_temporary(tmp_path, monkeypatch):
    _, _, store = parts()
    target = tmp_path / 'db.json'
    target.write_text('previous', encoding='utf-8')

    def fail(source, destination):
        raise OSError('disk full')
    monkeypatch.setattr(store.os, 'replace', fail)
    with pytest.raises(OSError):
        store.write_text_atomic(target, 'next')
    assert target.read_text(encoding='utf-8') == 'previous'
    assert [path.name for path in tmp_path.iterdir()] == ['db.json']


def test_recipe_json_save_uses_the_shared_atomic_writer(tmp_path, monkeypatch):
    from mikrocam.ui import laser_recipe
    calls = []
    monkeypatch.setattr(laser_recipe, 'write_text_atomic', lambda path, text: calls.append((Path(path), text)))
    recipe = LaserRecipe('x', (LaserPass('a', 1, 2, 3, 4),))
    laser_recipe.save_recipe_file(tmp_path / 'r.json', recipe)
    assert calls and calls[0][0] == tmp_path / 'r.json'


def test_write_text_atomic_uses_lf_utf8(tmp_path):
    _, _, store = parts()
    target = tmp_path / 'x.json'
    store.write_text_atomic(target, 'a\nµ\n')
    assert target.read_bytes() == 'a\nµ\n'.encode('utf-8')
    assert os.listdir(tmp_path) == ['x.json']
