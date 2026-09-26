"""Distinct Excellon tools survive display rounding."""
from types import SimpleNamespace

import pytest
from PyQt6 import QtWidgets
from shapely.geometry import Point

from test_mechanical_tool_regressions import host, table


@pytest.mark.parametrize('order', [0, 1, 2], ids=['source-order', 'ascending', 'descending'])
def test_excellon_milling_preserves_distinct_tools_with_equal_display_diameters(qtbot, order):
    from appPlugins.ToolMilling import ToolMilling
    source = SimpleNamespace(tools={
        1: dict(tooldia=.8001, drills=[Point(1, 2)], slots=[], data={'identity': 'first'}),
        2: dict(tooldia=.8002, drills=[Point(3, 4)], slots=[], data={'identity': 'second'})})
    ui = SimpleNamespace(param_frame=QtWidgets.QFrame(), order_combo=SimpleNamespace(get_value=lambda: order),
                         tools_table_mill_exc=table(qtbot, 5))
    qtbot.addWidget(ui.param_frame)
    tool = SimpleNamespace(app=host(), ui=ui, target_obj=source, decimals=3,
                           tot_drill_cnt=0, tot_slot_cnt=0)
    for _ in range(2):
        ToolMilling.build_ui_exc(tool)
        assert len(source.tools) == 2
        assert ui.tools_table_mill_exc.rowCount() == 4  # two real tools, two totals
        assert tool.tot_drill_cnt == 2
        expected = [.8002, .8001] if order == 2 else [.8001, .8002]
        assert [value['tooldia'] for value in source.tools.values()] == expected
        assert sorted(value['data']['identity'] for value in source.tools.values()) == ['first', 'second']
        assert {tuple(value['drills'][0].coords[0]) for value in source.tools.values()} == {(1, 2), (3, 4)}
