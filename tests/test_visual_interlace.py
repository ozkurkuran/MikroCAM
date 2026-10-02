"""Partitions, complementary pixels, original-row direction and cycle scheduling."""
import numpy as np
import pytest
from mikrocam.core.visual import BurnMask, PreparationSettings, build_grid
from mikrocam.core.interlace_job import InterlaceSettings
from mikrocam.core.visual_interlace import partition_rows, base_order, source_row_direction, materialize_group
from mikrocam.laser.visual_plan import build_plan, validate_plan


def mask(rows=10,width=13,blank=False):
    grid=build_grid(PreparationSettings(width*.05,rows*.05))
    data=np.zeros((rows,width),dtype=bool) if blank else np.random.default_rng(451).integers(0,2,(rows,width)).astype(bool)
    return BurnMask(data,grid)


def test_three_by_ten():
    assert [list(x) for x in partition_rows(10,3)]==[[0,3,6,9],[1,4,7],[2,5,8]]


@pytest.mark.parametrize('n',range(1,9))
def test_exhaustive_partition(n):
    for h in (*range(1025),1025,4095,4096,4097,100003):
        rows=[r for group in partition_rows(h,n) for r in group]
        assert len(rows)==h and set(rows)==set(range(h))


@pytest.mark.parametrize('h,n',[(h,n) for h in (-1,True,2.5) for n in (1,3)]+[(10,n) for n in (0,9,True,3.5)])
def test_partition_validation(h,n):
    with pytest.raises(ValueError): partition_rows(h,n)


@pytest.mark.parametrize('n',range(1,9))
def test_disjoint_pixels_and_n_one_identity(n):
    master=mask()
    total=np.zeros(master.burn.shape,dtype=np.uint16)
    for k in range(n):
        part=materialize_group(master,k,n)
        total+=part.burn
        assert part.grid==master.grid
        assert not part.burn.flags.writeable
    assert np.array_equal(total,master.burn)
    if n==1: assert materialize_group(master,0,1).sha256==master.sha256


@pytest.mark.parametrize('n,expected',[(1,[0]),(2,[0,1]),(3,[0,2,1]),(4,[0,2,1,3]),(5,[0,4,2,1,3]),(6,[0,4,2,1,5,3]),(7,[0,4,2,6,1,5,3]),(8,[0,4,2,6,1,5,3,7])])
def test_mixed_order(n,expected):
    assert list(base_order(n,'mixed'))==expected
    assert base_order(n,'sequential')==tuple(range(n))


def test_direction_with_skipped_rows():
    for n in range(1,9):
        for rows in partition_rows(10,n):
            for r in rows:
                assert source_row_direction(r)==('left_to_right' if r%2==0 else 'right_to_left')


def test_rounds_rotation_empty_groups_and_dwell():
    master=mask(2)
    settings=InterlaceSettings(count=3,order_mode='mixed',round_count=3,vary_order_each_round=True,delay_ms=17)
    plan=build_plan(master,settings,revision=4)
    assert plan.effective_orders==((0,2,1),(1,0,2),(2,1,0))
    assert len(plan.passes)==9 and plan.active_pass_count==6
    assert sum(p.delay_before_ms for p in plan.passes)==85
    assert [p.delay_before_ms for p in plan.passes if p.enabled]==[0,17,17,17,17,17]
    assert all(p.delay_before_ms==0 for p in plan.passes if not p.enabled)
    total=np.zeros(master.burn.shape,dtype=np.uint16)
    for p in plan.passes: total+=materialize_group(master,p.group_index,3).burn
    assert np.array_equal(total,master.burn.astype(np.uint16)*3)
    validate_plan(master,plan,revision=4)
    with pytest.raises(ValueError,match='PLAN_STALE'): validate_plan(master,plan,revision=5)
    different=BurnMask(master.burn,build_grid(PreparationSettings(.65,.1,requested_dpi=508)))
    # Same pixels but different physical pitch must also be rejected.
    from dataclasses import replace
    different=BurnMask(master.burn,replace(master.grid,requested_dpi=1016,requested_width_mm=.325,requested_height_mm=.05))
    with pytest.raises(ValueError,match='PLAN_STALE'): validate_plan(different,plan,revision=4)


def test_blank_plan_and_sequential_rounds():
    plan=build_plan(mask(blank=True),InterlaceSettings(round_count=2,delay_ms=20),1)
    assert plan.active_pass_count==0 and plan.total_delay_ms==0
    assert [p.group_index for p in plan.passes]==[0,1,2,0,1,2]


@pytest.mark.parametrize('field,value',[('count',True),('count',9),('round_count',0),('round_count',1000),('delay_ms',-1),('delay_ms',600001),('order_mode','random'),('spot_diameter_mm',0)])
def test_invalid_settings(field,value):
    with pytest.raises(ValueError): InterlaceSettings(**{field:value})
