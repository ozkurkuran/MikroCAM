"""Shared golden contract and asymmetric edge patterns; no native application needed."""
import json
from pathlib import Path
import numpy as np
import pytest
from mikrocam.core.visual import BurnMask,PreparationSettings,build_grid
from mikrocam.core.interlace_job import InterlaceSettings
from mikrocam.core.visual_interlace import partition_rows,base_order,materialize_group,source_row_direction
from mikrocam.laser.visual_plan import build_plan

REFERENCE=json.loads((Path(__file__).parent/'reference/visual/reference-cases.json').read_text())


def test_shared_partition_order_direction_and_physical_contract():
    for case in REFERENCE['partition_cases']:
        assert [list(rows) for rows in partition_rows(case['height'],case['count'])]==case['expected']
    for count,order in REFERENCE['mixed_orders'].items():
        assert list(base_order(int(count),'mixed'))==order
    case=REFERENCE['direction_case']
    assert [source_row_direction(r) for r in case['rows']]==case['expected']
    case=REFERENCE['physical_case'];grid=build_grid(PreparationSettings(case['width_mm'],case['height_mm'],case['dpi']))
    assert (grid.width_px,grid.height_px)==(case['width_px'],case['height_px'])
    assert grid.pitch_mm==case['pitch_mm']
    assert grid.pitch_mm*case['count']==pytest.approx(case['group_row_spacing_mm'])


def test_shared_empty_rows_cycles_and_requested_delay_contract():
    case=REFERENCE['empty_row_case'];grid=build_grid(PreparationSettings(.05,case['height']*.05))
    data=np.zeros((case['height'],1),bool);data[case['nonempty_rows']]=True
    mask=BurnMask(data,grid)
    plan=build_plan(mask,InterlaceSettings(count=case['count'],round_count=case['round_count'],delay_ms=case['delay_ms']),1)
    assert plan.active_pass_count==case['active_pass_count'] and plan.total_delay_ms==case['total_delay_ms']
    for k,expected in enumerate(case['active_rows_by_group']):
        assert np.flatnonzero(materialize_group(mask,k,case['count']).burn[:,0]).tolist()==expected
    case=REFERENCE['vary_order_case']
    plan=build_plan(mask,InterlaceSettings(count=case['count'],round_count=case['round_count'],order_mode=case['mode'],vary_order_each_round=True),1)
    assert [list(order) for order in plan.effective_orders]==case['expected_orders']


@pytest.mark.parametrize('pattern',['white','black','checkerboard','corners','single'])
@pytest.mark.parametrize('count',range(1,9))
def test_edge_patterns_are_lossless_and_disjoint(pattern,count):
    grid=build_grid(PreparationSettings(.65,.5));data=np.zeros((10,13),bool)
    if pattern=='black':data[:]=True
    elif pattern=='checkerboard':data[:]=np.indices(data.shape).sum(axis=0)%2==0
    elif pattern=='corners':data[0,0]=data[0,-1]=data[-1,0]=data[-1,-1]=True
    elif pattern=='single':data[7,11]=True
    mask=BurnMask(data,grid);total=np.zeros(data.shape,np.uint16)
    for group in base_order(count,'mixed'):
        part=materialize_group(mask,group,count);total+=part.burn
        assert part.grid==grid
    assert np.array_equal(total,data)
    assert mask.sha256==BurnMask(data,grid).sha256


@pytest.mark.parametrize('spot,expected',[(None,False),(.049,False),(.05,False),(.051,True)])
def test_spot_note_is_only_a_strict_pitch_comparison(spot,expected):
    grid=build_grid(PreparationSettings(.05,.05));mask=BurnMask(np.zeros((1,1),bool),grid)
    assert build_plan(mask,InterlaceSettings(spot_diameter_mm=spot),1).pitch_below_spot is expected
