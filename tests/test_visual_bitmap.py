"""Actual image codecs, orientation and complementary 1-bit export."""
from dataclasses import replace
from io import BytesIO
import numpy as np
import pytest
from PIL import Image
from mikrocam.bridge.visual_bitmap import inspect_bitmap, render_bitmap
from mikrocam.bridge.visual_png import encode_mask_png, decode_mask_png
from mikrocam.core.visual import SourceAsset, PreparationSettings, BurnMask, build_grid
from mikrocam.core.visual_normalize import make_burn_mask


def encoded(image,format='PNG',**kwargs):
    stream=BytesIO(); image.save(stream,format=format,**kwargs); return stream.getvalue()


@pytest.mark.parametrize('format',['PNG','JPEG','BMP','TIFF','WEBP','GIF'])
def test_formats_and_pixels(format):
    image=Image.new('RGB',(13,10),'white'); image.putpixel((0,0),(0,0,0))
    data=encoded(image,format)
    info=inspect_bitmap(data)
    assert info.page_count==1 and info.native_size_px==(13,10)
    prep=PreparationSettings(.65,.5)
    frame=render_bitmap(SourceAsset('example',data,info),prep,build_grid(prep))
    mask=make_burn_mask(frame,prep)
    assert mask.burn[0,0] and not mask.burn[-1,-1]
    assert (mask.grid.width_px,mask.grid.height_px)==(13,10)


def test_one_bit_exact_and_png_roundtrip():
    data=np.random.default_rng(87).integers(0,2,(10,13)).astype(bool)
    image=Image.fromarray(np.where(data,0,255).astype('uint8')).convert('1')
    png=encoded(image)
    prep=PreparationSettings(.65,.5)
    mask=make_burn_mask(render_bitmap(SourceAsset('test.png',png,inspect_bitmap(png)),prep,build_grid(prep)),prep)
    assert np.array_equal(mask.burn,data)
    output=encode_mask_png(mask)
    assert Image.open(BytesIO(output)).mode=='1'
    assert decode_mask_png(output,mask.grid).sha256==mask.sha256
    gray=encoded(Image.new('L',(13,10),127))
    with pytest.raises(ValueError): decode_mask_png(gray,mask.grid)


def test_palette_alpha_and_exif():
    image=Image.new('P',(2,1),0); image.putpalette([0,0,0,255,255,255]+[0]*762)
    png=encoded(image,transparency=0)
    prep=PreparationSettings(.1,.05)
    frame=render_bitmap(SourceAsset('alpha.png',png,inspect_bitmap(png)),prep,build_grid(prep))
    assert not make_burn_mask(frame,prep).burn.any()
    image=Image.new('RGB',(2,3),'white'); image.putpixel((0,0),(0,0,0))
    exif=Image.Exif(); exif[274]=6
    png=encoded(image,exif=exif)
    assert inspect_bitmap(png).native_size_px==(3,2)


@pytest.mark.parametrize('format',['TIFF','GIF','WEBP'])
def test_explicit_frame_selection(format):
    first=Image.new('RGB',(3,2),'white'); second=Image.new('RGB',(3,2),'black')
    data=encoded(first,format,save_all=True,append_images=[second],duration=100)
    info=inspect_bitmap(data)
    assert info.page_count==2
    prep=PreparationSettings(.15,.1)
    frame=render_bitmap(SourceAsset('pages',data,info,1),prep,build_grid(prep))
    assert make_burn_mask(frame,prep).burn.all()
    with pytest.raises(ValueError): SourceAsset('pages',data,info,2)


def test_quarter_turn_crop_mirror_and_fractional_scale():
    image=Image.new('1',(4,2),1); image.putpixel((0,0),0)
    data=encoded(image); info=inspect_bitmap(data)
    prep=PreparationSettings(.1,.2,quarter_turns=1)
    frame=render_bitmap(SourceAsset('x',data,info),prep,build_grid(prep))
    expected=np.zeros((4,2),bool); expected[0,1]=True
    assert np.array_equal(make_burn_mask(frame,prep).burn,expected)
    prep=PreparationSettings(.2013,.1017,invert=True)
    frame=render_bitmap(SourceAsset('x',data,info),prep,build_grid(prep))
    result=make_burn_mask(frame,prep)
    assert not result.burn[:,-1].any() and not result.burn[-1].any()
    with pytest.raises(ValueError):
        render_bitmap(SourceAsset('x',data,info),replace(prep,crop_rect=(0,0,8,8)),build_grid(prep))


def test_corrupt_unknown_and_bomb_before_decode(monkeypatch):
    for data in (b'not an image',b'\x89PNG\r\n\x1a\ntruncated'):
        with pytest.raises(ValueError): inspect_bitmap(data)
    monkeypatch.setattr(Image,'MAX_IMAGE_PIXELS',1)
    with pytest.raises(ValueError): inspect_bitmap(encoded(Image.new('RGB',(4,4))))


def test_16_bit_grayscale_is_scaled_without_clipping():
    image=Image.fromarray(np.array([[0,20000,65535]],dtype=np.uint16))
    data=encoded(image); prep=PreparationSettings(.15,.05)
    mask=make_burn_mask(render_bitmap(SourceAsset('gray16.png',data,inspect_bitmap(data)),prep,build_grid(prep)),prep)
    assert mask.burn.tolist()==[[True,True,False]]


def test_cmyk_and_srgb_icc_color_management():
    from PIL import ImageCms
    image=Image.new('CMYK',(2,1),(0,0,0,255));image.putpixel((1,0),(0,0,0,0))
    prep=PreparationSettings(.1,.05)
    data=encoded(image,'TIFF')
    frame=render_bitmap(SourceAsset('cmyk.tif',data,inspect_bitmap(data)),prep,build_grid(prep))
    assert make_burn_mask(frame,prep).burn.tolist()==[[True,False]]
    profile=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    rgb=Image.new('RGB',(2,1),'white');rgb.putpixel((0,0),(0,0,0))
    data=encoded(rgb,icc_profile=profile)
    info=inspect_bitmap(data);assert 'SOURCE_ASSUMED_SRGB' not in info.import_notes
    frame=render_bitmap(SourceAsset('icc.png',data,info),prep,build_grid(prep))
    assert make_burn_mask(frame,prep).burn.tolist()==[[True,False]]
    broken=encoded(rgb,icc_profile=b'broken')
    with pytest.raises(ValueError,match='color profile'):
        render_bitmap(SourceAsset('bad-icc.png',broken,inspect_bitmap(broken)),prep,build_grid(prep))


def test_explicit_bitmap_crop_preserves_selected_source_pixels():
    image=Image.new('1',(4,4),1);image.putpixel((1,1),0);image.putpixel((0,0),0)
    data=encoded(image);prep=PreparationSettings(.1,.1,crop_rect=(1,1,3,3))
    result=make_burn_mask(render_bitmap(SourceAsset('crop.png',data,inspect_bitmap(data)),prep,build_grid(prep)),prep)
    assert result.burn.tolist()==[[True,False],[False,False]]
