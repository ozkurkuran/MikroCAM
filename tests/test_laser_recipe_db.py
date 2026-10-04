"""Qt-free recipe database model: invariants, single device source and safe operations."""
from dataclasses import replace

import pytest

from mikrocam.core.laser_device import LaserDeviceProfile
from mikrocam.core.laser_job import LaserPass, LaserRecipe


def db_module():
    from mikrocam.core import laser_recipe_db
    return laser_recipe_db


MOPA = LaserDeviceProfile('mopa', 'MOPA M7 100 W')
DIODE = LaserDeviceProfile('diode', 'Diode bench')


def mopa_recipe(name='Isolation', power=20.0):
    return LaserRecipe(name, (LaserPass('outline', power, 250.0, 30.0, 100.0),), MOPA)


def legacy_recipe(name='Legacy 0.2'):
    return LaserRecipe(name, (LaserPass('first', 20, 250, 30, 100),))


def ids():
    counter = iter(range(1, 1000))
    return lambda: f'id{next(counter)}'


def sample():
    m = db_module()
    database = m.LaserRecipeDatabase(
        materials=(m.Material('fr4', 'FR4 35 µm Cu', 1.6, 'double sided'),),
        lenses=(m.Lens('f160', 'F-theta 160', 160.0),),
        machines=(m.Machine('m7', MOPA),))
    entry = m.RecipeEntry('r1', mopa_recipe(), 'm7', 'fr4', 'f160', 'synthetic test only')
    return m.put_recipe(database, entry)


def test_empty_database_and_explicit_optional_values_are_never_invented():
    m = db_module()
    database = m.LaserRecipeDatabase()
    assert database.materials == database.lenses == database.machines == database.recipes == ()
    material = m.Material('a', 'Copper')
    lens = m.Lens('b', 'Lens')
    assert material.thickness_mm is None and material.notes == ''
    assert lens.focal_length_mm is None
    assert m.Machine('c', MOPA).name == 'MOPA M7 100 W'


@pytest.mark.parametrize('factory', [
    lambda m: m.Material('', 'x'), lambda m: m.Material('UPPER', 'x'), lambda m: m.Material('a' * 65, 'x'),
    lambda m: m.Material('a', ' '), lambda m: m.Material('a', 'x', 0), lambda m: m.Material('a', 'x', -1),
    lambda m: m.Material('a', 'x', True), lambda m: m.Material('a', 'x', float('nan')),
    lambda m: m.Material('a', 'x', notes=None), lambda m: m.Material('a', 'x', notes='n' * 4001),
    lambda m: m.Lens('a', 'x', 0.0), lambda m: m.Lens('a', 'x', float('inf')),
    lambda m: m.Machine('a', 'mopa'), lambda m: m.RecipeEntry('a', 'recipe'),
    lambda m: m.Material('a', 'n' * 257)])
def test_invalid_catalog_values_are_rejected(factory):
    with pytest.raises(ValueError):
        factory(db_module())


def test_entry_labels_and_matching_search_all_four_names():
    m = db_module()
    database = sample()
    entry = database.recipes[0]
    assert m.entry_labels(database, entry) == ('FR4 35 µm Cu', 'MOPA M7 100 W', 'F-theta 160')
    for text in ('isolation', 'fr4', 'm7', 'THETA', '  '):
        assert m.matching_recipes(database, text) == (entry,)
    assert m.matching_recipes(database, 'absent') == ()


@pytest.mark.parametrize('change', [
    lambda m, d: replace(d, materials=d.materials * 2),
    lambda m, d: replace(d, materials=d.materials + (m.Material('other', ' fr4 35 µm cu '),)),
    lambda m, d: replace(d, lenses=d.lenses + (m.Lens('f2', 'f-THETA 160'),)),
    lambda m, d: replace(d, machines=d.machines + (m.Machine('m8', replace(DIODE, name='mopa m7 100 w')),)),
    lambda m, d: replace(d, recipes=(replace(d.recipes[0], material_id='missing'),)),
    lambda m, d: replace(d, recipes=(replace(d.recipes[0], lens_id='missing'),)),
    lambda m, d: replace(d, recipes=(replace(d.recipes[0], machine_id='missing'),)),
    lambda m, d: replace(d, recipes=(replace(d.recipes[0], machine_id=None),)),
    lambda m, d: replace(d, recipes=d.recipes + (replace(d.recipes[0], id='r2', recipe=mopa_recipe('ISOLATION ', 30)),)),
    lambda m, d: replace(d, recipes=d.recipes + (m.RecipeEntry('r2', legacy_recipe(), 'm7'),)),
    lambda m, d: replace(d, recipes=d.recipes + (m.RecipeEntry('r2', LaserRecipe('x', (LaserPass('p', 1, 1, None, None),), DIODE), 'm7'),)),
    lambda m, d: replace(d, recipes=list(d.recipes)),
])
def test_database_invariants_reject_duplicates_missing_references_and_profile_mismatch(change):
    m = db_module()
    with pytest.raises(ValueError):
        change(m, sample())


