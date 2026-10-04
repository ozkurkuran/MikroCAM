"""Strict versioned recipe-database JSON, migration entry point and lossless 0.2 recipes."""
import json
from pathlib import Path

import pytest

from mikrocam.core.laser_device import LaserDeviceProfile
from mikrocam.core.laser_job import LaserPass, LaserRecipe
from mikrocam.core.laser_json import recipe_from_json, recipe_to_json

FIXTURE = Path(__file__).parent / 'test_files' / 'laser_recipe_db_v1.json'
ROOT = Path(__file__).parents[1]


def modules():
    from mikrocam.core import laser_recipe_db, laser_recipe_db_json
    return laser_recipe_db, laser_recipe_db_json


def database():
    m, _ = modules()
    mopa = LaserDeviceProfile('mopa', 'MOPA M7 100 W', (1.0, 4000.0), None, (100.0, 200.0))
    value = m.LaserRecipeDatabase(
        materials=(m.Material('fr4', 'FR4 35 µm Cu', 1.6, 'not:  ölçülmedi'),),
        lenses=(m.Lens('f160', 'F-theta 160', None),),
        machines=(m.Machine('m7', mopa, 'user typed'), m.Machine('ruida', LaserDeviceProfile('ruida_rf_co2', 'RF tube'))))
    value = m.put_recipe(value, m.RecipeEntry('r1', LaserRecipe('Isolation', (
        LaserPass('outline', 20.123456789012345, 250.00000000000003, 30.123456789012345, 100.0, 0.0),), mopa),
        'm7', 'fr4', 'f160', 'synthetic'))
    value = m.put_recipe(value, m.RecipeEntry('r2', LaserRecipe('Cut', (
        LaserPass('cut', 50, 10, None, None, 5, 20),), LaserDeviceProfile('ruida_rf_co2', 'RF tube')), 'ruida'))
    return m.put_recipe(value, m.RecipeEntry('r3', LaserRecipe('Legacy', (LaserPass('p', 1, 2, 3, 4),))))


def test_roundtrip_is_deterministic_strict_and_versioned():
    _, codec = modules()
    text = codec.database_to_json(database())
    data = json.loads(text)
    assert data['kind'] == 'mikrocam.laser-recipe-db' and data['schema_version'] == 1
    assert codec.database_from_json(text) == database()
    assert codec.database_to_json(codec.database_from_json(text)) == text
    assert 'ölçülmedi' in text and 'µm' in text


def test_device_is_stored_once_on_machine_and_legacy_passes_keep_schema1_fields():
    _, codec = modules()
    data = json.loads(codec.database_to_json(database()))
    recipes = {value['id']: value for value in data['recipes']}
    assert 'device' not in recipes['r1'] and 'device' in data['machines'][0]
    assert set(recipes['r3']['passes'][0]) == {'name', 'power_percent', 'speed_mm_s', 'frequency_khz', 'pulse_width_ns'}
    assert recipes['r2']['passes'][0]['pwm_frequency_khz'] == 20.0
    assert recipes['r2']['passes'][0]['frequency_khz'] is None


def _mutate(text, change):
    data = json.loads(text)
    change(data)
    return json.dumps(data)


@pytest.mark.parametrize('change', [
    lambda d: d.update(schema_version=2), lambda d: d.update(schema_version=True),
    lambda d: d.update(schema_version=0), lambda d: d.update(kind='mikrocam.laser-recipe'),
    lambda d: d.update(extra=1), lambda d: d.pop('lenses'), lambda d: d.update(materials={}),
    lambda d: d['materials'][0].update(thickness_mm=True), lambda d: d['materials'][0].pop('notes'),
    lambda d: d['materials'][0].update(color='red'), lambda d: d['recipes'][0].update(device={}),
    lambda d: d['recipes'][0]['passes'][0].pop('min_power_percent'),
    lambda d: d['recipes'][2]['passes'][0].update(min_power_percent=None),
    lambda d: d['recipes'][0].update(machine_id='missing'),
    lambda d: d['machines'][0]['device'].update(kind='laser'),
    lambda d: d['recipes'][0].update(passes={}),
])
def test_reader_rejects_malformed_or_future_documents(change):
    _, codec = modules()
    with pytest.raises(ValueError):
        codec.database_from_json(_mutate(codec.database_to_json(database()), change))


