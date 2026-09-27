"""Authoritative Excellon operations, immutable snapshots and stale publication guards."""
from copy import deepcopy
from dataclasses import replace
import math
from types import SimpleNamespace

import pytest
from shapely.geometry import Point

from mikrocam.bridge.excellon_merge import (
    snapshot_excellon, load_excellon_merge, verify_excellon_merge, create_excellon_merge,
)


def owner(name='a', x=0, units='MM'):
    return SimpleNamespace(kind='excellon', obj_options={'name':name}, units=units,
        tools={1:{'tooldia':1.,'drills':[Point(x,0)],'data':{'feedrate':42}}},
        solid_geometry=['deliberately stale'],source_file='unchanged historical source')


def app_for(owners):
    return SimpleNamespace(collection=SimpleNamespace(get_by_name=lambda name: next(
        (o for o in owners if o.obj_options['name']==name),None)))


def test_drill_only_import_shape_missing_slots_is_valid_and_source_unchanged():
    source=owner(); original=deepcopy(source.__dict__)
    result=snapshot_excellon(source)
    assert result.tools[0].tool.drills_mm == ((0.,0.),)
    assert result.tools[0].tool.slots_mm == ()
    assert source.__dict__ == original
    source.solid_geometry=None; source.source_file='different text'
    assert snapshot_excellon(source) == result


def test_slot_only_import_shape_missing_drills_and_mixed_units():
    source=owner(units='IN')
    source.tools={1:{'tooldia':.1,'slots':[(Point(1,2),Point(3,2))]}}
    result=snapshot_excellon(source)
    assert result.tools[0].tool.diameter_mm == pytest.approx(2.54)
    assert result.tools[0].tool.drills_mm == ()
    assert result.tools[0].tool.slots_mm == (((25.4,50.8),(76.19999999999999,50.8)),)


def test_typed_tool_ids_and_source_hash_determinism():
    source=owner(); source.tools['1']={'tooldia':2,'slots':[[Point(10,0),Point(12,0)]]}
    a=snapshot_excellon(source)
    source.tools=dict(reversed(tuple(source.tools.items())))
    assert snapshot_excellon(source) == a
    assert [t.tool_id for t in a.tools] == ['int:1','str:1']
    source.tools[1]['drills'].append(Point(20,0))
    assert snapshot_excellon(source).source_sha256 != a.source_sha256


@pytest.mark.parametrize('tools',[{}, {1:{}}, {1:None}, {True:{'tooldia':1,'drills':[Point(0,0)]}},
    {1:{'tooldia':1,'drills':None}}, {1:{'tooldia':1,'slots':[]}},
    {1:{'tooldia':True,'drills':[Point(0,0)]}}, {1:{'tooldia':math.inf,'drills':[Point(0,0)]}},
    {1:{'tooldia':1,'drills':[Point()]}}, {1:{'tooldia':1,'drills':[Point(0,0,0)]}},
    {1:{'tooldia':1,'drills':[Point(math.inf,0)]}},
    {1:{'tooldia':1,'slots':[(Point(0,0),Point(0,0))]}},
    {1:{'tooldia':1,'slots':[(Point(0,0),)]}},
    {1:{'tooldia':1,'drills':[Point(0,0)]*1001}},
    {'x'*241:{'tooldia':1,'drills':[Point(0,0)]}},
])
def test_malformed_or_excessive_tools_reject_entire_source(tools):
    source=owner(); source.tools=tools
    with pytest.raises(ValueError): snapshot_excellon(source)


@pytest.mark.parametrize('field,value',[('kind','geometry'),('units','INCH'),('units',None),
    ('obj_options',{}),('obj_options',{'name':' untrimmed'}),('obj_options',{'name':'bad\nname'})])
def test_invalid_source_contract(field,value):
    source=owner(); setattr(source,field,value)
    with pytest.raises(ValueError): snapshot_excellon(source)


@pytest.mark.parametrize('change',['name','units','diameter','drill','slot','key','removed','replaced'])
def test_source_changes_reject_stale_review(change):
    owners=(owner(),owner('b',10)); app=app_for(owners); review=load_excellon_merge(owners)
    source=owners[0]
    if change=='name': source.obj_options['name']='renamed'
    elif change=='units': source.units='IN'
    elif change=='diameter': source.tools[1]['tooldia']=2
    elif change=='drill': source.tools[1]['drills']=[Point(1,0)]
    elif change=='slot': source.tools[1]['slots']=[(Point(20,0),Point(22,0))]
    elif change=='key': source.tools['new']=source.tools.pop(1)
    elif change=='removed': app.collection.get_by_name=lambda name:None
    elif change=='replaced': app.collection.get_by_name=lambda name:owner(name)
    with pytest.raises(ValueError,match='[Aa]nalyse again'):
        verify_excellon_merge(app,owners,review)


