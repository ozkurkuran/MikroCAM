"""Analytic winding and bounded topology cases, independent of importer syntax."""
import pytest
from shapely import union_all

from mikrocam.core.svg_fill import fill_svg_paths
from mikrocam.core.svg_models import SvgPath, SvgPaint
from mikrocam.core.svg_paint import render_svg_paths
from mikrocam.core.svg_transform import IDENTITY


def square(x=0., y=0., side=10., reverse=False):
    pts = ((x,y),(x+side,y),(x+side,y+side),(x,y+side),(x,y))
    return SvgPath(tuple(reversed(pts)) if reverse else pts, True)


def material(paths, rule='nonzero'):
    return union_all(fill_svg_paths(paths, rule))


@pytest.mark.parametrize('rule,reverse,area', [('nonzero',False,150),('nonzero',True,100),
    ('evenodd',False,100),('evenodd',True,100)])
def test_overlapping_rings_follow_signed_winding(rule, reverse, area):
    result=material((square(),square(5,0,10,reverse)),rule)
    assert result.is_valid and result.area == area and result.bounds == (0.,0.,15.,10.)


@pytest.mark.parametrize('rule,reverse,area', [('nonzero',False,100),('nonzero',True,0),
    ('evenodd',False,0),('evenodd',True,0)])
def test_coincident_rings_preserve_multiplicity(rule,reverse,area):
    assert material((square(),square(reverse=reverse)),rule).area == area


@pytest.mark.parametrize('rule',['nonzero','evenodd'])
def test_self_crossing_bowtie_keeps_both_lobes(rule):
    bow=SvgPath(((0.,0.),(4.,4.),(0.,4.),(4.,0.),(0.,0.)),True)
    result=material((bow,),rule)
    assert result.is_valid and result.area == 8
    assert len(result.geoms) == 2


def test_shared_edge_and_touching_corner_regions():
    assert material((square(),square(10,0))).area == 200
    assert material((square(),square(10,10))).area == 200
    assert material((square(),square(0,0,5,True))).area == 75


def test_empty_cancellation_is_valid_and_source_closure_unchanged():
    paths=(square(),square(reverse=True))
    rendered=render_svg_paths(paths,SvgPaint(),IDENTITY)
    assert rendered.geometry_mm == ()
    assert rendered.paths_mm == paths
    open_path=SvgPath(((0.,0.),(4.,4.),(0.,4.),(4.,0.)))
    rendered=render_svg_paths((open_path,),SvgPaint(),IDENTITY)
    assert union_all(rendered.geometry_mm).area == 8
    assert not rendered.paths_mm[0].closed


def test_nested_large_coordinates_do_not_lose_winding_sign():
    x=1e9-10
    assert material((square(x,x),square(x+2,x+2,6,True))).area == 64


def test_complex_segment_budget_checked_before_noding(monkeypatch):
    from mikrocam.core import svg_fill
    monkeypatch.setattr(svg_fill,'MAX_COMPLEX_SEGMENTS',7)
    with pytest.raises(ValueError,match='budget|limit'):
        material((square(),square(5,0)))


def test_complex_intersection_pair_budget(monkeypatch):
    from mikrocam.core import svg_fill
    monkeypatch.setattr(svg_fill,'MAX_INTERSECTION_PAIRS',1)
    with pytest.raises(ValueError,match='budget|limit'):
        material((square(),square(5,0)))


@pytest.mark.parametrize('limit',['MAX_FILL_FACES','MAX_WINDING_OPERATIONS'])
def test_complex_face_and_winding_limits(monkeypatch,limit):
    from mikrocam.core import svg_fill
    monkeypatch.setattr(svg_fill,limit,1)
    with pytest.raises(ValueError,match='budget|limit'):
        material((square(),square(5,0)))
