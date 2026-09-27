"""Slot-capable shared creation with the existing defaults and publication guard contract."""
from copy import deepcopy
from pathlib import Path
import os
import subprocess
import sys

import pytest
from shapely import LineString

from mikrocam.bridge.excellon import create_excellon_operations
from mikrocam.core.excellon_tools import ExcellonTool
from test_svg_drill_bridge import Host


class SlotHost(Host):
    def geometry(self, obj):
        result = super().geometry(obj)
        if result == 'fail':
            return result
        for tool in obj.tools.values():
            shapes = [LineString((start, end)).buffer(tool['tooldia'] / 2) for start, end in tool['slots']]
            tool['solid_geometry'].extend(shapes)
            obj.solid_geometry.extend(shapes)


TOOLS = (ExcellonTool(2.54, ((25.4, 50.8),), (((76.2, 25.4), (101.6, 25.4)),)),
         ExcellonTool(5.08, (), (((0., 100.), (25.4, 100.)),)))


@pytest.mark.parametrize('units,header', [('METRIC','C0.00'),('INCH','C0.0000')])
def test_zero_tool_after_export_quantization_prevents_publication(units,header):
    app=SlotHost()
    app.f_handlers.export_excellon=lambda *a,**k:f'M48\n{units}\nT1F00S00{header}\n%\nM30\n'
    with pytest.raises(ValueError,match='precision|zero'):
        create_excellon_operations(app,TOOLS,'too-small')
    assert not app.published and app.initialized.source_file == ''


@pytest.mark.parametrize(('units', 'factor'), [('MM', 1.), ('IN', 1 / 25.4)])
def test_drills_and_slot_only_tools_convert_once_with_preserved_defaults(units, factor):
    app = SlotHost(units)
    defaults, options = deepcopy(app.defaults), deepcopy(app.options)
    obj = create_excellon_operations(app, TOOLS, 'mixed')
    assert app.published == [obj]
    assert obj.tools[1]['tooldia'] == pytest.approx(2.54 * factor)
    assert obj.tools[1]['drills'][0].coords[0] == pytest.approx((25.4 * factor, 50.8 * factor))
    start, end = obj.tools[1]['slots'][0]
    assert start.coords[0] == pytest.approx((76.2 * factor, 25.4 * factor))
    assert end.coords[0] == pytest.approx((101.6 * factor, 25.4 * factor))
    assert obj.tools[2]['drills'] == [] and len(obj.tools[2]['slots']) == 1
    assert len(obj.solid_geometry) == 3
    assert all(tool['data'] == defaults for tool in obj.tools.values())
    assert app.defaults == defaults and app.options == options
    assert obj.source_file.startswith('M48')


@pytest.mark.parametrize('reject_at', [None, 1, 2])
def test_both_guard_checkpoints_cover_slot_creation(reject_at):
    app = SlotHost()
    calls = []
    def guard():
        calls.append(True)
        assert not app.published and app.initialized.source_file == ''
        if len(calls) == 1:
            assert app.initialized.tools == {'old': {}}
        else:
            assert app.initialized.tools[1]['slots'] and app.calls[-1] == ('export', 'MM')
        if len(calls) == reject_at:
            raise ValueError('Source changed; analyse again')
    if reject_at is None:
        create_excellon_operations(app, TOOLS, 'guarded', source_guard=guard)
        assert len(calls) == 2
    else:
        with pytest.raises(ValueError, match='Source changed'):
            create_excellon_operations(app, TOOLS, 'guarded', source_guard=guard)
        assert not app.published


@pytest.mark.parametrize('failure', ['factory', 'units', 'geometry', 'geometry-exception',
                                     'export', 'empty-export', 'none-export', 'export-exception'])
def test_slot_factory_errors_do_not_publish(failure):
    app = SlotHost(failure=failure)
    with pytest.raises(ValueError):
        create_excellon_operations(app, TOOLS, 'failed')
    assert not app.published


def test_capsule_conflict_rejected_before_factory():
    app = SlotHost()
    tools = (ExcellonTool(1, ((5, 0),), (((0, 0), (10, 0)),)),)
    with pytest.raises(ValueError, match='overlap'):
        create_excellon_operations(app, tools, 'bad')
    assert not app.calls


