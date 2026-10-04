"""Immutable material, lens, machine and recipe catalog with one device-profile source."""
from collections.abc import Callable
from dataclasses import dataclass, replace
import re

from .laser_device import LaserDeviceProfile
from .laser_job import LaserRecipe
from .placement import _finite_real

MAX_ENTRIES = 10_000
MAX_NAME = 256
MAX_NOTES = 4000
_ID = re.compile(r'[a-z0-9][a-z0-9_-]{0,63}')
_TABLES = ('materials', 'lenses', 'machines', 'recipes')


def _check_id(value: object, context: str) -> None:
    if type(value) is not str or not _ID.fullmatch(value):
        raise ValueError(f'{context}.id must match [a-z0-9][a-z0-9_-]{{0,63}}')


def _check_text(name: object, notes: object, context: str) -> None:
    if type(name) is not str or not name.strip() or len(name) > MAX_NAME:
        raise ValueError(f'{context}.name requires nonempty text of at most {MAX_NAME} characters')
    if type(notes) is not str or len(notes) > MAX_NOTES:
        raise ValueError(f'{context}.notes requires text of at most {MAX_NOTES} characters')


def _optional_length(owner: object, field: str, context: str) -> None:
    value = getattr(owner, field)
    if value is None:
        return
    number = _finite_real(value, f'{context}.{field}')
    if number <= 0:
        raise ValueError(f'{context}.{field} must be positive millimetres or empty')
    object.__setattr__(owner, field, number)


def _key(name: str) -> str:
    return name.strip().casefold()


class RecipeExistsError(ValueError):
    """The recipe key is taken by different values; replacing needs explicit consent."""


@dataclass(frozen=True)
class Material:
    """User-named workpiece material; thickness is optional and never assumed."""
    id: str
    name: str
    thickness_mm: float | None = None
    notes: str = ''

    def __post_init__(self) -> None:
        _check_id(self.id, 'material')
        _check_text(self.name, self.notes, 'material')
        _optional_length(self, 'thickness_mm', 'material')


@dataclass(frozen=True)
class Lens:
    """User-named lens; focal length is optional user data, not a catalog value."""
    id: str
    name: str
    focal_length_mm: float | None = None
    notes: str = ''

    def __post_init__(self) -> None:
        _check_id(self.id, 'lens')
        _check_text(self.name, self.notes, 'lens')
        _optional_length(self, 'focal_length_mm', 'lens')


@dataclass(frozen=True)
class Machine:
    """The single stored source of a laser device profile shared by its recipes."""
    id: str
    device: LaserDeviceProfile
    notes: str = ''

    def __post_init__(self) -> None:
        _check_id(self.id, 'machine')
        if not isinstance(self.device, LaserDeviceProfile):
            raise ValueError('machine.device requires LaserDeviceProfile')
        _check_text(self.device.name, self.notes, 'machine')

    @property
    def name(self) -> str:
        return self.device.name


@dataclass(frozen=True)
class RecipeEntry:
    """A full recipe snapshot labelled by optional material, machine and lens references."""
    id: str
    recipe: LaserRecipe
    machine_id: str | None = None
    material_id: str | None = None
    lens_id: str | None = None
    notes: str = ''

    def __post_init__(self) -> None:
        _check_id(self.id, 'recipe')
        if not isinstance(self.recipe, LaserRecipe):
            raise ValueError('recipe.recipe requires LaserRecipe')
        _check_text(self.recipe.name, self.notes, 'recipe')
        for field in ('machine_id', 'material_id', 'lens_id'):
            if getattr(self, field) is not None:
                _check_id(getattr(self, field), f'recipe.{field}')

    @property
    def key(self) -> tuple[str | None, str | None, str | None, str]:
        return self.material_id, self.machine_id, self.lens_id, _key(self.recipe.name)


def _unique(values: tuple, label: Callable[[object], str], table: str) -> dict[str, object]:
    by_id, names = {}, set()
    for value in values:
        if value.id in by_id:
            raise ValueError(f'{table} contains duplicate id {value.id!r}')
        name = _key(label(value))
        if name in names:
            raise ValueError(f'{table} contains duplicate name {label(value)!r}')
        by_id[value.id] = value
        names.add(name)
    return by_id


