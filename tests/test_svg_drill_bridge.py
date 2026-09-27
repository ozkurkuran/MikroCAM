from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from mikrocam.bridge.svg_drills import create_drill_object, load_drill_review, verify_drill_source
from mikrocam.core.svg_drills import DrillCandidate, DrillReview


def review():
    return DrillReview('original.svg', 'a' * 64, False,
                       (DrillCandidate((25.4, 50.8), 2.54, 'o1', 'p1'),
                        DrillCandidate((76.2, 25.4), 5.08, 'o2', 'p2')), ())


class Host:
    def __init__(self, units='MM', failure=None):
        self.app_units = units
        self.failure = failure
        self.published = []
        self.calls = []
        self.defaults = {'feedrate': 123, 'nested': {'x': 1}}
        self.options = {'units': units, 'unrelated': 42}
        self.app_obj = SimpleNamespace(new_object=self.new_object)
        self.f_handlers = SimpleNamespace(export_excellon=self.export)

    def new_object(self, kind, name, initialize, **kwargs):
        self.calls.append(('factory', kind, name))
        if self.failure == 'factory':
            return 'fail'
        obj = SimpleNamespace(units=self.app_units, tools={'old': {}}, source_file='',
                              default_data=deepcopy(self.defaults), solid_geometry=[])
        if self.failure == 'units':
            obj.units = 'IN' if self.app_units == 'MM' else 'MM'
        obj.create_geometry = lambda: self.geometry(obj)
        self.initialized = obj
        if initialize(obj, self) == 'fail':
            return 'fail'
        self.published.append(obj)
        return obj

    def geometry(self, obj):
        self.calls.append(('geometry', obj.units))
        if self.failure == 'geometry':
            return 'fail'
        if self.failure == 'geometry-exception':
            raise RuntimeError('buffer failed')
        obj.solid_geometry = []
        for tool in obj.tools.values():
            tool['solid_geometry'] = [point.buffer(tool['tooldia'] / 2) for point in tool['drills']]
            tool['data'] = deepcopy(obj.default_data)
            obj.solid_geometry.extend(tool['solid_geometry'])

    def export(self, name, filename, *, local_use, use_thread):
        assert filename is None and use_thread is False
        assert local_use is self.initialized and local_use.solid_geometry
        self.calls.append(('export', local_use.units))
        if self.failure == 'export-exception':
            raise RuntimeError('export failed')
        return {'export': 'fail', 'empty-export': '', 'none-export': None}.get(
            self.failure, 'M48\nMETRIC\n%\nM30\n')


@pytest.mark.parametrize('units,factor', [('MM', 1), ('IN', 1 / 25.4)])
def test_fresh_complete_object_converts_once_before_geometry_and_export(units, factor):
    app = Host(units)
    data = review()
    original = data.candidates
    defaults = deepcopy(app.defaults)
    options = deepcopy(app.options)
    obj = create_drill_object(app, data, (1, 0), 'holes')
    assert app.published == [obj] and obj.units == units
    assert tuple(obj.tools) == (1, 2)
    assert obj.tools[1]['tooldia'] == pytest.approx(2.54 * factor)
    assert obj.tools[1]['drills'][0].coords[0] == pytest.approx((25.4 * factor, 50.8 * factor))
    assert obj.tools[2]['tooldia'] == pytest.approx(5.08 * factor)
    assert all(tool['slots'] == [] and tool['solid_geometry'] for tool in obj.tools.values())
    assert all(tool['data'] == defaults and tool['data'] is not obj.default_data
               for tool in obj.tools.values())
    assert obj.source_file.startswith('M48')
    assert app.calls == [('factory', 'excellon', 'holes'), ('geometry', units), ('export', units)]
    assert data.candidates is original and app.defaults == defaults and app.options == options


@pytest.mark.parametrize('name', ['', ' ', ' holes', 'holes ', 'x' * 257, 'a\nb', 'a\x00b', 1])
def test_name_validation_precedes_factory(name):
    app = Host()
    with pytest.raises(ValueError):
        create_drill_object(app, review(), (0,), name)
    assert not app.calls and not app.published


@pytest.mark.parametrize('indices', [(), [], (True,), (-1,), (2,), (0, 0)])
def test_selection_validation_precedes_factory(indices):
    app = Host()
    with pytest.raises(ValueError):
        create_drill_object(app, review(), indices, 'holes')
    assert not app.calls and not app.published


@pytest.mark.parametrize('failure', ['factory', 'units', 'geometry', 'geometry-exception',
                                     'export', 'empty-export', 'none-export', 'export-exception'])
def test_failed_initialization_never_publishes(failure):
    app = Host(failure=failure)
    with pytest.raises(ValueError):
        create_drill_object(app, review(), (0,), 'holes')
    assert not app.published


@pytest.mark.parametrize('units', [None, 'CM', 'mm'])
def test_unknown_host_units_are_never_guessed(units):
    app = Host(units)
    with pytest.raises(ValueError):
        create_drill_object(app, review(), (0,), 'holes')
    assert not app.calls


def test_two_creations_have_independently_owned_lists_and_geometry():
    app = Host()
    first = create_drill_object(app, review(), (0,), 'first')
    second = create_drill_object(app, review(), (0,), 'second')
    first.tools[1]['drills'].clear()
    first.tools[1]['slots'].append('changed')
    assert len(second.tools[1]['drills']) == 1 and second.tools[1]['slots'] == []


