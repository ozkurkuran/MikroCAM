"""Actual host import/serialization preserves metadata independently of CAM behavior."""
from contextlib import nullcontext
from copy import deepcopy
from hashlib import sha256
import io
import json
from types import SimpleNamespace

import pytest
from shapely import union_all

from test_import_report_persistence import object_factory
from mikrocam.bridge.cad_source import read_cad_source


def source_bytes(source_format, marker=True):
    if source_format == 'SVG':
        comment = '<!-- Generator: Adobe Illustrator 29.0 -->\r\n' if marker else ''
        source = ('<svg width="10mm" height="20mm" viewBox="0 0 10 20">\r\n'
                  + comment + '<rect x="2" y="3" width="4" height="2"/>\r\n</svg>\r\n')
    else:
        import ezdxf
        document = ezdxf.new('R2010')
        document.units = 4
        document.modelspace().add_lwpolyline([(2, 3), (6, 3), (6, 5), (2, 5)], close=True)
        output = io.StringIO()
        document.write(output)
        source = output.getvalue().replace('\n', '\r\n')
        if marker:
            source = source.replace('  0\r\nEOF', '999\r\nGenerator: Proteus 8.6\r\n  0\r\nEOF')
    return b'\xef\xbb\xbf' + source.encode('utf-8')


def import_host(create, path, source_format):
    from appHandlers.appIO import appIO
    objects = []
    sample = create()
    app = sample.app
    app.options.update(tools_mill_feedrate=321.25, tools_mill_cutz=-0.321)
    before = deepcopy(app.options)
    signal = SimpleNamespace(emit=lambda *args: None)
    app.inform = signal
    app.file_opened = signal
    app.abort_flag = False
    app.proc_container = SimpleNamespace(new=lambda *args: nullcontext())

    def factory(kind, name, initialize, **kwargs):
        obj = create()
        obj.units = app.app_units
        obj.obj_options['name'] = name
        for key, value in app.options.items():
            if key.startswith(kind + '_'):
                obj.obj_options[key[len(kind) + 1:]] = deepcopy(value)
            elif key.startswith('tools_'):
                obj.obj_options[key] = deepcopy(value)
        if initialize(obj, app) == 'fail':
            return 'fail'
        objects.append(obj)
        return obj

    app.app_obj = SimpleNamespace(new_object=factory)
    handler = SimpleNamespace(app=app, app_units=app.app_units, log=app.log, inform=signal)
    method = appIO.import_svg if source_format == 'SVG' else appIO.import_dxf
    assert method(handler, str(path), geo_type=sample.kind, outname='authored-source', plot=False) != 'fail'
    assert len(objects) == 1 and app.options == before
    return objects[0]


@pytest.mark.parametrize('source_format,application', [('SVG', 'Illustrator'), ('DXF', 'Proteus')])
def test_real_handler_preserves_exact_bom_crlf_and_producer_does_not_change_cam(
        object_factory, tmp_path, source_format, application):
    path = tmp_path / ('source.' + source_format.lower())
    source = source_bytes(source_format)
    path.write_bytes(source)
    obj = import_host(object_factory, path, source_format)
    record = read_cad_source(obj)
    assert record is not None and record.application == application and record.status == 'identified'
    assert record.source_sha256 == sha256(source).hexdigest()
    assert obj.source_file.encode('utf-8') == source and path.read_bytes() == source
    assert obj.obj_options['tools_mill_feedrate'] == 321.25
    assert obj.obj_options['tools_mill_cutz'] == -0.321
    expected = (2, 15, 6, 17) if source_format == 'SVG' else (2, 3, 6, 5)
    material = union_all(obj.solid_geometry)
    assert material.bounds == pytest.approx(expected)
    assert material.is_valid
    if source_format == 'SVG':
        assert material.area == pytest.approx(8)
    baseline_path = tmp_path / ('without-marker.' + source_format.lower())
    baseline_path.write_bytes(source_bytes(source_format, marker=False))
    baseline = import_host(object_factory, baseline_path, source_format)
    assert read_cad_source(baseline).application == 'Unknown'
    assert union_all(baseline.solid_geometry).equals(material)
    assert baseline.obj_options['tools_mill_feedrate'] == obj.obj_options['tools_mill_feedrate']


def test_actual_serializer_missing_old_field_keeps_none_without_inspection(object_factory):
    value = object_factory()
    assert value.cad_source is None
    data = value.to_dict()
    assert data.pop('cad_source') is None
    restored = object_factory()
    restored.from_dict(data)
    assert read_cad_source(restored) is None


@pytest.mark.parametrize('source_format', ['SVG', 'DXF'])
def test_actual_serializer_roundtrip_is_detached_and_requires_no_source_file(
        object_factory, tmp_path, monkeypatch, source_format):
    from camlib import dict2obj, to_dict
    from mikrocam.bridge import cad_source
    path = tmp_path / ('source.' + source_format.lower())
    path.write_bytes(source_bytes(source_format))
    value = import_host(object_factory, path, source_format)
    expected = read_cad_source(value)
    data = json.loads(json.dumps(value.to_dict(), default=to_dict, ensure_ascii=False), object_hook=dict2obj)
    path.unlink()
    monkeypatch.setattr(cad_source, 'detect_cad_source', lambda *args: pytest.fail('unexpected recomputation'))
    restored = object_factory()
    restored.from_dict(data)
    assert read_cad_source(restored) == expected
    assert restored.cad_source is not value.cad_source
    assert restored.source_file == value.source_file
    assert union_all(restored.solid_geometry).equals(union_all(value.solid_geometry))


def test_bad_assessment_does_not_block_actual_object_restore(object_factory):
    value = object_factory()
    data = value.to_dict()
    data['cad_source'] = {'schema_version': 999}
    restored = object_factory()
    restored.from_dict(data)
    assert restored.kind == value.kind and restored.obj_options['name'] == value.obj_options['name']
    with pytest.raises(ValueError):
        read_cad_source(restored)