@dataclass(frozen=True)
class LaserRecipeDatabase:
    """Ordered catalog tables; every operation returns a new fully validated value."""
    materials: tuple[Material, ...] = ()
    lenses: tuple[Lens, ...] = ()
    machines: tuple[Machine, ...] = ()
    recipes: tuple[RecipeEntry, ...] = ()

    def __post_init__(self) -> None:
        for table, kind in zip(_TABLES, (Material, Lens, Machine, RecipeEntry)):
            values = getattr(self, table)
            if type(values) is not tuple or len(values) > MAX_ENTRIES:
                raise ValueError(f'{table} requires a tuple of at most {MAX_ENTRIES} values')
            if not all(isinstance(value, kind) for value in values):
                raise ValueError(f'{table} must contain only {kind.__name__} values')
        materials = _unique(self.materials, lambda value: value.name, 'materials')
        lenses = _unique(self.lenses, lambda value: value.name, 'lenses')
        machines = _unique(self.machines, lambda value: value.name, 'machines')
        _unique(self.recipes, lambda value: value.id, 'recipes')
        keys = set()
        for entry in self.recipes:
            context = f'recipe {entry.recipe.name!r}'
            for field, table in (('material_id', materials), ('lens_id', lenses), ('machine_id', machines)):
                reference = getattr(entry, field)
                if reference is not None and reference not in table:
                    raise ValueError(f'{context} references unknown {field} {reference!r}')
            device = None if entry.machine_id is None else machines[entry.machine_id].device
            if entry.recipe.device != device:
                raise ValueError(f'{context} device profile must equal its machine profile '
                                 '(no machine for an unspecified legacy device)')
            if entry.key in keys:
                raise ValueError(f'{context} already exists for this material, machine and lens')
            keys.add(entry.key)


def _with(values: tuple, value: object) -> tuple:
    if any(item.id == value.id for item in values):
        return tuple(value if item.id == value.id else item for item in values)
    return values + (value,)


def _put(database: LaserRecipeDatabase, table: str, value: object) -> LaserRecipeDatabase:
    return replace(database, **{table: _with(getattr(database, table), value)})


def _users(database: LaserRecipeDatabase, field: str, key: str) -> list[str]:
    return [entry.recipe.name for entry in database.recipes if getattr(entry, field) == key]


def _remove(database: LaserRecipeDatabase, table: str, field: str | None, key: str) -> LaserRecipeDatabase:
    values = getattr(database, table)
    if not any(item.id == key for item in values):
        raise ValueError(f'Cannot remove unknown {table} id {key!r}')
    users = _users(database, field, key) if field else []
    if users:
        raise ValueError(f'Cannot remove {table} entry used by recipes: {", ".join(users)}')
    return replace(database, **{table: tuple(item for item in values if item.id != key)})


def put_material(database: LaserRecipeDatabase, material: Material) -> LaserRecipeDatabase:
    """Insert or replace one material by id, keeping table order."""
    return _put(database, 'materials', material)


def put_lens(database: LaserRecipeDatabase, lens: Lens) -> LaserRecipeDatabase:
    """Insert or replace one lens by id, keeping table order."""
    return _put(database, 'lenses', lens)


def put_recipe(database: LaserRecipeDatabase, entry: RecipeEntry) -> LaserRecipeDatabase:
    """Insert or replace one recipe entry by id after whole-catalog validation."""
    return _put(database, 'recipes', entry)


def put_machine(database: LaserRecipeDatabase, machine: Machine) -> LaserRecipeDatabase:
    """Replace a profile and revalidate every dependent recipe with it, or change nothing."""
    recipes = []
    for entry in database.recipes:
        if entry.machine_id != machine.id:
            recipes.append(entry)
            continue
        try:
            rebound = LaserRecipe(entry.recipe.name, entry.recipe.passes, machine.device)
        except ValueError as error:
            raise ValueError(f'recipe {entry.recipe.name!r} is invalid for the updated machine: {error}') from error
        recipes.append(replace(entry, recipe=rebound))
    return replace(database, machines=_with(database.machines, machine), recipes=tuple(recipes))


