"""Static SVG and selected PDF pages use the same canonical mask pipeline."""
from io import BytesIO
import numpy as np
import pytest
from reportlab.pdfgen.canvas import Canvas
from mikrocam.core.visual import SourceAsset, PreparationSettings, build_grid
from mikrocam.bridge.visual_svg import inspect_svg, render_svg
from mikrocam.ui.visual_pdf import inspect_pdf, render_pdf_page
from mikrocam.core.visual_normalize import make_burn_mask
from mikrocam.core.visual_interlace import materialize_group

SVG=b'''<svg xmlns="http://www.w3.org/2000/svg" width="30mm" height="18mm" viewBox="0 0 30 18">
<defs><clipPath id="clip"><rect x="2" y="2" width="5" height="5"/></clipPath></defs>
<rect width="30" height="18" fill="white"/><rect x="1" y="1" width="10" height="10" clip-path="url(#clip)"/>
<path d="M15 2h10v10h-10z M17 4h6v6h-6z" fill-rule="evenodd"/>
<path d="M2 15h20" stroke="black" stroke-width=".1" transform="translate(1 0)"/>
</svg>'''


def pdf():
    stream=BytesIO(); canvas=Canvas(stream,pagesize=(30/25.4*72,18/25.4*72))
    canvas.setFillColorRGB(0,0,0); canvas.rect(2/25.4*72,11/25.4*72,5/25.4*72,5/25.4*72,fill=1,stroke=0)
    canvas.showPage(); canvas.setPageSize((20/25.4*72,10/25.4*72))
    canvas.setFillColorRGB(0,0,0); canvas.rect(0,0,20/25.4*72,10/25.4*72,fill=1,stroke=0)
    canvas.save(); return stream.getvalue()


def test_svg_physical_size_clip_and_hole():
    info=inspect_svg(SVG)
    assert info.suggested_size_mm==pytest.approx((30,18))
    prep=PreparationSettings(30,18)
    mask=make_burn_mask(render_svg(SourceAsset('x.svg',SVG,info),prep,build_grid(prep)),prep)
    assert (mask.grid.width_px,mask.grid.height_px)==(600,360)
    assert mask.burn[60,60] and not mask.burn[20,20]
    assert mask.burn[50,310] and not mask.burn[100,400]
    assert np.array_equal(sum((materialize_group(mask,k,3).burn.astype(np.uint16) for k in range(3))),mask.burn)


@pytest.mark.parametrize('size,expected',[(b'width="96px" height="48px"',(25.4,12.7)),(b'viewBox="0 0 96 48"',(25.4,12.7)),(b'width="1in" height=".5in"',(25.4,12.7))])
def test_svg_units(size,expected):
    source=b'<svg xmlns="http://www.w3.org/2000/svg" '+size+b'/>'
    assert inspect_svg(source).suggested_size_mm==pytest.approx(expected)


@pytest.mark.parametrize('content,code',[(b'<image href="file:///x.png"/>','SVG_EXTERNAL_RESOURCE'),(b'<style>@import url(https://x)</style>','SVG_EXTERNAL_RESOURCE'),(b'<script/>','SVG_UNSUPPORTED_FEATURE'),(b'<animate/>','SVG_UNSUPPORTED_FEATURE'),(b'<text font-family="NoSuchFont">hello</text>','FONT_MISSING'),(b'<rect onclick="hello()"/>','SVG_UNSUPPORTED_FEATURE')])
def test_svg_rejects_unsafe_or_unresolved_content(content,code):
    data=b'<svg xmlns="http://www.w3.org/2000/svg" width="30mm" height="18mm">'+content+b'</svg>'
    with pytest.raises(ValueError,match=code): inspect_svg(data)


def test_svg_entities_and_bad_source():
    with pytest.raises(ValueError): inspect_svg(b'<!DOCTYPE svg [<!ENTITY a "x">]><svg/>')
    with pytest.raises(ValueError): inspect_svg(b'<svg')


def test_pdf_page_selection_and_physical_size(qapp):
    data=pdf(); info=inspect_pdf(data)
    assert info.page_count==2 and info.suggested_size_mm==pytest.approx((30,18),abs=1e-5)
    selected=inspect_pdf(data,1)
    assert selected.suggested_size_mm==pytest.approx((20,10),abs=1e-5)
    prep=PreparationSettings(20,10)
    frame=render_pdf_page(SourceAsset('x.pdf',data,selected,1),prep,build_grid(prep))
    assert make_burn_mask(frame,prep).burn.all()
    prep=PreparationSettings(30,18)
    frame=render_pdf_page(SourceAsset('x.pdf',data,info,0),prep,build_grid(prep))
    mask=make_burn_mask(frame,prep)
    assert mask.burn[60,60] and not mask.burn[-1,-1]
    with pytest.raises(ValueError,match='PAGE_OUT_OF_RANGE'): inspect_pdf(data,2)
    with pytest.raises(ValueError): inspect_pdf(b'bad pdf')


