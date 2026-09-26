"""Mechanical tool regressions against real legacy rebuilds and Qt tables.

The global pytest settings sandbox runs before these deferred legacy imports.
Only unrelated signal connections are omitted from the minimized host fixtures.
"""
from copy import deepcopy
import logging
from types import SimpleNamespace

import pytest
from PyQt6 import QtWidgets
from shapely.geometry import Point


def host():
    return SimpleNamespace(log=logging.getLogger('mechanical-regression'), app_units='MM',
                           dec_format=lambda value: round(value, 3),
                           exc_areas=SimpleNamespace(exclusion_areas_storage=[]))


def table(qtbot, columns):
    from appGUI.GUIElements import FCTable
    value = FCTable()
    value.setColumnCount(columns)
    qtbot.addWidget(value)
    return value


@pytest.mark.parametrize('database_diameter', [.8, .81], ids=['exact', 'within-tolerance'])
def test_drilling_database_replacement_survives_real_default_order_rebuild(qtbot, database_diameter):
    from appPlugins.ToolDrilling import ToolDrilling
    from appGUI.GUIElements import FCDoubleSpinner
    source = SimpleNamespace(tools={1: dict(tooldia=.8, drills=[Point(1, 2)], slots=[],
                                          data={'tools_drill_feedrate_z': 99.0})})
    database = {'1': dict(tooldia=database_diameter, data=dict(tool_target=2, tol_min=.79, tol_max=.82,
                         tools_drill_feedrate_z=321.0, tools_mill_feedrate=777.0))}
    original_database = deepcopy(database)
    feed = FCDoubleSpinner()
    feed.set_range(0, 1000)
    qtbot.addWidget(feed)
    ui = SimpleNamespace(order_combo=SimpleNamespace(get_value=lambda: 0),
                         exc_param_frame=QtWidgets.QFrame(), tools_table=table(qtbot, 5),
                         exclusion_table=table(qtbot, 4), tool_data_label=QtWidgets.QLabel())
    qtbot.addWidget(ui.exc_param_frame)
    qtbot.addWidget(ui.tool_data_label)
    tool = SimpleNamespace(app=host(), ui=ui, excellon_obj=source, excellon_tools=deepcopy(source.tools),
                           tools_db_dict=database, dec_format=lambda value: round(value, 3),
                           ui_disconnect=lambda: None, ui_connect=lambda: None,
                           general_form_fields={}, tool_form_fields={'tools_drill_feedrate_z': feed})
    tool.build_tool_ui = lambda: ToolDrilling.build_tool_ui(tool)
    ToolDrilling.replace_tools(tool)
    tool.build_tool_ui()
    ToolDrilling.storage_to_form(tool, tool.excellon_tools[1]['data'])
    assert feed.get_value() == 321.0
    assert source.tools[1]['data']['tools_drill_feedrate_z'] == 321.0
    assert source.tools[1]['tooldia'] == database_diameter
    assert tool.excellon_tools[1]['drills'] == [Point(1, 2)]
    assert 'tools_mill_feedrate' not in source.tools[1]['data']
    assert database == original_database