def test_created_slot_lists_and_points_are_independently_owned():
    app = SlotHost()
    first = create_excellon_operations(app, TOOLS, 'first')
    second = create_excellon_operations(app, TOOLS, 'second')
    first.tools[1]['slots'].clear()
    assert len(second.tools[1]['slots']) == len(TOOLS[0].slots_mm) == 1


@pytest.mark.parametrize('units', ['MM', 'IN'])
@pytest.mark.parametrize('slot_type', ['routing', 'drilling'])
def test_actual_excellon_mixed_and_slot_only_export_reparse(tmp_path, units, slot_type):
    script = '''
import copy, logging, sys
from types import SimpleNamespace
from qt_settings_sandbox import install_settings_sandbox
install_settings_sandbox(sys.argv[1])
from defaults import AppDefaults
from appObjects.ExcellonObject import ExcellonObject
from appParsers.ParseExcellon import Excellon
from appHandlers.appIO import appIO
from mikrocam.bridge.excellon import create_excellon_operations
from mikrocam.core.excellon_tools import ExcellonTool
options = copy.deepcopy(AppDefaults.factory_defaults)
options.update(units=sys.argv[2], excellon_exp_units='METRIC', excellon_exp_format='dec',
               excellon_exp_slot_type=sys.argv[3])
class Defaults(dict):
    factory_defaults = AppDefaults.factory_defaults
signal = SimpleNamespace(emit=lambda *a: None)
app = SimpleNamespace(options=options, defaults=Defaults(options), app_units=sys.argv[2], decimals=4,
                      log=logging.getLogger('test'), abort_flag=False, inform=signal,
                      version='test', version_date='test', use_3d_engine=True,
                      plotcanvas=SimpleNamespace(new_shape_collection=lambda **kw: None),
                      proc_container=SimpleNamespace(update_view_text=lambda *a: None, new_text=''))
before = copy.deepcopy(options)
published = []
def factory(kind, name, initialize):
    obj = ExcellonObject.__new__(ExcellonObject)
    Excellon.__init__(obj, app, excellon_circle_steps=32)
    obj.default_data = {'feedrate': 123}
    if initialize(obj, app) == 'fail': return 'fail'
    published.append(obj)
    return obj
app.app_obj = SimpleNamespace(new_object=factory)
handler = SimpleNamespace(app=app, app_units=app.app_units, log=app.log, inform=signal)
app.f_handlers = SimpleNamespace(export_excellon=lambda *a, **kw: appIO.export_excellon(handler, *a, **kw))
tools = (ExcellonTool(2.54, ((25.4, 50.8),), (((76.2, 25.4), (101.6, 25.4)),)),
         ExcellonTool(5.08, (), (((0., 100.), (25.4, 100.)),)))
obj = create_excellon_operations(app, tools, 'mixed-slots')
assert published == [obj] and options == before
assert all(t['data'] == {'feedrate':123} for t in obj.tools.values())
assert len(obj.solid_geometry) == 3
parsed = Excellon(app, excellon_circle_steps=32)
parsed.default_data = {}
assert parsed.parse_file(file_obj=obj.source_file.splitlines()) != 'fail'
assert parsed.units == 'MM' and len(parsed.tools) == 2
assert len(parsed.tools[1]['drills']) == 1 and len(parsed.tools[1]['slots']) == 1
assert parsed.tools[2]['drills'] == [] and len(parsed.tools[2]['slots']) == 1
for tool_id, diameter, endpoints in [(1,2.54,((76.2,25.4),(101.6,25.4))),
                                    (2,5.08,((0.,100.),(25.4,100.)))]:
    assert abs(parsed.tools[tool_id]['tooldia']-diameter) < 1e-6
    for actual, wanted in zip(parsed.tools[tool_id]['slots'][0], endpoints):
        assert abs(actual.x-wanted[0]) < 1e-6 and abs(actual.y-wanted[1]) < 1e-6
assert parsed.create_geometry() != 'fail' and len(parsed.solid_geometry) == 3
'''
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path), units, slot_type],
                            cwd=Path(__file__).parents[1], capture_output=True, text=True,
                            timeout=60, env=os.environ | {'PYTHONPATH': 'tests;.'})
    assert result.returncode == 0, result.stdout + result.stderr
