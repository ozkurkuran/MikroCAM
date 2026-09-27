"""Clip intersections retain material dimension and preflight topology cost."""
import pytest
from shapely.geometry import box

from mikrocam.core.svg_clip import apply_svg_clips
from mikrocam.core.svg_models import SvgClip,SvgDocument,SvgElement,SvgPaint,SvgPath,SvgRendered,SvgViewport
from mikrocam.core.svg_transform import IDENTITY


def inputs():
    clip=SvgClip('a','c','userSpaceOnUse',IDENTITY,())
    element=SvgElement('e','rect',(),IDENTITY,SvgPaint(),clips=(clip,))
    document=SvgDocument('a.svg','a'*64,SvgViewport(10,10,IDENTITY),(element,))
    path=SvgPath(((0.,0.),(10.,0.),(10.,10.),(0.,10.),(0.,0.)),True)
    return document,(SvgRendered((path,),(box(0,0,10,10),)),)


def test_polygon_touching_clip_edge_does_not_turn_into_cutting_line():
    doc,rendered=inputs()
    result=apply_svg_clips(doc,rendered,{'a':(box(10,0,20,10),)})
    assert result[0].geometry_mm==()
    assert result[0].paths_mm==rendered[0].paths_mm


def test_clip_topology_preflight_rejects_before_overlay(monkeypatch):
    from mikrocam.core import svg_clip
    monkeypatch.setattr(svg_clip,'MAX_CLIP_SEGMENTS',3,raising=False)
    doc,rendered=inputs()
    with pytest.raises(ValueError,match='budget|limit'):
        apply_svg_clips(doc,rendered,{'a':(box(5,0,20,10),)})
