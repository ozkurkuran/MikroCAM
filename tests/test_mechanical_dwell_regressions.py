"""Real mechanical UI methods must preserve selected tool parameters and modes."""
from copy import deepcopy
import logging
from types import SimpleNamespace

import pytest
from PyQt6 import QtWidgets
from shapely.geometry import LineString


def milling_fixture(qtbot):
    from appGUI.GUIElements import FCTable, FCComboBox2
    fields = ('add_tool_frame offset_type_lbl offset_label offset_entry offset_separator_line '
              'job_type_lbl job_type_combo job_separator_line mpass_cb maxdepth_entry extracut_cb '
              'e_cut_entry dwell_cb dwelltime_entry endmove_xy_label endxy_entry exclusion_cb apply_param_to_all')
    ui = SimpleNamespace(**{name: QtWidgets.QWidget() for name in fields.split()})
    ui.level = QtWidgets.QToolButton()
    ui.offset_type_combo = FCComboBox2()
    ui.offset_type_combo.addItems(['Path', 'Inside', 'Outside', 'Custom'])
    ui.tools_table_mill_geo = FCTable()
    ui.object_combo = SimpleNamespace(get_value=lambda: 'geometry')
    ui.target_radio = SimpleNamespace(get_value=lambda: 'geo')
    for widget in vars(ui).values():
        if isinstance(widget, QtWidgets.QWidget):
            qtbot.addWidget(widget)
    options = dict(tools_mill_offset_type=0, tools_mill_offset_value=0., tools_mill_job_type=0,
                   tools_mill_extracut=False, tools_mill_dwell=False, tools_mill_area_exclusion=False)
    data = dict(options, tools_mill_dwell=True, tools_mill_dwelltime=4.2)
    source = SimpleNamespace(tools={1: {'data': data}}, obj_options=deepcopy(options))
    app = SimpleNamespace(options=options, collection=SimpleNamespace(get_by_name=lambda name: source))
    return SimpleNamespace(app=app, ui=ui, target_obj=source, on_pp_changed=lambda: None), data


def actual_cnc_gcode(data):
    from camlib import CNCjob, Geometry
    from defaults import AppDefaults
    from preprocessors.default import default
    options = deepcopy(AppDefaults.factory_defaults)
    options.update(units='MM', tools_mill_optimization_type='N', cncjob_coords_type='G90')
    app = SimpleNamespace(options=options, defaults=options, decimals=4, abort_flag=False, app_units='MM',
        use_3d_engine=True, is_legacy=False, log=logging.getLogger('dwell-regression'),
        preprocessors={'default': default()}, inform=SimpleNamespace(emit=lambda *args: None),
        proc_container=SimpleNamespace(update_view_text=lambda *args: None),
        plotcanvas=SimpleNamespace(new_shape_collection=lambda **kwargs: None),
        exc_areas=SimpleNamespace(exclusion_areas_storage=[],
                                 travel_coordinates=lambda **kwargs: [[None, kwargs['end_point']]]))
    geometry = Geometry(app=app, geo_steps_per_circle=64)
    geometry.solid_geometry = [LineString([(0, 0), (2, 0)])]
    geometry.obj_options = dict(name='dwell-test', type='Geometry', tool_dia=.2, xmin=0, ymin=0, xmax=2, ymax=0)
    geometry.multigeo = False
    cnc = CNCjob(app=app, units='MM', steps_per_circle=64)
    cnc.obj_options = geometry.obj_options
    cnc.origin_kind = 'geometry'
    cnc.coords_decimals, cnc.fr_decimals = 4, 2
    body, header = cnc.generate_from_geometry_2(geometry, append=False, tooldia=.2, offset=0, tolerance=0,
        z_cut=-.1, z_move=2, feedrate=120, feedrate_z=60, feedrate_rapid=300, spindlespeed=10000,
        spindle_dir='CW', dwell=data['tools_mill_dwell'], dwelltime=data['tools_mill_dwelltime'],
        multidepth=False, depthpercut=.1, toolchange=False, toolchangez=2, toolchangexy='',
        extracut=False, extracut_length=0, startz=2, endz=2, endxy='0,0', pp_geometry_name='default',
        tool_no=1, is_first=True)
    return header + body


