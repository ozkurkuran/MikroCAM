"""Renderer tolerance is distinct from exact interlace reconstruction."""
from io import BytesIO
import numpy as np
from PIL import Image
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
from mikrocam.core.visual import PreparationSettings,SourceAsset,build_grid
from mikrocam.core.visual_normalize import make_burn_mask
from mikrocam.core.visual_interlace import materialize_group
from mikrocam.bridge.visual_bitmap import inspect_bitmap,render_bitmap
from mikrocam.bridge.visual_svg import inspect_svg,render_svg
from mikrocam.ui.visual_pdf import inspect_pdf,render_pdf_page


def test_same_rectangle_has_common_physical_grid_and_exact_split(qapp):
    prep=PreparationSettings(30,18);grid=build_grid(prep)
    image=Image.new('1',(600,360),1)
    for row in range(40,140):
        for column in range(40,140):image.putpixel((column,row),0)
    stream=BytesIO();image.save(stream,format='PNG');png=stream.getvalue()
    svg=b'<svg xmlns="http://www.w3.org/2000/svg" width="30mm" height="18mm" viewBox="0 0 30 18"><rect x="2" y="2" width="5" height="5"/></svg>'
    stream=BytesIO();canvas=Canvas(stream,pagesize=(30*72/25.4,18*72/25.4))
    canvas.rect(2*72/25.4,11*72/25.4,5*72/25.4,5*72/25.4,fill=1,stroke=0);canvas.save();pdf=stream.getvalue()
    masks=[]
    for name,data,inspect,render in [('x.png',png,inspect_bitmap,render_bitmap),('x.svg',svg,inspect_svg,render_svg),('x.pdf',pdf,inspect_pdf,render_pdf_page)]:
        mask=make_burn_mask(render(SourceAsset(name,data,inspect(data)),prep,grid),prep);masks.append(mask)
        assert mask.grid==grid and mask.burn[60,60] and not mask.burn[10,10]
        # Only renderer boundary antialiasing may differ (one pixel perimeter).
        assert np.count_nonzero(mask.burn!=masks[0].burn)<=400
        for count in range(1,9):
            total=sum((materialize_group(mask,k,count).burn.astype(np.uint16) for k in range(count)))
            assert np.array_equal(total,mask.burn)


def test_pdf_embedded_bitmap_and_vector_share_the_selected_page(qapp):
    stream=BytesIO();canvas=Canvas(stream,pagesize=(30*72/25.4,18*72/25.4))
    image=Image.new('RGB',(8,8),'black')
    canvas.drawImage(ImageReader(image),2*72/25.4,11*72/25.4,5*72/25.4,5*72/25.4)
    canvas.rect(15*72/25.4,11*72/25.4,5*72/25.4,5*72/25.4,fill=1,stroke=0);canvas.save();data=stream.getvalue()
    prep=PreparationSettings(30,18)
    mask=make_burn_mask(render_pdf_page(SourceAsset('mixed.pdf',data,inspect_pdf(data)),prep,build_grid(prep)),prep)
    assert mask.burn[60,60] and mask.burn[60,320] and not mask.burn[60,220]
