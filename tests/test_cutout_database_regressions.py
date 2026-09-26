"""Explicit cutout database settings must survive both real insertion routes."""
from copy import deepcopy
import json
import logging
from types import SimpleNamespace

import pytest
from PyQt6 import QtCore

from test_mechanical_dwell_regressions import cutout_fixture


def database_tool():
    from defaults import AppDefaults
    data = {key: deepcopy(value) for key, value in AppDefaults.factory_defaults.items() if key.startswith('tools_')}
    data.update(tool_target=6, tol_min=2.3, tol_max=2.5,
                tools_cutout_z=-1.75, tools_cutout_mdepth=True, tools_cutout_depthperpass=.3,
                tools_mill_cutz=-.25, tools_mill_multidepth=False, tools_mill_depthperpass=.1)
    return dict(name='explicit-cutout-settings', tooldia=2.4, data=data)


def cutout_tool_fixture(qtbot, tmp_path):
    from appPlugins.ToolCutOut import CutOut
    from appGUI.GUIElements import FCDoubleSpinner
    from defaults import AppDefaults
    ui = cutout_fixture(qtbot, 'a')
    ui.dia = FCDoubleSpinner()
    ui.dia.set_range(.01, 100)
    qtbot.addWidget(ui.dia)
    path = tmp_path / 'tools.FlatDB'
    record = database_tool()
    path.write_text(json.dumps({'1': record}), encoding='utf-8')
    options = deepcopy(AppDefaults.factory_defaults)
    signals = QtCore.QObject()
    messages = []
    app = SimpleNamespace(options=options, tools_database_path=lambda: str(path),
        dec_format=lambda value, decimals: round(value, decimals), log=logging.getLogger('cutout-database'),
        inform=SimpleNamespace(emit=messages.append))
    tool = SimpleNamespace(app=app, ui=ui, decimals=3, default_data=deepcopy(options), cut_tool_dict={},
                           blockSignals=signals.blockSignals)
    tool.update_ui = lambda data: CutOut.update_ui(tool, data)
    tool.on_cutout_type = lambda value: CutOut.on_cutout_type(tool, value)
    tool.on_tool_default_add = lambda **kwargs: pytest.fail('Valid matching database record must be selected')
    return tool, record, path


@pytest.mark.parametrize('route', ['exact', 'tolerance', 'picker'])
@pytest.mark.parametrize('parameter,expected,control', [
    ('tools_cutout_z', -1.75, 'cutz_entry'),
    ('tools_cutout_mdepth', True, 'mpass_cb'),
    ('tools_cutout_depthperpass', .3, 'maxdepth_entry')])
def test_cutout_database_values_are_not_overwritten_by_milling_values(qtbot, tmp_path, route, parameter, expected, control):
    from appPlugins.ToolCutOut import CutOut
    tool, record, path = cutout_tool_fixture(qtbot, tmp_path)
    original_record = deepcopy(record)
    original_file = path.read_bytes()
    if route == 'picker':
        assert CutOut.on_cutout_tool_add_from_db_executed(tool, record) is True
    else:
        CutOut.on_tool_add(tool, custom_dia=2.4 if route == 'exact' else 2.45)
    assert tool.cut_tool_dict['data'][parameter] == expected
    assert getattr(tool.ui, control).get_value() == expected
    assert tool.cut_tool_dict['tooldia'] == 2.4
    assert tool.cut_tool_dict['solid_geometry'] == []
    assert record == original_record
    assert path.read_bytes() == original_file
