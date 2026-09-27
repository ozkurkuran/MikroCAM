"""Bounded source records for immutable SVG clipping and page evidence."""
from dataclasses import replace

import pytest

from mikrocam.core.svg_models import SvgClip, SvgDocument, SvgElement, SvgPaint, SvgViewport
from mikrocam.core.svg_transform import IDENTITY


def shape(**changes):
    return replace(SvgElement('shape', 'rect', (), IDENTITY, SvgPaint()), **changes)


def clip(**changes):
    return replace(SvgClip('application', 'definition', 'userSpaceOnUse', IDENTITY, (shape(),)), **changes)


def test_clip_records_are_bounded_and_do_not_change_positional_shape_contract():
    element = shape()
    assert element.clips == () and element.layer_path == ()
    applied = shape(clips=(clip(),), layer_path=('Board', 'Copper'))
    assert applied.clips[0].elements[0] == element
    assert applied.layer_path == ('Board', 'Copper')


@pytest.mark.parametrize('changes', [
    {'application_id': ''}, {'application_id': 'x'*257}, {'source_id': ''},
    {'units': 'pixels'}, {'matrix': (1,0,0,0,0,0)}, {'elements': []},
    {'elements': (None,)}, {'elements': (shape(),)*65},
    {'elements': (shape(clips=(clip(),)),)},
])
def test_invalid_clip_records_rejected(changes):
    with pytest.raises(ValueError):
        clip(**changes)


@pytest.mark.parametrize('changes', [
    {'clips': []}, {'clips': (None,)}, {'clips': (clip(),)*9},
    {'layer_path': []}, {'layer_path': ('',)}, {'layer_path': ('x'*257,)},
    {'layer_path': ('x',)*65},
])
def test_invalid_layer_and_clip_chain_rejected(changes):
    with pytest.raises(ValueError):
        shape(**changes)


def test_empty_clip_is_valid_and_effective_root_is_separate():
    assert clip(elements=()).elements == ()
    original = (('width','100%'), ('height','100%'), ('viewBox','0 0 10 20'))
    effective = (('width','10mm'), ('height','20mm'), ('viewBox','0 0 10 20'))
    doc = SvgDocument('a.svg', 'a'*64, SvgViewport(10,20,IDENTITY), (),
                      root_attributes=original, viewport_attributes=effective)
    assert doc.root_attributes is original and doc.viewport_attributes is effective
    with pytest.raises(ValueError):
        replace(doc, viewport_attributes=(('width','10mm'),('width','20mm')))
