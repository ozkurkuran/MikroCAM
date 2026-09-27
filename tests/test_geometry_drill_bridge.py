"""Host geometry authority and stale review guards, independent of Qt."""
from types import SimpleNamespace
from dataclasses import replace

import pytest
from shapely.geometry import Point

from mikrocam.bridge.geometry_drills import load_geometry_review, verify_geometry_review, create_geometry_drills


def owner():
    return SimpleNamespace(kind='geometry', obj_options={'name': 'board'}, units='MM',
        multigeo=False, solid_geometry=[Point(10, 12).buffer(.5, quad_segs=32)], tools={},
        source_file='preserved source')


def app_for(source):
    return SimpleNamespace(collection=SimpleNamespace(get_by_name=lambda name: source))


def test_single_authority_ignores_tools_and_preserves_state():
    source = owner(); source.tools = {'bad': None}
    result = load_geometry_review(source)
    assert result.candidates[0].center_mm == pytest.approx((10, 12))
    verify_geometry_review(app_for(source), source, result)
    assert source.source_file == 'preserved source'


def test_multi_authority_ignores_stale_top_level_and_types_keys():
    source = owner(); source.multigeo = True
    source.tools = {'1': {'solid_geometry': [Point(20, 12).buffer(.5, quad_segs=32)]},
                    1: {'solid_geometry': source.solid_geometry}}
    source.solid_geometry = None
    result = load_geometry_review(source)
    assert len(result.candidates) == 2
    assert 'int:1' in result.candidates[0].source_id
    assert 'str:1' in result.candidates[1].source_id
    source.tools = dict(reversed(tuple(source.tools.items())))
    assert load_geometry_review(source) == result


@pytest.mark.parametrize('field,value', [('kind','gerber'), ('multigeo',1), ('units','inch'),
    ('obj_options',{}), ('obj_options',{'name':' board '}), ('solid_geometry',None)])
def test_invalid_host_contract(field, value):
    source = owner(); setattr(source, field, value)
    with pytest.raises(ValueError):
        load_geometry_review(source)


@pytest.mark.parametrize('tools', [{}, {True:{'solid_geometry':[]}}, {1:{}},
    {1:None}, {1.5:{'solid_geometry':[]}}, {'x'*257:{'solid_geometry':[]}}])
def test_multi_missing_or_bad_tools_never_falls_back(tools):
    source = owner(); source.multigeo = True; source.tools = tools
    with pytest.raises(ValueError):
        load_geometry_review(source)


@pytest.mark.parametrize('change', ['name','units','mode','geometry','tool','removed','replaced'])
def test_stale_source_rejected(change):
    source = owner(); app = app_for(source)
    result = load_geometry_review(source)
    if change == 'name': source.obj_options['name'] = 'renamed'
    elif change == 'units': source.units = 'IN'
    elif change == 'mode':
        source.multigeo = True; source.tools = {1:{'solid_geometry':source.solid_geometry}}
    elif change == 'geometry': source.solid_geometry.append(Point(30, 0).buffer(1))
    elif change == 'tool':
        source.multigeo = True; source.tools = {1:{'solid_geometry':source.solid_geometry}}
        result = load_geometry_review(source)
        source.tools[2] = source.tools.pop(1)
    elif change == 'removed': app.collection.get_by_name = lambda name: None
    elif change == 'replaced': app.collection.get_by_name = lambda name: owner()
    with pytest.raises(ValueError, match='[Aa]nalyse again'):
        verify_geometry_review(app, source, result)


def test_creation_passes_both_source_guard_and_grouped_tools(monkeypatch):
    source = owner(); app = app_for(source); result = load_geometry_review(source)
    sentinel = object()
    def create(app_arg, tools, name, *, source_guard):
        assert app_arg is app and name == 'holes'
        assert tools[0].diameter_mm == pytest.approx(1)
        source_guard()
        source.solid_geometry = []
        with pytest.raises(ValueError, match='[Aa]nalyse again'):
            source_guard()
        return sentinel
    monkeypatch.setattr('mikrocam.bridge.geometry_drills.create_excellon_tools', create)
    assert create_geometry_drills(app, source, result, (0,), 'holes') is sentinel


@pytest.mark.parametrize('when', ['factory', 'export'])
def test_changed_geometry_inside_actual_shared_factory_never_publishes(when):
    from test_svg_drill_bridge import Host
    source = owner(); result = load_geometry_review(source)
    app = Host(); app.collection = app_for(source).collection
    if when == 'factory':
        original = app.app_obj.new_object
        def changed(*args):
            source.solid_geometry = []
            return original(*args)
        app.app_obj.new_object = changed
    else:
        original = app.f_handlers.export_excellon
        def changed(*args, **kwargs):
            text = original(*args, **kwargs)
            source.units = 'IN'
            return text
        app.f_handlers.export_excellon = changed
    with pytest.raises(ValueError, match='[Aa]nalyse again'):
        create_geometry_drills(app, source, result, (0,), 'holes')
    assert not app.published


def test_genuine_fingerprint_cannot_authorize_forged_measurements():
    source = owner(); result = load_geometry_review(source)
    forged = replace(result, candidates=(replace(result.candidates[0], center_mm=(100., 100.)),))
    with pytest.raises(ValueError, match='[Aa]nalyse again'):
        verify_geometry_review(app_for(source), source, forged)
