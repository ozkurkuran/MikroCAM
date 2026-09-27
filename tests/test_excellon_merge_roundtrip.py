"""Mixed current MM/IN inventories retain actual parsed drills and G85 slots."""
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
from defaults import AppDefaults
from appObjects.ExcellonObject import ExcellonObject
from appParsers.ParseExcellon import Excellon
from appHandlers.appIO import appIO
from mikrocam.bridge.excellon_merge import load_excellon_merge, create_excellon_merge
units, export_units = sys.argv[2:4]
options = copy.deepcopy(AppDefaults.factory_defaults)
options.update(units=units, excellon_exp_units=export_units, excellon_exp_format='dec',
               excellon_exp_decimals=6, tools_mill_feedrate=321.25)
class Defaults(dict):
    factory_defaults = AppDefaults.factory_defaults
signal = SimpleNamespace(emit=lambda *a: None)
app = SimpleNamespace(options=options, defaults=Defaults(options), app_units=units, decimals=4,
    log=logging.getLogger('roundtrip'), abort_flag=False, inform=signal, version='test',
    version_date='test', use_3d_engine=True,
    plotcanvas=SimpleNamespace(new_shape_collection=lambda **kw: None),
    proc_container=SimpleNamespace(update_view_text=lambda *a: None, new_text=''))
texts = ('M48\nMETRIC,LZ\nT01C2.54\nT02C2.54\n%\nT01\nX25.4Y50.8\nT02\nX25.4Y101.6G85X50.8Y101.6\nM30\n',
         'M48\nINCH,LZ\nT01C0.1\nT02C0.1\nT03C0.2\n%\nT01\nX1.0Y2.0\nT02\nX2.0Y4.0G85X1.0Y4.0\nT03\nX8.0Y2.0\nM30\n')
sources = []
for index,text in enumerate(texts):
    parser = Excellon(app, excellon_circle_steps=32)
    parser.default_data = {'source feedrate':index+7}
    assert parser.parse_file(file_obj=text.splitlines()) != 'fail'
    parsed_tools = copy.deepcopy(parser.tools)
    # Exercise the admitted sparse host representation without removing any operations.
    assert not parsed_tools[2]['drills'] and not parsed_tools[1]['slots']
    parsed_tools[2].pop('drills')
    parsed_tools[1].pop('slots')
    assert parser.create_geometry() != 'fail'
    sources.append(SimpleNamespace(kind='excellon', obj_options={'name':f'source{index}'},
        units=parser.units, tools=parsed_tools, solid_geometry=parser.solid_geometry,
        source_file=text, default_data=copy.deepcopy(parser.default_data)))
owners = tuple(sources)
original = tuple(copy.deepcopy(obj.__dict__) for obj in owners)
original_options = copy.deepcopy(options)
app.collection = SimpleNamespace(get_by_name=lambda name: next((obj for obj in owners if obj.obj_options['name']==name),None))
published = []
def factory(kind, name, initialize, **kwargs):
    assert kind == 'excellon'
    obj = ExcellonObject.__new__(ExcellonObject)
    Excellon.__init__(obj, app, excellon_circle_steps=32)
    obj.default_data = {'feedrate':321.25,'nested':{'preserved':True}}
    if initialize(obj, app) == 'fail':
        return 'fail'
    published.append(obj)
    return obj
app.app_obj = SimpleNamespace(new_object=factory)
handler = SimpleNamespace(app=app, app_units=units, log=app.log, inform=signal)
app.f_handlers = SimpleNamespace(export_excellon=lambda *a, **kw: appIO.export_excellon(handler,*a,**kw))
review = load_excellon_merge(owners)
assert not review.conflict_count and len(review.duplicates)==2 and len(review.tool_map)==5
assert len(review.tools)==2 and len(review.tools[0].slots_mm)==1
obj = create_excellon_merge(app,owners,review,'merged holes and slots')
assert published==[obj] and obj.units==units
assert all(tool['data']==obj.default_data and tool['data'] is not obj.default_data for tool in obj.tools.values())
assert tuple(source.__dict__ for source in owners)==original and options==original_options
assert load_excellon_merge(owners)==review
parsed = Excellon(app,excellon_circle_steps=32)
parsed.default_data = {}
assert parsed.parse_file(file_obj=obj.source_file.splitlines()) != 'fail'
assert parsed.create_geometry() != 'fail'
factor = 1 if parsed.units=='MM' else 25.4
# Six-decimal inch coordinate quantum plus legacy 0.03937 conversion error over this board.
tolerance = 1e-6 if export_units=='METRIC' else 25.4e-6 + 203.2 * 2e-6
tools = sorted(parsed.tools.values(),key=lambda t:t['tooldia'])
for tool,diameter,center in zip(tools,(2.54,5.08),((25.4,50.8),(203.2,50.8))):
    assert abs(tool['tooldia']*factor-diameter)<tolerance
    point = tool['drills'][0]
    assert abs(point.x*factor-center[0])<tolerance and abs(point.y*factor-center[1])<tolerance
slot = tools[0]['slots'][0]
for point,expected in zip(slot,((25.4,101.6),(50.8,101.6))):
    assert abs(point.x*factor-expected[0])<tolerance and abs(point.y*factor-expected[1])<tolerance
assert sum(len(t.get('drills',()))+len(t.get('slots',())) for t in tools)==3
assert tuple(source.__dict__ for source in owners)==original and options==original_options
'''


@pytest.mark.parametrize('units', ['MM', 'IN'])
@pytest.mark.parametrize('export_units', ['METRIC', 'INCH'])
def test_actual_mixed_sources_export_reparse_slots_without_source_mutation(tmp_path, units, export_units):
    result = subprocess.run([sys.executable, '-c', SCRIPT, str(tmp_path), units, export_units],
                            cwd=Path(__file__).parents[1], capture_output=True, text=True,
                            timeout=60, env=os.environ | {'PYTHONPATH': 'tests;.'})
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('export_units', ['METRIC', 'INCH'])
def test_actual_export_zero_diameter_is_rejected_before_publication(tmp_path, export_units):
    script=SCRIPT.split('review = load_excellon_merge(owners)')[0]+r'''
from mikrocam.bridge.excellon import create_excellon_operations
from mikrocam.core.excellon_tools import ExcellonTool
diameter=.004 if export_units=='METRIC' else .0004
try:
    create_excellon_operations(app,(ExcellonTool(diameter,((0.,0.),),()),),'unrepresentable')
except ValueError as error:
    assert 'precision' in str(error) and 'zero' in str(error)
else:
    raise AssertionError('Zero exported diameter must not be published')
assert not published and tuple(source.__dict__ for source in owners)==original
'''
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path),'MM',export_units],
                          cwd=Path(__file__).parents[1],capture_output=True,text=True,
                          timeout=60,env=os.environ|{'PYTHONPATH':'tests;.'})
    assert result.returncode == 0,result.stdout+result.stderr
