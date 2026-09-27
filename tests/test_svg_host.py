"""Actual legacy SVG import seam preserves physical scale and failure atomicity."""
from copy import deepcopy
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from shapely import union_all
from shapely.geometry import box

from camlib import Geometry
from appParsers.ParseGerber import Gerber
from defaults import AppDefaults
from mikrocam.ui.svg_import import import_svg_geometry


FIXTURE = Path(__file__).parent / 'reference/svg-physical-transform.svg'


def host(kind='geometry', units='MM'):
    messages, logs = [], []
    options = deepcopy(AppDefaults.factory_defaults)
    options['tools_mill_tooldia'] = .87654
    app = SimpleNamespace(app_units=units, decimals=4, options=options, defaults=options,
                          use_3d_engine=True, plotcanvas=SimpleNamespace(new_shape_collection=lambda **kw: None),
                          log=SimpleNamespace(debug=logs.append, info=logs.append, warning=logs.append, error=logs.append),
                          inform=SimpleNamespace(emit=messages.append))
    value = Geometry(app, geo_steps_per_circle=64) if kind == 'geometry' else Gerber(app)
    # AppObject.new_object assigns application units before the import initializer.
    value.units = units
    value.obj_options = dict(name='svg-test', explicit_setting=123)
    value.source_file = 'unchanged existing source'
    return value, messages, logs


@pytest.mark.parametrize('kind', ['geometry', 'gerber'])
@pytest.mark.parametrize('units', ['MM', 'IN'])
@pytest.mark.parametrize('flip', [False, True])
def test_actual_host_physical_bounds_units_and_tool_population(kind, units, flip):
    value, _, _ = host(kind, units)
    before = FIXTURE.read_bytes()
    assert value.import_svg(str(FIXTURE), kind, flip=flip, units=units) is None
    material = union_all(value.solid_geometry)
    expected = (10., 30., 30., 40.) if flip else (10., 10., 30., 20.)
    scale = 1. if units == 'MM' else 1 / 25.4
    assert material.bounds == pytest.approx(tuple(item * scale for item in expected))
    assert material.area == pytest.approx(200 * scale ** 2)
    assert all(not item.is_empty for item in value.solid_geometry)
    assert value.units == units
    assert value.source_file == 'unchanged existing source'
    assert FIXTURE.read_bytes() == before
    if kind == 'geometry':
        assert value.tools[1]['tooldia'] == .8765
        assert value.tools[1]['data'] == value.obj_options
        assert value.tools[1]['solid_geometry'] is value.solid_geometry
    else:
        assert value.tools[0]['type'] == 'REG'
        assert union_all([item['solid'] for item in value.tools[0]['geometry']]).equals(material)


def test_success_appends_material_without_changing_existing_tools():
    value, _, _ = host()
    old = box(-2, -2, -1, -1)
    value.solid_geometry = [old]
    value.tools[9] = {'data': {'explicit': 'unchanged'}}
    value.import_svg(str(FIXTURE), 'geometry', flip=False)
    assert value.solid_geometry[0] is old
    assert value.tools[9] == {'data': {'explicit': 'unchanged'}}
    assert union_all(value.solid_geometry).area == pytest.approx(201.)


@pytest.mark.parametrize('source', ['<svg',
    '<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm"><text>x</text></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm"><rect width="3" height="2"/><rect width="-1" height="4"/></svg>',
    '<!DOCTYPE svg><svg width="10mm" height="10mm"/>',
    '<svg width="10mm" height="10mm"><rect width="3" height="2"/>'
    '<rect width="2" height="2" clip-path="url(#absent)"/></svg>',
    '<svg width="10mm" height="10mm"><defs><clipPath id="c"/></defs>'
    '<rect width="2" height="2" clip-path="url(#c)"/></svg>',
    '<svg width="10mm" height="10mm"><defs><clipPath id="c">'
    + '<rect width="1" height="1"/>' * 65 + '</clipPath></defs>'
    '<rect width="2" height="2" clip-path="url(#c)"/></svg>'])
