"""Strict versioned JSON for the laser recipe database and lossless 0.2 recipe import."""
from collections.abc import Callable, Iterable
from dataclasses import asdict
import json

from .laser_job import LaserPass, LaserRecipe
from .laser_json import DEVICE_PASS_FIELDS, PASS_FIELDS, _fields, _load, device_from_data, recipe_from_json
from .laser_recipe_db import Lens, LaserRecipeDatabase, Machine, Material, RecipeEntry, store_recipe

KIND = 'mikrocam.laser-recipe-db'
SCHEMA_VERSION = 1
MAX_DATABASE_BYTES = 16 * 1024 * 1024
DOCUMENT_FIELDS = {'kind', 'schema_version', 'materials', 'lenses', 'machines', 'recipes'}
MATERIAL_FIELDS = {'id', 'name', 'thickness_mm', 'notes'}
LENS_FIELDS = {'id', 'name', 'focal_length_mm', 'notes'}
MACHINE_FIELDS = {'id', 'device', 'notes'}
RECIPE_FIELDS = {'id', 'name', 'machine_id', 'material_id', 'lens_id', 'notes', 'passes'}
CONTEXT = 'recipe database'


def migrate_database_data(data: dict) -> dict:
    """Return current-version data; each later schema adds one explicit step here."""
    version = data.get('schema_version') if isinstance(data, dict) else None
    if type(version) is not int or version != SCHEMA_VERSION:
        raise ValueError(f'{CONTEXT}.schema_version is unsupported: {version!r}')
    return data


def _array(value: object, context: str) -> list:
    if type(value) is not list:
        raise ValueError(f'{context} must be an array')
    return value


def _entry(value: object, machines: dict[str, Machine], index: int) -> RecipeEntry:
    context = f'{CONTEXT}.recipes[{index}]'
    data = _fields(value, RECIPE_FIELDS, context)
    machine = machines.get(data['machine_id']) if data['machine_id'] is not None else None
    if data['machine_id'] is not None and machine is None:
        raise ValueError(f'{context} references unknown machine_id {data["machine_id"]!r}')
    passes = []
    for number, item in enumerate(_array(data['passes'], f'{context}.passes')):
        fields = _fields(item, PASS_FIELDS if machine is None else DEVICE_PASS_FIELDS, f'{context}.passes[{number}]')
        passes.append(LaserPass(**fields))
    recipe = LaserRecipe(data['name'], tuple(passes), None if machine is None else machine.device)
    return RecipeEntry(data['id'], recipe, data['machine_id'], data['material_id'], data['lens_id'], data['notes'])


def _database(data: dict) -> LaserRecipeDatabase:
    materials = tuple(Material(**_fields(value, MATERIAL_FIELDS, f'{CONTEXT}.materials[{index}]'))
                      for index, value in enumerate(_array(data['materials'], 'materials')))
    lenses = tuple(Lens(**_fields(value, LENS_FIELDS, f'{CONTEXT}.lenses[{index}]'))
                   for index, value in enumerate(_array(data['lenses'], 'lenses')))
    machines = []
    for index, value in enumerate(_array(data['machines'], 'machines')):
        item = _fields(value, MACHINE_FIELDS, f'{CONTEXT}.machines[{index}]')
        machines.append(Machine(item['id'], device_from_data(item['device']), item['notes']))
    by_id = {machine.id: machine for machine in machines}
    recipes = tuple(_entry(value, by_id, index) for index, value in enumerate(_array(data['recipes'], 'recipes')))
    return LaserRecipeDatabase(materials, lenses, tuple(machines), recipes)


def database_from_json(text: str) -> LaserRecipeDatabase:
    """Read a complete strict document; malformed, future or oversized input is rejected."""
    if not isinstance(text, str):
        raise ValueError(f'{CONTEXT} JSON must be text')
    if len(text.encode('utf-8')) > MAX_DATABASE_BYTES:
        raise ValueError(f'{CONTEXT} exceeds the {MAX_DATABASE_BYTES} byte size limit')
    data = _load(text, CONTEXT)
    if not isinstance(data, dict):
        raise ValueError(f'{CONTEXT} must be an object')
    if data.get('kind') != KIND:
        raise ValueError(f'{CONTEXT}.kind must be {KIND!r}')
    data = _fields(migrate_database_data(data), DOCUMENT_FIELDS, CONTEXT)
    try:
        return _database(data)
    except (TypeError, KeyError) as error:
        raise ValueError(f'{CONTEXT} is malformed: {error}') from error


def _recipe_data(entry: RecipeEntry) -> dict:
    fields = PASS_FIELDS if entry.recipe.device is None else DEVICE_PASS_FIELDS
    return {'id': entry.id, 'name': entry.recipe.name, 'machine_id': entry.machine_id,
            'material_id': entry.material_id, 'lens_id': entry.lens_id, 'notes': entry.notes,
            'passes': [{field: getattr(value, field) for field in fields} for value in entry.recipe.passes]}


def database_to_json(database: LaserRecipeDatabase) -> str:
    """Deterministic, indented UTF-8 text; device profiles are stored once per machine."""
    if not isinstance(database, LaserRecipeDatabase):
        raise ValueError('Expected LaserRecipeDatabase')
    data = {'kind': KIND, 'schema_version': SCHEMA_VERSION,
            'materials': [asdict(value) for value in database.materials],
            'lenses': [asdict(value) for value in database.lenses],
            'machines': [{'id': value.id, 'device': asdict(value.device), 'notes': value.notes}
                         for value in database.machines],
            'recipes': [_recipe_data(entry) for entry in database.recipes]}
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'


def import_recipe_texts(database: LaserRecipeDatabase, texts: Iterable[str], material_id: str | None,
                        lens_id: str | None, new_id: Callable[[], str]) -> LaserRecipeDatabase:
    """Import schema1/schema2 recipe files all-or-nothing; identical repeats are no-ops."""
    for number, text in enumerate(texts, 1):
        try:
            database, _, _ = store_recipe(database, recipe_from_json(text), material_id, lens_id, new_id)
        except ValueError as error:
            raise ValueError(f'recipe file {number}: {error}') from error
    return database
