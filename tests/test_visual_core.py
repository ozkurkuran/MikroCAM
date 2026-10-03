"""Numerical contracts for visual masks, independent of any decoder."""
import hashlib
import struct
import numpy as np
import pytest
from mikrocam.core.visual import PreparationSettings, RasterFrame, BurnMask, build_grid
from mikrocam.core.visual_normalize import make_burn_mask


def preparation(width=30.0, height=18.0, **kwargs):
    return PreparationSettings(requested_width_mm=width, requested_height_mm=height, **kwargs)


def test_exact_grid_and_fractional_padding():
    grid=build_grid(preparation())
    assert (grid.width_px, grid.height_px)==(600,360)
    assert grid.pitch_mm==pytest.approx(.05)
    assert (grid.canvas_width_mm,grid.canvas_height_mm)==pytest.approx((30,18))
    fractional=build_grid(preparation(30.013,18.017))
    assert (fractional.width_px,fractional.height_px)==(601,361)
    valid=fractional.valid_area()
    assert not valid[-1].any() and not valid[:,-1].any()
    assert fractional.pixel_center(0,0)==pytest.approx((.025,18.025))


@pytest.mark.parametrize('field,value', [(f,v) for f in ('requested_width_mm','requested_height_mm','requested_dpi') for v in (0,-1,float('nan'),float('inf'),True)])
def test_invalid_preparation(field,value):
    kwargs=dict(requested_width_mm=30,requested_height_mm=18)
    kwargs[field]=value
    with pytest.raises(ValueError):
        build_grid(PreparationSettings(**kwargs))


def test_early_pixel_limit():
    with pytest.raises(ValueError,match='RASTER_LIMIT_EXCEEDED'):
        build_grid(preparation(10000,10000))


def test_alpha_threshold_and_invert_padding():
    prep=preparation(.2,.05)
    grid=build_grid(prep)
    rgba=np.array([[[0,0,0,0],[0,0,0,128],[128,128,128,255],[127,127,127,255]]],dtype=np.uint8)
    frame=RasterFrame(rgba,grid,grid.valid_area())
    mask=make_burn_mask(frame,prep)
    assert mask.burn.tolist()==[[False,True,False,True]]
    rgba[:]=255
    assert not frame.rgba.flags.writeable and frame.rgba[0,1,3]==128
    inverted=make_burn_mask(frame,preparation(.2,.05,invert=True))
    assert inverted.burn.tolist()==[[True,False,True,False]]
    tiny=build_grid(preparation(.026,.026,invert=True))
    invalid=RasterFrame(np.zeros((1,1,4),dtype=np.uint8),tiny,np.zeros((1,1),dtype=bool))
    assert not make_burn_mask(invalid,preparation(.026,.026,invert=True)).burn.any()


def test_mask_digest_ownership_and_dtype():
    grid=build_grid(preparation(.1,.1))
    original=np.array([[True,False],[False,True]])
    mask=BurnMask(original,grid)
    expected=hashlib.sha256(b'MCAM-MASK-1\0'+struct.pack('>II',2,2)+b'\x90').hexdigest()
    assert mask.sha256==expected and mask.black_pixel_count==2
    original[:]=False
    assert mask.black_pixel_count==2 and mask.burn[0,0]
    assert mask.burn.flags.c_contiguous and not mask.burn.flags.writeable
    # A caller must not be able to undo read-only and corrupt the digest.
    with pytest.raises(ValueError): mask.burn.setflags(write=True)
    with pytest.raises(ValueError): BurnMask(np.zeros((2,2),dtype=np.uint8),grid)


@pytest.mark.parametrize('threshold',[0,256,True,128.5])
def test_invalid_threshold(threshold):
    with pytest.raises(ValueError): preparation(threshold=threshold)


def test_preview_does_not_lose_group_when_downsampling():
    from mikrocam.core.visual_preview import preview_rgb
    grid=build_grid(preparation(.05,120.05))
    data=np.zeros((2401,1),bool); data[1,0]=True
    master=BurnMask(data,grid)
    image=preview_rgb(master,3,group=1,max_side=1200)
    assert np.any(image < 255)
    assert not preview_rgb(master,3,group=2,max_side=1200).min() < 255
    assert master.black_pixel_count==1


def test_grid_rejects_nonfinite_derived_pitch():
    with pytest.raises(ValueError): build_grid(preparation(requested_dpi=5e-324))