@pytest.mark.parametrize('text', ['[]', '{"kind": 1, "kind": 2}', '{"x": NaN}', 'not json', b'{}'])
def test_reader_rejects_non_documents(text):
    _, codec = modules()
    with pytest.raises(ValueError):
        codec.database_from_json(text)


def test_reader_rejects_oversized_text():
    _, codec = modules()
    with pytest.raises(ValueError, match='size'):
        codec.database_from_json(' ' * (codec.MAX_DATABASE_BYTES + 1))


def test_migration_entry_point_keeps_v1_and_rejects_unknown_versions():
    _, codec = modules()
    data = json.loads(codec.database_to_json(database()))
    assert codec.migrate_database_data(dict(data)) == data
    for version in (2, 99, '1', None):
        with pytest.raises(ValueError, match='schema_version'):
            codec.migrate_database_data({**data, 'schema_version': version})


def test_committed_v1_golden_file_still_opens_exactly():
    m, codec = modules()
    text = FIXTURE.read_text(encoding='utf-8')
    value = codec.database_from_json(text)
    assert codec.database_to_json(value) == text
    assert text.endswith('\n') and '\n  "lenses"' in text
    assert [entry.recipe.name for entry in value.recipes] == ['Isolation', 'Legacy 0.2 import']
    assert value.recipes[1].recipe.device is None and value.recipes[1].machine_id is None
    assert m.entry_labels(value, value.recipes[0]) == ('FR4 35 µm Cu', 'MOPA M7 100 W', None)


@pytest.mark.parametrize('recipe', [
    LaserRecipe('precise μ recipe', (LaserPass('first', 20.123456789012345, 250.00000000000003, 30.123456789012345, 100.00000000000001),
                                    LaserPass('second', 40, 500, 60, 200))),
    LaserRecipe('MOPA', (LaserPass('a', 20, 250, 30, 100, 1.5),), LaserDeviceProfile('mopa', 'MOPA M7 100 W', (1, 4000), (2, 500), (100, 200))),
    LaserRecipe('UV', (LaserPass('a', None, 250, 30, 2),), LaserDeviceProfile('uv', 'UV 5 W')),
    LaserRecipe('Diode', (LaserPass('a', 80, 20),), LaserDeviceProfile('diode', 'Bench')),
])
def test_existing_recipe_json_imports_and_exports_byte_identical(recipe):
    m, codec = modules()
    original = recipe_to_json(recipe)
    counter = iter(range(100))
    imported = codec.import_recipe_texts(m.LaserRecipeDatabase(), (original,), None, None, lambda: f'n{next(counter)}')
    entry = imported.recipes[0]
    assert (entry.machine_id is None) == (recipe.device is None)
    reopened = codec.database_from_json(codec.database_to_json(imported))
    assert recipe_to_json(reopened.recipes[0].recipe) == original
    assert recipe_from_json(original) == reopened.recipes[0].recipe


def test_multi_file_import_is_all_or_nothing_and_names_the_failed_file():
    m, codec = modules()
    good = recipe_to_json(LaserRecipe('Good', (LaserPass('a', 1, 2, 3, 4),)))
    counter = iter(range(100))
    with pytest.raises(ValueError, match='2'):
        codec.import_recipe_texts(m.LaserRecipeDatabase(), (good, '{"kind":"x"}'), None, None, lambda: f'n{next(counter)}')
    conflicting = recipe_to_json(LaserRecipe('Good', (LaserPass('a', 9, 2, 3, 4),)))
    with pytest.raises(ValueError, match='exists'):
        codec.import_recipe_texts(m.LaserRecipeDatabase(), (good, conflicting), None, None, lambda: f'n{next(counter)}')
    same = codec.import_recipe_texts(m.LaserRecipeDatabase(), (good, good), None, None, lambda: f'n{next(counter)}')
    assert len(same.recipes) == 1


def test_json_schema_document_matches_codec_version():
    schema = json.loads((ROOT / 'mikrocam/core/laser_recipe_db_v1.schema.json').read_text(encoding='utf-8'))
    assert schema['properties']['schema_version'] == {'const': 1}
    assert schema['properties']['kind'] == {'const': 'mikrocam.laser-recipe-db'}
    assert set(schema['required']) == {'kind', 'schema_version', 'materials', 'lenses', 'machines', 'recipes'}
