"""Actual Excellon exporter/parser preserves reviewed current Geometry in MM and IN."""
import os
from pathlib import Path
import subprocess
import sys
import pytest

SCRIPT = r'''
import copy, logging, sys
from types import SimpleNamespace
from qt_settings_sandbox import install_settings_sandbox
install_settings_sandbox(sys.argv[1])
from shapely.geometry import Point
from shapely.affinity import scale
from defaults import AppDefaults
from appObjects.ExcellonObject import ExcellonObject
from appParsers.ParseExcellon import Excellon
from appHandlers.appIO import appIO
from mikrocam.bridge.geometry_drills import load_geometry_review, create_geometry_drills
units, multi = sys.argv[2], sys.argv[3] == 'multi'
options = copy.deepcopy(AppDefaults.factory_defaults)
options.update(units=units, excellon_exp_units='METRIC', excellon_exp_format='dec',
               tools_mill_feedrate=321.25)
class Defaults(dict):
    factory_defaults = AppDefaults.factory_defaults
signal = SimpleNamespace(emit=lambda *a: None)
app = SimpleNamespace(options=options, defaults=Defaults(options), app_units=units, decimals=4,
    log=logging.getLogger('roundtrip'), abort_flag=False, inform=signal, version='test',
    version_date='test', use_3d_engine=True,
    plotcanvas=SimpleNamespace(new_shape_collection=lambda **kw: None),
    proc_container=SimpleNamespace(update_view_text=lambda *a: None, new_text=''))
factor = 1 if units == 'MM' else 1 / 25.4
circles = [scale(Point(x, y).buffer(d / 2, quad_segs=32), xfact=factor, yfact=factor, origin=(0, 0))
           for x, y, d in [(25.4, 50.8, 2.54), (76.2, 25.4, 5.08)]]
source = SimpleNamespace(kind='geometry', obj_options={'name':'current geometry'}, units=units,
    multigeo=multi, solid_geometry=circles, tools={1:{'solid_geometry':[circles[0]], 'data':{'feedrate':7}},
    'second':{'solid_geometry':[circles[1]], 'data':{'feedrate':9}}}, source_file='unchanged source text')
if multi:
    source.solid_geometry = [Point(999, 999).buffer(5)]
original = copy.deepcopy(source.__dict__)
original_options = copy.deepcopy(options)
app.collection = SimpleNamespace(get_by_name=lambda name: source if name == 'current geometry' else None)
published = []
def factory(kind, name, initialize, **kwargs):
    assert kind == 'excellon'
    obj = ExcellonObject.__new__(ExcellonObject)
    Excellon.__init__(obj, app, excellon_circle_steps=32)
    obj.default_data = {'feedrate':321.25, 'nested':{'preserved':True}}
    if initialize(obj, app) == 'fail':
        return 'fail'
    published.append(obj)
    return obj
app.app_obj = SimpleNamespace(new_object=factory)
handler = SimpleNamespace(app=app, app_units=units, log=app.log, inform=signal)
app.f_handlers = SimpleNamespace(export_excellon=lambda *a, **kw: appIO.export_excellon(handler, *a, **kw))
review = load_geometry_review(source)
assert len(review.candidates) == 2
obj = create_geometry_drills(app, source, review, (1, 0), 'reviewed holes')
assert published == [obj] and obj.units == units
assert all(tool['data'] == obj.default_data and tool['data'] is not obj.default_data for tool in obj.tools.values())
assert source.__dict__ == original and options == original_options
assert load_geometry_review(source) == review
parsed = Excellon(app, excellon_circle_steps=32)
parsed.default_data = {}
assert parsed.parse_file(file_obj=obj.source_file.splitlines()) != 'fail'
assert parsed.units == 'MM'
assert parsed.create_geometry() != 'fail'
assert len(parsed.solid_geometry) == 2
for tool, expected in zip(sorted(parsed.tools.values(), key=lambda t:t['tooldia']),
                          [(2.54,25.4,50.8),(5.08,76.2,25.4)]):
    diameter,x,y = expected
    assert abs(tool['tooldia']-diameter) < 1e-6
    assert len(tool['drills']) == 1 and not tool['slots']
    point = tool['drills'][0]
    assert abs(point.x-x) < 1e-6 and abs(point.y-y) < 1e-6
assert source.__dict__ == original
'''


@pytest.mark.parametrize('units', ['MM', 'IN'])
@pytest.mark.parametrize('mode', ['single', 'multi'])
def test_actual_geometry_review_export_reparse_preserves_source(tmp_path, units, mode):
    result = subprocess.run([sys.executable, '-c', SCRIPT, str(tmp_path), units, mode],
                            cwd=Path(__file__).parents[1], capture_output=True, text=True,
                            timeout=60, env=os.environ | {'PYTHONPATH': 'tests;.'})
    assert result.returncode == 0, result.stdout + result.stderr