def remove_material(database: LaserRecipeDatabase, material_id: str) -> LaserRecipeDatabase:
    """Remove an unused material; a used one is an explicit error naming its recipes."""
    return _remove(database, 'materials', 'material_id', material_id)


def remove_lens(database: LaserRecipeDatabase, lens_id: str) -> LaserRecipeDatabase:
    """Remove an unused lens; a used one is an explicit error naming its recipes."""
    return _remove(database, 'lenses', 'lens_id', lens_id)


def remove_machine(database: LaserRecipeDatabase, machine_id: str) -> LaserRecipeDatabase:
    """Remove an unused machine; a used one is an explicit error naming its recipes."""
    return _remove(database, 'machines', 'machine_id', machine_id)


def remove_recipe(database: LaserRecipeDatabase, entry_id: str) -> LaserRecipeDatabase:
    """Remove one recipe entry; catalog entries stay until explicitly removed."""
    return _remove(database, 'recipes', None, entry_id)


def machine_for_device(database: LaserRecipeDatabase, device: LaserDeviceProfile) -> Machine | None:
    """Return the exactly equal machine profile; a same-name different profile conflicts."""
    for machine in database.machines:
        if machine.device == device:
            return machine
        if _key(machine.name) == _key(device.name):
            raise ValueError(f'machine {machine.name!r} is stored with a different profile; '
                             'update the machine profile or use another profile name')
    return None


def machine_named(database: LaserRecipeDatabase, name: str) -> Machine | None:
    """The machine whose profile name matches without case or edge spaces."""
    return next((machine for machine in database.machines if _key(machine.name) == _key(name)), None)


def find_recipe(database: LaserRecipeDatabase, name: str, machine_id: str | None,
                material_id: str | None, lens_id: str | None) -> RecipeEntry | None:
    """Look up the unique recipe key, comparing names without case or edge spaces."""
    key = (material_id, machine_id, lens_id, _key(name))
    return next((entry for entry in database.recipes if entry.key == key), None)


def store_recipe(database: LaserRecipeDatabase, recipe: LaserRecipe, material_id: str | None,
                 lens_id: str | None, new_id: Callable[[], str], replace: bool = False,
                 ) -> tuple[LaserRecipeDatabase, RecipeEntry, bool]:
    """Add a recipe under its profile's machine; differing same-key values need replace=True."""
    machine = None if recipe.device is None else machine_for_device(database, recipe.device)
    if recipe.device is not None and machine is None:
        machine = Machine(new_id(), recipe.device)
        database = _put(database, 'machines', machine)
    machine_id = None if machine is None else machine.id
    existing = find_recipe(database, recipe.name, machine_id, material_id, lens_id)
    if existing is not None and existing.recipe == recipe:
        return database, existing, False
    if existing is not None and not replace:
        raise RecipeExistsError(f'recipe {recipe.name!r} already exists for this material, machine and lens '
                         'with different values')
    entry = (RecipeEntry(new_id(), recipe, machine_id, material_id, lens_id) if existing is None
             else _replace_recipe(existing, recipe))
    return put_recipe(database, entry), entry, True


def _replace_recipe(entry: RecipeEntry, recipe: LaserRecipe) -> RecipeEntry:
    return replace(entry, recipe=recipe)


def entry_labels(database: LaserRecipeDatabase, entry: RecipeEntry) -> tuple[str | None, str | None, str | None]:
    """Material, machine and lens display names; None means explicitly unspecified."""
    def name(table: tuple, key: str | None) -> str | None:
        return None if key is None else next(item.name for item in table if item.id == key)
    return (name(database.materials, entry.material_id), name(database.machines, entry.machine_id),
            name(database.lenses, entry.lens_id))


def matching_recipes(database: LaserRecipeDatabase, text: str = '') -> tuple[RecipeEntry, ...]:
    """Entries whose recipe, material, machine or lens name contains the search text."""
    needle = _key(text)
    if not needle:
        return database.recipes
    return tuple(entry for entry in database.recipes
                 if any(needle in _key(label) for label in (entry.recipe.name, *entry_labels(database, entry))
                        if label is not None))