@pytest.mark.parametrize('levels', [(False, True, False), (True, False, True)], ids=['basic-first', 'advanced-first'])
def test_milling_level_switch_preserves_custom_dwell_and_actual_g4(qtbot, levels):
    from appPlugins.ToolMilling import ToolMilling
    tool, data = milling_fixture(qtbot)
    assert 'G4 P4.2' in actual_cnc_gcode(data)
    outputs = []
    for checked in levels:
        ToolMilling.on_level_changed(tool, checked)
        outputs.append(actual_cnc_gcode(data))
    assert all('G4 P4.2' in output for output in outputs)
    assert data['tools_mill_dwell'] is True
    assert data['tools_mill_dwelltime'] == 4.2


def cutout_fixture(qtbot, mode):
    from appPlugins.ToolCutOut import CutoutUI
    from appGUI.GUIElements import FCComboBox, FCComboBox2, FCCheckBox, FCDoubleSpinner, RadioSet
    ui = SimpleNamespace()
    for name in ('margin gapsize thin_depth_entry mb_dia_entry mb_spacing_entry cutz_entry maxdepth_entry').split():
        widget = FCDoubleSpinner()
        widget.set_range(-100, 100)
        setattr(ui, name, widget)
    for name in ('big_cursor_cb convex_box_cb mpass_cb').split():
        setattr(ui, name, FCCheckBox())
    for name in ('gaps_label generate_cutout_btn man_geo_creation_btn man_gaps_creation_btn man_frame '
                 'thin_depth_label mb_dia_label mb_spacing_label').split():
        setattr(ui, name, QtWidgets.QWidget())
    ui.obj_kind_combo = RadioSet([dict(label='Single', value='single'), dict(label='Panel', value='panel')])
    ui.cutout_type_radio = RadioSet([dict(label='Automatic', value='a'), dict(label='Manual', value='m')])
    ui.cutout_type_radio.set_value(mode)
    ui.gaptype_combo = FCComboBox2()
    ui.gaptype_combo.addItems(['Bridge', 'Thin', 'Mouse Bytes'])
    ui.gaps = FCComboBox()
    ui.gaps.addItems(['4', '8'])
    ui.on_gap_type_radio = lambda index: CutoutUI.on_gap_type_radio(ui, index)
    ui.gaptype_combo.currentIndexChanged.connect(ui.on_gap_type_radio)
    ui.on_gap_type_radio(0)
    for widget in vars(ui).values():
        if isinstance(widget, QtWidgets.QWidget):
            qtbot.addWidget(widget)
    return ui


@pytest.mark.parametrize('levels', [(False, True, False), (True, False, True)], ids=['basic-first', 'advanced-first'])
@pytest.mark.parametrize('flag', ['tools_mill_extracut', 'tools_mill_area_exclusion'])
def test_milling_level_switch_preserves_selected_advanced_machining_flags(qtbot, levels, flag):
    from appPlugins.ToolMilling import ToolMilling
    tool, data = milling_fixture(qtbot)
    data.update(tools_mill_extracut=True, tools_mill_area_exclusion=True, tools_mill_extracut_length=.65)
    observed = []
    for checked in levels:
        ToolMilling.on_level_changed(tool, checked)
        observed.append(data[flag])
    assert observed == [True, True, True]
    assert data['tools_mill_extracut_length'] == .65