@pytest.mark.parametrize('kind', ['geometry', 'gerber'])
def test_bad_source_returns_fail_without_partial_geometry_or_tool_mutation(tmp_path, source, kind):
    target = tmp_path / 'bad.svg'
    target.write_text(source, encoding='utf-8')
    value, messages, logs = host(kind)
    original_geometry = [box(-2, -2, -1, -1)]
    value.solid_geometry = original_geometry
    original_tools = {9: {'data': {'explicit': 321}}}
    value.tools = original_tools
    assert value.import_svg(str(target), kind) == 'fail'
    assert value.solid_geometry is original_geometry
    assert value.tools is original_tools and value.tools == {9: {'data': {'explicit': 321}}}
    assert value.source_file == 'unchanged existing source'
    assert messages and any('[ERROR_NOTCL]' in message for message in messages)
    assert logs


@pytest.mark.parametrize('units', ['unknown', ''])
def test_invalid_host_units_and_missing_file_are_useful_failures(units, tmp_path):
    value, messages, _ = host()
    assert import_svg_geometry(str(FIXTURE), 'geometry', units, True, value.app) is None
    assert import_svg_geometry(str(tmp_path / 'missing.svg'), 'geometry', 'MM', True, value.app) is None
    assert len(messages) == 2 and all('[ERROR_NOTCL]' in text for text in messages)


def test_open_centreline_geometry_retained_but_gerber_empty_rejected(tmp_path):
    path = tmp_path / 'line.svg'
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm">'
                    '<line x1="0" y1="0" x2="10" y2="0" fill="none"/></svg>', encoding='utf-8')
    value, messages, _ = host()
    assert value.import_svg(str(path), 'geometry', flip=False) is None
    assert union_all(value.solid_geometry).geom_type == 'LineString'
    assert messages and any('centreline' in message.lower() for message in messages)
    gerber, _, _ = host('gerber')
    before_geometry = gerber.solid_geometry
    assert gerber.import_svg(str(path), 'gerber') == 'fail'
    assert gerber.solid_geometry is before_geometry and not gerber.tools


def test_gerber_hole_remains_void_and_existing_aperture_is_preserved(tmp_path):
    target = tmp_path / 'hole.svg'
    target.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm" viewBox="0 0 10 10">'
                      '<path fill-rule="evenodd" d="M0 0H10V10H0Z M2 2H8V8H2Z"/></svg>', encoding='utf-8')
    gerber, _, _ = host('gerber')
    existing = {'type': 'C', 'size': .25, 'geometry': []}
    gerber.tools[7] = existing
    assert gerber.import_svg(str(target), 'gerber', flip=False) is None
    assert gerber.tools[7] is existing
    assert union_all(gerber.solid_geometry).area == pytest.approx(64.)
    assert len(gerber.solid_geometry[0].interiors) == 1
    assert gerber.tools[0]['geometry'][0]['follow'].equals(gerber.solid_geometry[0].exterior)


@pytest.mark.parametrize('bom', [False, True])
@pytest.mark.parametrize('newline', ['\n', '\r\n'])
def test_actual_file_handler_preserves_utf8_text_and_bom(tmp_path, bom, newline, monkeypatch):
    from appHandlers.appIO import appIO
    target = tmp_path / 'utf8.svg'
    text = ('\ufeff' if bom else '') + FIXTURE.read_text(encoding='utf-8').replace(
        'Authored MikroCAM', 'MikroCAM Türkçe ışık ölçüsü')
    text = text.replace('\n', newline)
    target.write_bytes(text.encode('utf-8'))
    value, _, _ = host()
    # Isolate the actual file-handler reader; geometry parsing is covered above.
    monkeypatch.setattr(value, 'import_svg', lambda *args, **kwargs: None)
    published = []

    def new_object(kind, name, initializer, **kwargs):
        assert kind == 'geometry'
        result = initializer(value, value.app)
        if result != 'fail':
            published.append(value)
        return result

    value.app.proc_container = SimpleNamespace(new=lambda message: nullcontext())
    value.app.app_obj = SimpleNamespace(new_object=new_object)
    value.app.file_opened = SimpleNamespace(emit=lambda *args: None)
    handler = SimpleNamespace(app=value.app, log=value.app.log, inform=value.app.inform, app_units='MM')
    assert appIO.import_svg(handler, str(target)) is None
    assert published == [value]
    assert value.source_file == text
    assert target.read_bytes() == text.encode('utf-8')