def test_source_geometry_caches_and_tool_settings_are_not_operation_authority():
    owners=(owner(),owner('b',10)); app=app_for(owners); review=load_excellon_merge(owners)
    owners[0].source_file='text'; owners[0].solid_geometry=[]
    owners[0].tools[1]['data']['feedrate']=100
    verify_excellon_merge(app,owners,review)


def test_forged_review_with_real_source_hashes_rejected():
    owners=(owner(),owner('b',10)); review=load_excellon_merge(owners)
    forged=replace(review,tools=(replace(review.tools[0],drills_mm=((100.,100.),)),))
    with pytest.raises(ValueError,match='[Aa]nalyse again'):
        verify_excellon_merge(app_for(owners),owners,forged)


def test_selection_requires_distinct_identities_and_names():
    a=owner()
    for selected in ([],(a,),(a,a),(a,owner()),(a,)*65):
        with pytest.raises(ValueError): load_excellon_merge(selected)


def test_conflicts_block_before_factory(monkeypatch):
    owners=(owner(),owner('b',.5)); review=load_excellon_merge(owners)
    calls=[]
    monkeypatch.setattr('mikrocam.bridge.excellon_merge.create_excellon_operations',lambda *a,**k:calls.append(a))
    with pytest.raises(ValueError,match='conflict|overlap'):
        create_excellon_merge(app_for(owners),owners,review,'merged')
    assert not calls


def test_mixed_unit_exact_duplicate_and_roundoff_are_explicit():
    a=owner(); b=owner('b',units='IN')
    a.tools[1]['tooldia']=25.4; b.tools[1]['tooldia']=1
    assert len(load_excellon_merge((a,b)).duplicates) == 1
    a.tools[1]['tooldia']=7.62; b.tools[1]['tooldia']=.3
    result=load_excellon_merge((a,b))
    assert not result.duplicates and result.conflict_count == 1
    assert result.conflicts[0].reason == 'same-centre'


@pytest.mark.parametrize('when',['factory','export'])
def test_source_changes_inside_shared_factory_prevent_publication(when):
    from test_svg_drill_bridge import Host
    owners=(owner(),owner('b',10)); review=load_excellon_merge(owners)
    app=Host(); app.collection=app_for(owners).collection
    if when=='factory':
        original=app.app_obj.new_object
        def changed(*args):
            owners[1].tools[1]['drills']=[Point(11,0)]
            return original(*args)
        app.app_obj.new_object=changed
    else:
        original=app.f_handlers.export_excellon
        def changed(*args,**kwargs):
            result=original(*args,**kwargs)
            owners[0].tools[1]['tooldia']=2
            return result
        app.f_handlers.export_excellon=changed
    with pytest.raises(ValueError,match='[Aa]nalyse again'):
        create_excellon_merge(app,owners,review,'merged')
    assert not app.published


def test_successful_merge_preserves_sources_and_current_destination_defaults():
    from test_svg_drill_bridge import Host
    owners=(owner(),owner('b',10)); before=[deepcopy(o.__dict__) for o in owners]
    review=load_excellon_merge(owners); app=Host(); app.collection=app_for(owners).collection
    result=create_excellon_merge(app,owners,review,'merged')
    assert app.published == [result]
    assert all(o.__dict__ == expected for o,expected in zip(owners,before))
    assert result.tools[1]['data'] == app.defaults


def test_aggregate_tool_and_operation_limits():
    sources=[]
    for i in range(2):
        value=owner(str(i)); value.tools={j:{'tooldia':1,'drills':[Point(j*2,0)]} for j in range(501)}
        sources.append(value)
    with pytest.raises(ValueError,match='1000'):
        load_excellon_merge(tuple(sources))


def test_equivalent_sequence_containers_preserve_operation_fingerprint():
    source=owner()
    source.tools[1]['slots']=[(Point(10,0),Point(12,0))]
    original=snapshot_excellon(source)
    source.tools[1]['slots']=((Point(10,0),Point(12,0)),)
    source.tools[1]['drills']=tuple(source.tools[1]['drills'])
    assert snapshot_excellon(source) == original
    source.tools[1]['slots']=[[Point(10,0),Point(12,0)]]
    assert snapshot_excellon(source) == original
