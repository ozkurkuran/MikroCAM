"""Real GeometryObject construction and inherited project dictionary round trips."""
from copy import deepcopy
import json
import logging
from types import SimpleNamespace

import pytest


@pytest.fixture
def geometry_factory(qtbot, monkeypatch):
    from appObjects import AppObjectTemplate
    from appObjects.GeometryObject import GeometryObject
    from defaults import AppDefaults

    # Rendering is irrelevant to persistence; retain the real QObject and object constructors.
    monkeypatch.setattr(AppObjectTemplate, 'ShapeCollection', lambda **kwargs: SimpleNamespace())
    options = deepcopy(AppDefaults.factory_defaults)
    app = SimpleNamespace(options=options, defaults=options, app_units='MM', decimals=4,
                          use_3d_engine=True, call_source='app', pool=None,
                          log=logging.getLogger('svg-source-persistence'),
                          plotcanvas=SimpleNamespace(view=SimpleNamespace(scene=None),
                              new_shape_group=lambda: SimpleNamespace(),
                              new_shape_collection=lambda **kwargs: SimpleNamespace()))
    objects = []

    def create(name='source-test'):
        value = GeometryObject(name, app)
        objects.append(value)
        return value

    yield create
    for value in objects:
        value.deleteLater()


def test_actual_geometry_constructor_initializes_empty_source(geometry_factory):
    value = geometry_factory()
    assert value.source_file == ''
    assert value.to_dict()['source_file'] == ''


def test_inherited_serializers_preserve_complete_utf8_bom_crlf_source(geometry_factory):
    value = geometry_factory()
    text = '\ufeff<svg><!-- Türkçe ışık ölçüsü -->\r\n<path d="M0 0L1 1"/>\r\n</svg>\r\n'
    value.source_file = text
    payload = json.loads(json.dumps(value.to_dict(), ensure_ascii=False))
    assert payload['source_file'] == text
    restored = geometry_factory('restored')
    restored.from_dict(payload)
    assert restored.source_file == text
    assert restored.source_file.encode('utf-8') == text.encode('utf-8')
    assert restored.kind == value.kind == 'geometry'
    assert restored.obj_options['name'] == 'source-test'


def test_old_dictionary_without_source_keeps_constructor_empty_default(geometry_factory):
    previous = geometry_factory('old-project')
    payload = previous.to_dict()
    payload.pop('source_file', None)
    restored = geometry_factory('new-object')
    restored.from_dict(payload)
    assert restored.source_file == ''
    assert restored.obj_options['name'] == 'old-project'
    assert restored.units == previous.units == 'MM'
    assert restored.tools == previous.tools
