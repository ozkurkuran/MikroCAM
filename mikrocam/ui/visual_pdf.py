"""Lazy QtPdf boundary; each native document lives in its creating worker thread."""
from contextlib import contextmanager
from collections.abc import Iterator
from mikrocam.core.visual import MAX_SOURCE_BYTES, RasterFrame, RasterGrid, SourceAsset, SourceInfo, PreparationSettings


@contextmanager
def pdf_document(data: bytes) -> Iterator[object]:
    if type(data) is not bytes or not 1 <= len(data) <= MAX_SOURCE_BYTES or not data.startswith(b'%PDF-'):
        raise ValueError('SOURCE_DECODE_FAILED: invalid PDF source')
    try:
        from PyQt6 import QtCore
        from PyQt6.QtPdf import QPdfDocument
    except ImportError as error: raise ValueError('PDF_UNAVAILABLE') from error
    buffer = QtCore.QBuffer()
    buffer.setData(QtCore.QByteArray(data))
    buffer.open(QtCore.QIODevice.OpenModeFlag.ReadOnly)
    document = QPdfDocument(None)
    try:
        document.load(buffer)
        if document.error() in (QPdfDocument.Error.IncorrectPassword, QPdfDocument.Error.UnsupportedSecurityScheme):
            raise ValueError('PDF_PASSWORD_REQUIRED')
        if document.status() != QPdfDocument.Status.Ready or not 1 <= document.pageCount() <= 128:
            raise ValueError('SOURCE_DECODE_FAILED: invalid PDF or more than 128 pages')
        yield document
    finally:
        document.close()
        buffer.close()


def inspect_pdf(data: bytes, page_index: int = 0) -> SourceInfo:
    with pdf_document(data) as document:
        if type(page_index) is not int or not 0 <= page_index < document.pageCount(): raise ValueError('PAGE_OUT_OF_RANGE')
        size = document.pagePointSize(page_index)
        return SourceInfo('pdf', 'application/pdf', document.pageCount(),
                          suggested_size_mm=(size.width() * 25.4/72, size.height() * 25.4/72), size_origin='document')


def render_pdf_page(source: SourceAsset, preparation: PreparationSettings, grid: RasterGrid) -> RasterFrame:
    if preparation.crop_rect is not None: raise ValueError('CROP_UNSUPPORTED')
    import numpy as np
    from PIL import Image
    from PyQt6 import QtCore, QtGui
    from mikrocam.bridge.visual_bitmap import sample_image
    with pdf_document(source.data) as document:
        if not 0 <= source.page_index < document.pageCount(): raise ValueError('PAGE_OUT_OF_RANGE')
        width, height = (grid.height_px, grid.width_px) if preparation.quarter_turns % 2 else (grid.width_px, grid.height_px)
        rendered = document.render(source.page_index, QtCore.QSize(width, height))
        if rendered.isNull(): raise ValueError('SOURCE_DECODE_FAILED: PDF render failed')
        rgba = rendered.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
        bits = rgba.constBits()
        bits.setsize(rgba.bytesPerLine() * rgba.height())
        array = np.frombuffer(bits, dtype=np.uint8).reshape(rgba.height(), rgba.bytesPerLine())
        array = array[:, :rgba.width() * 4].reshape(rgba.height(), rgba.width(), 4).copy()
        return sample_image(Image.fromarray(array), preparation, grid)