def test_load_uses_physical_importer_and_requested_flip_without_changing_file(tmp_path):
    source = (b'<svg width="10mm" height="10mm" viewBox="0 0 10 10">'
              b'<circle cx="4" cy="3" r="2" fill="black"/>'
              b'<circle cx="4" cy="3" r=".5" fill="white"/></svg>')
    path = tmp_path / 'drills.svg'
    path.write_bytes(source)
    normal = load_drill_review(path, flip=False)
    flipped = load_drill_review(path, flip=True)
    assert normal.candidates[0].center_mm == pytest.approx((4, 3))
    assert flipped.candidates[0].center_mm == pytest.approx((4, 7))
    assert normal.candidates[0].diameter_mm == pytest.approx(1)
    assert normal.source_sha256 == flipped.source_sha256
    assert normal.flipped is False and flipped.flipped is True
    assert path.read_bytes() == source


def test_load_propagates_missing_and_invalid_sources(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_drill_review(tmp_path / 'missing.svg')
    path = tmp_path / 'bad.svg'
    path.write_bytes(b'not SVG')
    with pytest.raises(ValueError):
        load_drill_review(path)


def test_source_verification_is_exact_and_never_reparses(tmp_path):
    import hashlib
    from dataclasses import replace
    source = b'original bytes need not be reparsed during verification'
    path = tmp_path / 'source.svg'
    path.write_bytes(source)
    data = replace(review(), source_sha256=hashlib.sha256(source).hexdigest())
    assert verify_drill_source(path, data) is None
    path.write_bytes(source + b'changed')
    with pytest.raises(ValueError, match='changed'):
        verify_drill_source(path, data)


def test_source_verification_missing_and_bounded_oversize(tmp_path, monkeypatch):
    from mikrocam.bridge import svg_drills as module
    path = tmp_path / 'source.svg'
    with pytest.raises(FileNotFoundError):
        verify_drill_source(path, review())
    path.write_bytes(b'12345')
    monkeypatch.setattr(module, 'MAX_SVG_BYTES', 4)
    with pytest.raises(ValueError, match='size'):
        verify_drill_source(path, review())


def test_source_verification_requires_a_review_before_file_access(tmp_path):
    with pytest.raises(ValueError):
        verify_drill_source(tmp_path / 'missing', None)


@pytest.mark.parametrize('units', ['MM', 'IN'])
def test_real_excellon_geometry_local_export_and_reparse(tmp_path, units):
    script = '''
import copy, logging, sys
from types import SimpleNamespace
from qt_settings_sandbox import install_settings_sandbox
install_settings_sandbox(sys.argv[1])
from defaults import AppDefaults
from appObjects.ExcellonObject import ExcellonObject
from appParsers.ParseExcellon import Excellon
from appHandlers.appIO import appIO
from mikrocam.bridge.svg_drills import create_drill_object
from mikrocam.core.svg_drills import DrillCandidate, DrillReview
options = copy.deepcopy(AppDefaults.factory_defaults)
options.update(units=sys.argv[2], excellon_exp_units='METRIC', excellon_exp_format='dec')
class Defaults(dict):
    factory_defaults = AppDefaults.factory_defaults
signal = SimpleNamespace(emit=lambda *a: None)
app = SimpleNamespace(options=options, defaults=Defaults(options), app_units=sys.argv[2], decimals=4,
                      log=logging.getLogger('test'), abort_flag=False, inform=signal,
                      version='test', version_date='test', use_3d_engine=True,
                      plotcanvas=SimpleNamespace(new_shape_collection=lambda **kw: None),
                      proc_container=SimpleNamespace(update_view_text=lambda *a: None, new_text=''))
published = []
def factory(kind, name, initialize, **kwargs):
    obj = ExcellonObject.__new__(ExcellonObject)
    Excellon.__init__(obj, app, excellon_circle_steps=32)
    obj.default_data = {'feedrate': 123}
    if initialize(obj, app) == 'fail': return 'fail'
    published.append(obj)
    return obj
app.app_obj = SimpleNamespace(new_object=factory)
handler = SimpleNamespace(app=app, app_units=app.app_units, log=app.log, inform=signal)
app.f_handlers = SimpleNamespace(export_excellon=lambda *a, **kw: appIO.export_excellon(handler, *a, **kw))
review = DrillReview('original.svg', 'a'*64, False,
                    (DrillCandidate((25.4,50.8),2.54,'o','p'),), ())
obj = create_drill_object(app, review, (0,), 'holes')
assert published == [obj] and obj.tools[1]['data'] == {'feedrate':123}
assert len(obj.solid_geometry) == 1
parsed = Excellon(app, excellon_circle_steps=32)
parsed.default_data = {}
assert parsed.parse_file(file_obj=obj.source_file.splitlines()) != 'fail'
assert parsed.units == 'MM'
assert abs(parsed.tools[1]['tooldia']-2.54) < 1e-6
point = parsed.tools[1]['drills'][0]
assert abs(point.x-25.4) < 1e-6 and abs(point.y-50.8) < 1e-6
assert parsed.create_geometry() != 'fail'
'''
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path), units],
                            cwd=Path(__file__).parents[1], capture_output=True, text=True,
                            timeout=60, env=__import__('os').environ | {'PYTHONPATH': 'tests;.'})
    assert result.returncode == 0, result.stdout + result.stderr