def test_same_recipe_name_is_allowed_for_different_material_or_lens():
    m = db_module()
    database = m.put_material(sample(), m.Material('al', 'Aluminium'))
    other = m.RecipeEntry('r2', mopa_recipe(), 'm7', 'al', 'f160')
    assert len(m.put_recipe(database, other).recipes) == 2


def test_legacy_recipe_stays_without_machine_and_profile():
    m = db_module()
    database, entry, changed = m.store_recipe(m.LaserRecipeDatabase(), legacy_recipe(), None, None, ids())
    assert changed and entry.machine_id is None and entry.recipe.device is None
    assert database.machines == ()


def test_store_recipe_reuses_equal_machine_or_adds_profile_once():
    m = db_module()
    new_id = ids()
    database, first, _ = m.store_recipe(m.LaserRecipeDatabase(), mopa_recipe('A'), None, None, new_id)
    database, second, _ = m.store_recipe(database, mopa_recipe('B'), None, None, new_id)
    assert len(database.machines) == 1 and first.machine_id == second.machine_id == database.machines[0].id
    assert database.machines[0].device == MOPA


def test_store_recipe_conflicting_same_name_profile_is_explicit():
    m = db_module()
    database = sample()
    bounded = replace(MOPA, frequency_range_khz=(1.0, 4000.0))
    recipe = LaserRecipe('B', mopa_recipe().passes, bounded)
    with pytest.raises(ValueError, match='machine'):
        m.store_recipe(database, recipe, None, None, ids())


def test_store_recipe_identical_is_unchanged_and_different_requires_replace():
    m = db_module()
    database = sample()
    same, entry, changed = m.store_recipe(database, mopa_recipe(), 'fr4', 'f160', ids())
    assert same == database and not changed and entry.id == 'r1'
    with pytest.raises(ValueError, match='exists'):
        m.store_recipe(database, mopa_recipe(power=40), 'fr4', 'f160', ids())
    replaced, entry, changed = m.store_recipe(database, mopa_recipe(power=40), 'fr4', 'f160', ids(), replace=True)
    assert changed and entry.id == 'r1' and entry.notes == 'synthetic test only'
    assert replaced.recipes[0].recipe.passes[0].power_percent == 40
    assert m.find_recipe(replaced, 'ISOLATION', 'm7', 'fr4', 'f160') == entry


def test_put_machine_revalidates_and_rebinds_every_dependent_recipe():
    m = db_module()
    database = sample()
    bounded = replace(MOPA, frequency_range_khz=(1.0, 4000.0), pulse_widths_ns=(100.0, 200.0))
    updated = m.put_machine(database, m.Machine('m7', bounded, 'manufacturer sheet'))
    assert updated.recipes[0].recipe.device == bounded
    assert updated.recipes[0].recipe.passes == database.recipes[0].recipe.passes
    narrow = replace(MOPA, frequency_range_khz=(40.0, 60.0))
    with pytest.raises(ValueError, match='Isolation'):
        m.put_machine(database, m.Machine('m7', narrow))
    assert database.recipes[0].recipe.device == MOPA


def test_put_machine_cannot_change_family_of_used_machine_silently():
    m = db_module()
    with pytest.raises(ValueError):
        m.put_machine(sample(), m.Machine('m7', replace(DIODE, name='MOPA M7 100 W')))


def test_remove_used_catalog_entries_is_rejected_and_unused_is_removed():
    m = db_module()
    database = sample()
    for remove, key in ((m.remove_material, 'fr4'), (m.remove_lens, 'f160'), (m.remove_machine, 'm7')):
        with pytest.raises(ValueError, match='Isolation'):
            remove(database, key)
        with pytest.raises(ValueError, match='unknown'):
            remove(database, 'missing')
    empty = m.remove_recipe(database, 'r1')
    assert empty.recipes == ()
    empty = m.remove_machine(m.remove_lens(m.remove_material(empty, 'fr4'), 'f160'), 'm7')
    assert empty == m.LaserRecipeDatabase()
    with pytest.raises(ValueError, match='unknown'):
        m.remove_recipe(empty, 'r1')


def test_put_material_and_lens_replace_by_id_preserving_order():
    m = db_module()
    database = m.put_material(sample(), m.Material('al', 'Aluminium'))
    database = m.put_material(database, m.Material('fr4', 'FR4 renamed', None, ''))
    assert [value.name for value in database.materials] == ['FR4 renamed', 'Aluminium']
    database = m.put_lens(database, m.Lens('f160', 'Lens renamed', 163.0))
    assert database.lenses[0].focal_length_mm == 163.0
    assert m.entry_labels(database, database.recipes[0])[0] == 'FR4 renamed'


def test_new_identifier_is_valid_and_unique():
    from mikrocam.laser.recipe_db_store import new_id
    m = db_module()
    values = {new_id() for _ in range(50)}
    assert len(values) == 50
    for value in values:
        m.Material(value, 'x')
