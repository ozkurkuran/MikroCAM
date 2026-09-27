"""Report dictionaries survive real host serialization and old project migration."""
from copy import deepcopy
import json
import logging
from types import SimpleNamespace

import pytest

from mikrocam.bridge.import_report import read_import_report, store_import_report
from mikrocam.bridge.svg_import import import_svg_bytes


@pytest.fixture(params=['geometry', 'gerber'])
def object_factory(request, qtbot, monkeypatch):
    from appObjects import AppObjectTemplate
    from appObjects.GeometryObject import GeometryObject
    from appObjects.GerberObject import GerberObject
    from defaults import AppDefaults
    monkeypatch.setattr(AppObjectTemplate, 'ShapeCollection', lambda **kwargs: SimpleNamespace())
    options = deepcopy(AppDefaults.factory_defaults)
    app = SimpleNamespace(options=options, defaults=options, app_units='MM', decimals=4,
                          use_3d_engine=True, call_source='app', pool=None,
                          log=logging.getLogger('import-report-persistence'),
                          plotcanvas=SimpleNamespace(view=SimpleNamespace(scene=None),
                              new_shape_group=lambda: SimpleNamespace(),
                              new_shape_collection=lambda **kwargs: SimpleNamespace()))
    instances = []

    def create():
        cls = GeometryObject if request.param == 'geometry' else GerberObject
        value = cls('report-object', app)
        value.solid_geometry = []
        value.follow_geometry = []
        instances.append(value)
        return value

    yield create
    for value in instances:
        value.deleteLater()


def test_missing_old_field_migrates_to_unavailable_without_inventing_report(object_factory):
    old = object_factory()
    assert old.import_report is None
    payload = old.to_dict()
    assert payload.pop('import_report') is None
    restored = object_factory()
    restored.from_dict(payload)
    assert read_import_report(restored) is None
    assert restored.obj_options['name'] == old.obj_options['name']
    assert restored.units == old.units


def test_exact_supported_report_and_source_roundtrip(object_factory):
    value = object_factory()
    source = (b'<svg width="1in" height="25.4mm" viewBox="0 0 10 10">'
              b'<path d="M0 0L5 0L5 5"/></svg>')
    value.source_file = source.decode()
    store_import_report(value, import_svg_bytes(source, 'roundtrip.svg'))
    report = read_import_report(value)
    payload = json.loads(json.dumps(value.to_dict(), ensure_ascii=False))
    restored = object_factory()
    restored.from_dict(payload)
    assert read_import_report(restored) == report
    assert restored.source_file == value.source_file
    assert restored.import_report is not value.import_report
    assert restored.tools == value.tools


@pytest.mark.parametrize('record', [{'schema_version': 999}, {'schema_version': True}, ['broken']])
def test_bad_report_does_not_block_normal_legacy_object_restore(object_factory, record):
    old = object_factory()
    payload = old.to_dict()
    payload['import_report'] = record
    restored = object_factory()
    restored.from_dict(payload)
    assert restored.kind == old.kind
    assert restored.obj_options['name'] == 'report-object'
    with pytest.raises(ValueError):
        read_import_report(restored)
