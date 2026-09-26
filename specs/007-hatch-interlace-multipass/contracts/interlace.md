# Contracts
`mikrocam.laser.interlace.interlace_paths(paths: tuple[LaserPath,...], n: int,
cancelled: CancelCheck=None) -> tuple[LaserPath,...]` uses no Qt/Shapely/host imports.
Planner calls this before final placement, once per geometry plan, not once per recipe pass.
`LaserPlan.pass_plans -> tuple[LaserPassPlan,...]` preserves exact settings/path tuple identity.

`mikrocam.ui.laser_recipe.LaserRecipeEditor(QWidget)` public API:
- `changed` signal, `set_recipe(recipe)`, `get_recipe() -> LaserRecipe`;
- `name_edit: QLineEdit`, `table: QTableWidget` with name/power/speed/frequency/pulse columns;
- `add_pass()`, `remove_pass()`, `move_pass(offset)`; new numeric cells are blank.
- `save_recipe_file(path, recipe)` same-directory temp + replace, cleanup on failure.

Panel keeps existing load button/set_recipe public API, adds editor, save button and
`interlace_n: QSpinBox` 1..1,000,000. set_recipe populates editor; _request obtains current
validated editor recipe; editor changed calls existing _input_changed. Status after success
includes explicit pass count. Existing fake-host tests remain compatible after integration.
