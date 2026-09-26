"""New and backfilled database records use supported machining defaults.

Scope follows immutable MIT upstream f239fcbb's six namespaces and explicit
application-only exclusions. The fixtures call real creation/normalization,
without saving or reloading the newly created record to conceal missing keys.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from PyQt6 import QtWidgets


PREFIXES = ('tools_drill_', 'tools_mill_', 'tools_iso_', 'tools_ncc_', 'tools_paint_', 'tools_cutout_')
EXCLUDED = {'tools_drill_tool_order', 'tools_drill_preprocessor_list', 'tools_mill_tooldia',
            'tools_mill_preprocessor_list', 'tools_iso_tooldia', 'tools_iso_order', 'tools_ncc_tools',
            'tools_ncc_order', 'tools_paint_tooldia', 'tools_paint_order', 'tools_cutout_tooldia',
            'tools_cutout_big_cursor'}
LASER_OPTIONS = {'tools_mill_min_power': 11.5, 'tools_mill_laser_on': 'M3',
                 'tools_drill_min_power': 12.5, 'tools_drill_laser_on': 'M4'}


def default_options():
    from defaults import AppDefaults
    options = deepcopy(AppDefaults.factory_defaults)
    options.update(LASER_OPTIONS, tools_mill_tooldia=2.4)
    return options


def new_database_fixture(qtbot):
    from appDatabase import ToolsDB2
    tree = QtWidgets.QTreeWidget()
    tree.setColumnCount(2)
    qtbot.addWidget(tree)
    options = default_options()
    existing = dict(name='existing-explicit', tooldia=1.2,
                    data={'tools_mill_min_power': 42., 'tools_cutout_z': -2.75})
    messages = []
    app = SimpleNamespace(options=options, inform=SimpleNamespace(emit=messages.append),
                          tools_db_changed_flag=False)
    database = SimpleNamespace(app=app, db_tool_dict={'1': existing}, ui=SimpleNamespace(tree_widget=tree),
                               on_tool_target_changed=lambda **kwargs: None,
                               on_tools_db_edited=lambda: setattr(app, 'tools_db_changed_flag', True))
    def render_tree():
        tree.clear()
        for identifier, record in database.db_tool_dict.items():
            tree.addTopLevelItem(QtWidgets.QTreeWidgetItem([identifier, record['name']]))
    database.build_db_ui = render_tree
    before = deepcopy(existing)
    ToolsDB2.on_tool_add(database)
    assert database.db_tool_dict['1'] == before
    assert app.tools_db_changed_flag is True
    assert tree.currentItem().text(0) == '2'
    return database.db_tool_dict['2']['data'], options


@pytest.mark.parametrize('key', LASER_OPTIONS)
def test_new_tool_contains_current_laser_settings_before_any_save_or_reload(qtbot, key):
    data, options = new_database_fixture(qtbot)
    assert key in data
    assert data[key] == options[key]


def test_new_tool_has_every_eligible_supported_namespace_default(qtbot):
    data, options = new_database_fixture(qtbot)
    eligible = {key for key in options if key.startswith(PREFIXES) and key not in EXCLUDED}
    assert not eligible - data.keys(), f'Missing machining defaults: {sorted(eligible - data.keys())}'
    assert {key: data[key] for key in eligible} == {key: options[key] for key in eligible}
    assert not EXCLUDED & data.keys()
    assert not {key for key in data if key.startswith('tools_') and not key.startswith(PREFIXES)}


def test_normalization_backfills_only_canonical_defaults_without_overwriting_explicit_data():
    from appDatabase import normalize_tools_database
    options = default_options()
    original = {'1': dict(name='explicit', tooldia=1.2,
                         data=dict(tool_target=0, tools_mill_feedrate=135., tools_mill_min_power=42.))}
    before = deepcopy(original)
    result = normalize_tools_database(original, options)['1']['data']
    assert original == before
    assert result['tools_mill_feedrate'] == 135.
    assert result['tools_mill_min_power'] == 42.
    eligible = {key for key in options if key.startswith(PREFIXES) and key not in EXCLUDED}
    assert eligible <= result.keys()
    unrelated = {key for key in options if key.startswith('tools_') and not key.startswith(PREFIXES)}
    assert unrelated  # real application UI-tool defaults are present in the host
    assert not unrelated & result.keys(), f'Unrelated defaults backfilled: {sorted(unrelated & result.keys())}'
    assert not EXCLUDED & result.keys()
