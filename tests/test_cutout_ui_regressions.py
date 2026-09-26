"""Cutout mode remains separate from gap type during restoration."""
from types import SimpleNamespace

import pytest

from test_mechanical_dwell_regressions import cutout_fixture


@pytest.mark.parametrize('blocked', [False, True], ids=['signals-connected', 'signals-blocked'])
@pytest.mark.parametrize('mode', ['a', 'm'], ids=['automatic', 'manual'])
@pytest.mark.parametrize('gap_type', [1, 2], ids=['thin-gap', 'mouse-bites'])
def test_cutout_update_restores_cutout_mode_independently_of_gap_type(qtbot, mode, gap_type, blocked):
    from appPlugins.ToolCutOut import CutOut
    ui = cutout_fixture(qtbot, mode)
    ui.gaptype_combo.blockSignals(blocked)
    tool = SimpleNamespace(ui=ui, default_data={'tools_cutout_kind': 'single', 'tools_cutout_big_cursor': False})
    tool.on_cutout_type = lambda value: CutOut.on_cutout_type(tool, value)
    data = dict(tools_cutout_margin=.1, tools_cutout_gapsize=.8, tools_cutout_gap_type=gap_type,
                tools_cutout_gap_depth=-.05, tools_cutout_mb_dia=.4, tools_cutout_mb_spacing=.3,
                tools_cutout_convexshape=False, tools_cutout_gaps_ff='4', tools_cutout_z=-1,
                tools_cutout_mdepth=False, tools_cutout_depthperpass=.2)
    CutOut.update_ui(tool, data)
    assert ui.cutout_type_radio.get_value() == mode
    assert ui.generate_cutout_btn.isHidden() is (mode == 'm')
    assert ui.man_frame.isHidden() is (mode == 'a')
    assert ui.gaps.isHidden() is (mode == 'm')
    assert ui.thin_depth_entry.isHidden() is (gap_type != 1)
    assert ui.mb_dia_entry.isHidden() is (gap_type != 2)
    assert ui.mb_spacing_entry.isHidden() is (gap_type != 2)