@pytest.mark.parametrize('levels', [(False, True, False), (True, False, True)], ids=['basic-first', 'advanced-first'])
@pytest.mark.parametrize('already_blocked', [False, True])
def test_milling_level_is_read_only_for_selected_offset_and_job_settings(qtbot, levels, already_blocked):
    from PyQt6 import QtCore
    from appGUI.GUIElements import FCComboBox2, FCDoubleSpinner
    from appPlugins.ToolMilling import ToolMilling
    base, data = milling_fixture(qtbot)
    class SignalHost(QtCore.QObject):
        def form_to_storage(self, *args):
            self.form_writes.append(self.sender().objectName())
            ToolMilling.form_to_storage(self)
    tool = SignalHost()
    tool.__dict__.update(vars(base))
    tool.form_writes = []
    tool.on_job_changed = lambda index: ToolMilling.on_job_changed(tool, index)
    for name in ('polish_margin_lbl polish_margin_entry polish_over_lbl polish_over_entry '
                 'polish_method_lbl polish_method_combo').split():
        widget = QtWidgets.QWidget()
        widget.show()
        setattr(tool.ui, name, widget)
        qtbot.addWidget(widget)
    tool.ui.cutzlabel = QtWidgets.QLabel()
    qtbot.addWidget(tool.ui.cutzlabel)
    tool.ui.object_combo.currentText = lambda: 'geometry'
    tool.ui.job_type_combo = FCComboBox2()
    tool.ui.job_type_combo.addItems(['Roughing', 'Finishing', 'Isolation', 'Polishing'])
    tool.ui.offset_entry = FCDoubleSpinner()
    tool.ui.offset_entry.set_range(-10, 10)
    tool.ui.offset_entry.set_precision(2)
    for widget in (tool.ui.job_type_combo, tool.ui.offset_entry):
        qtbot.addWidget(widget)
    data.update(tools_mill_offset_type=3, tools_mill_offset_value=.42, tools_mill_job_type=2)
    other_data = dict(data, tools_mill_offset_type=1, tools_mill_offset_value=.7, tools_mill_job_type=1)
    tool.target_obj.tools[2] = {'data': other_data}
    before = deepcopy(tool.target_obj.tools)
    table = tool.ui.tools_table_mill_geo
    table.setColumnCount(5)
    table.setRowCount(1)
    table.setItem(0, 3, QtWidgets.QTableWidgetItem('1'))
    table.selectRow(0)
    tool.form_fields = dict(tools_mill_offset_type=tool.ui.offset_type_combo,
                           tools_mill_offset_value=tool.ui.offset_entry, tools_mill_job_type=tool.ui.job_type_combo)
    tool.general_form_fields = {}
    tool.name2option = {}
    tool.ui_disconnect = tool.ui_connect = lambda: None
    for key, widget in tool.form_fields.items():
        widget.setObjectName(key)
        tool.name2option[key] = key
        if isinstance(widget, FCComboBox2):
            widget.currentIndexChanged.connect(tool.form_to_storage)
            widget.blockSignals(already_blocked)
    tool.ui.offset_type_combo.currentIndexChanged.connect(lambda index: ToolMilling.on_offset_type_changed(tool, index))
    for checked in levels:
        ToolMilling.on_level_changed(tool, checked)
        assert tool.target_obj.tools == before
        if checked:
            assert tool.ui.offset_type_combo.get_value() == 3
            assert tool.ui.offset_entry.get_value() == .42
            assert tool.ui.job_type_combo.get_value() == 2
            assert not tool.ui.offset_entry.isHidden()
            assert tool.ui.polish_margin_entry.isHidden()
        else:
            assert tool.ui.offset_type_combo.isHidden()
            assert tool.ui.offset_entry.isHidden()
        assert tool.ui.offset_type_combo.signalsBlocked() is already_blocked
        assert tool.ui.job_type_combo.signalsBlocked() is already_blocked
    assert tool.form_writes == []
    if not already_blocked:
        tool.ui.offset_type_combo.set_value(1)
        assert data['tools_mill_offset_type'] == 1  # actual editing still writes via the live signal
        assert tool.form_writes == ['tools_mill_offset_type']