def test_encrypted_pdf(qapp):
    from pypdf import PdfReader, PdfWriter
    writer=PdfWriter(); writer.append(PdfReader(BytesIO(pdf()))); writer.encrypt('secret')
    stream=BytesIO(); writer.write(stream)
    with pytest.raises(ValueError,match='PDF_PASSWORD_REQUIRED'): inspect_pdf(stream.getvalue())


def test_svg_known_font_is_rendered_without_substitution():
    data=b'<svg xmlns="http://www.w3.org/2000/svg" width="30mm" height="18mm" viewBox="0 0 30 18"><text x="2" y="10" font-family="DejaVu Sans" font-size="6">ABC</text></svg>'
    info=inspect_svg(data); prep=PreparationSettings(30,18)
    frame=render_svg(SourceAsset('text.svg',data,info),prep,build_grid(prep))
    assert make_burn_mask(frame,prep).black_pixel_count > 500


def test_svg_mask_transparency_and_embedded_bitmap():
    import base64
    from PIL import Image
    buffer=BytesIO(); Image.new('1',(2,2),0).save(buffer,format='PNG')
    embedded=base64.b64encode(buffer.getvalue()).decode()
    text='<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm" viewBox="0 0 10 10"><defs><mask id="m"><rect width="10" height="10" fill="white"/><rect x="4" y="4" width="2" height="2" fill="black"/></mask></defs><rect x="2" y="2" width="6" height="6" mask="url(#m)"/><image x="0" y="0" width="1" height="1" href="data:image/png;base64,'+embedded+'"/><rect x="8" y="8" width="1" height="1" fill-opacity="0"/></svg>'
    data=text.encode(); prep=PreparationSettings(10,10)
    mask=make_burn_mask(render_svg(SourceAsset('mask.svg',data,inspect_svg(data)),prep,build_grid(prep)),prep)
    assert mask.burn[10,10] and mask.burn[60,60] and not mask.burn[100,100] and not mask.burn[170,170]


def test_pdf_rotation_and_fractional_padding(qapp):
    from pypdf import PdfReader, PdfWriter
    writer=PdfWriter(); page=PdfReader(BytesIO(pdf())).pages[0]; page.rotate(90); writer.add_page(page)
    stream=BytesIO(); writer.write(stream); data=stream.getvalue()
    info=inspect_pdf(data)
    assert info.suggested_size_mm==pytest.approx((18,30),abs=1e-5)
    prep=PreparationSettings(18,30)
    mask=make_burn_mask(render_pdf_page(SourceAsset('rot.pdf',data,info),prep,build_grid(prep)),prep)
    assert mask.burn[60,260] and not mask.burn[60,60]
    stream=BytesIO(); canvas=Canvas(stream,pagesize=(30.013/25.4*72,18.017/25.4*72)); canvas.rect(0,0,999,999,fill=1,stroke=0); canvas.save(); data=stream.getvalue()
    prep=PreparationSettings(30.013,18.017,invert=True)
    mask=make_burn_mask(render_pdf_page(SourceAsset('fraction.pdf',data,inspect_pdf(data)),prep,build_grid(prep)),prep)
    assert (mask.grid.width_px,mask.grid.height_px)==(601,361)
    assert not mask.burn[-1].any() and not mask.burn[:,-1].any()


def test_native_renderers_unavailable_are_clear_errors(qapp,monkeypatch):
    import builtins
    original=builtins.__import__
    def unavailable(name,*args,**kwargs):
        if name in ('resvg_py','PyQt6.QtPdf'): raise ImportError('not installed')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',unavailable)
    prep=PreparationSettings(30,18)
    with pytest.raises(ValueError,match='SVG_UNAVAILABLE'):
        render_svg(SourceAsset('x.svg',SVG,inspect_svg(SVG)),prep,build_grid(prep))
    with pytest.raises(ValueError,match='PDF_UNAVAILABLE'): inspect_pdf(pdf())


def test_comment_prefixed_svg_is_detected_by_content():
    from mikrocam.importers.visual_source import detect_visual_kind
    data=b'<!-- generated artwork -->\n'+SVG
    assert detect_visual_kind(data)=='svg'
    assert inspect_svg(data).suggested_size_mm==pytest.approx((30,18))


@pytest.mark.parametrize('kind',['svg','pdf'])
def test_non_bitmap_crop_is_explicitly_unsupported(qapp,kind):
    prep=PreparationSettings(30,18,crop_rect=(0,0,10,10))
    data=SVG if kind=='svg' else pdf()
    info=inspect_svg(data) if kind=='svg' else inspect_pdf(data)
    renderer=render_svg if kind=='svg' else render_pdf_page
    with pytest.raises(ValueError,match='CROP_UNSUPPORTED'):
        renderer(SourceAsset('crop.'+kind,data,info),prep,build_grid(prep))
