"""Offline static SVG appearance renderer; external resources never reach resvg."""
from base64 import b64decode
from io import BytesIO
import math
import re
from xml.etree import ElementTree as ET
from mikrocam.core.visual import MAX_SOURCE_BYTES, SourceInfo, SourceAsset, RasterFrame, RasterGrid, PreparationSettings
from .visual_bitmap import inspect_bitmap, sample_image
from .visual_fonts import svg_font_options

SVG_NS = 'http://www.w3.org/2000/svg'
DYNAMIC = {'script', 'animate', 'animateMotion', 'animateTransform', 'set', 'foreignObject', 'discard'}
LENGTH = re.compile(r'^\s*([+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)\s*(mm|cm|in|pt|pc|px)?\s*$')


def _length(value: str | None) -> float | None:
    if value is None or value.endswith('%'): return None
    match = LENGTH.fullmatch(value)
    if match is None: raise ValueError('SVG_UNSUPPORTED_FEATURE: invalid document length')
    number = float(match[1])
    if not math.isfinite(number) or number <= 0: raise ValueError('INVALID_GRID: SVG size')
    return number * {'mm': 1, 'cm': 10, 'in': 25.4, 'pt': 25.4/72, 'pc': 25.4/6, 'px': 25.4/96, None: 25.4/96}[match[2]]


def _resource(value: str) -> None:
    value = value.strip()
    if value.startswith('#') and len(value) > 1: return
    match = re.fullmatch(r'data:(image/(?:png|jpeg|gif|webp));base64,([A-Za-z0-9+/=\s]+)', value)
    if not match or len(match[2]) > 4 * ((MAX_SOURCE_BYTES + 2)//3): raise ValueError('SVG_EXTERNAL_RESOURCE')
    try:
        data = b64decode(re.sub(r'\s+', '', match[2]), validate=True)
        info = inspect_bitmap(data)
        if info.media_type != match[1]: raise ValueError('SVG_EXTERNAL_RESOURCE: embedded image media mismatch')
    except ValueError as error:
        raise ValueError(f'SVG_EXTERNAL_RESOURCE: invalid embedded image: {error}') from error


def _css(value: str) -> None:
    if re.search(r'@import|@font-face|expression\s*\(', value, re.I) or '\\' in value:
        raise ValueError('SVG_EXTERNAL_RESOURCE: external or escaped CSS')
    for match in re.finditer(r'url\s*\((.*?)\)', value, re.I | re.S):
        reference = match[1].strip().strip('"').strip("'")
        _resource(reference)


def validated_svg(data: bytes) -> ET.Element:
    if type(data) is not bytes or not 1 <= len(data) <= MAX_SOURCE_BYTES: raise ValueError('SOURCE_TOO_LARGE')
    try: text = data.decode('utf-8-sig')
    except UnicodeError as error: raise ValueError('SOURCE_DECODE_FAILED: SVG requires UTF-8') from error
    if re.search(r'<!DOCTYPE|<!ENTITY|<\?xml-stylesheet', text, re.I): raise ValueError('SVG_EXTERNAL_RESOURCE: DTD/entity/stylesheet')
    try: root = ET.fromstring(text)
    except ET.ParseError as error: raise ValueError(f'SOURCE_DECODE_FAILED: {error}') from error
    if root.tag not in ('svg', '{' + SVG_NS + '}svg'): raise ValueError('UNSUPPORTED_SOURCE_FORMAT')
    for node in root.iter():
        tag = node.tag.rsplit('}', 1)[-1]
        if tag in DYNAMIC: raise ValueError('SVG_UNSUPPORTED_FEATURE: ' + tag)
        if tag == 'style': _css(node.text or '')
        for key, value in node.attrib.items():
            local = key.rsplit('}', 1)[-1]
            if local.lower().startswith('on'): raise ValueError('SVG_UNSUPPORTED_FEATURE: event handler')
            if key == '{http://www.w3.org/XML/1998/namespace}base': raise ValueError('SVG_EXTERNAL_RESOURCE: xml:base')
            if local == 'href': _resource(value)
            _css(value)
    svg_font_options(root)
    return root


def inspect_svg(data: bytes) -> SourceInfo:
    root = validated_svg(data)
    width, height = _length(root.get('width')), _length(root.get('height'))
    viewbox = root.get('viewBox')
    box = None
    if viewbox is not None:
        try: box = tuple(float(x) for x in re.split(r'[\s,]+', viewbox.strip()))
        except ValueError as error: raise ValueError('INVALID_GRID: viewBox') from error
        if len(box) != 4 or any(not math.isfinite(x) for x in box) or min(box[2:]) <= 0:
            raise ValueError('INVALID_GRID: viewBox')
    if width is None or height is None:
        if box is None: raise ValueError('INVALID_GRID: SVG requires dimensions or viewBox')
        if width is None and height is None: width, height = box[2] * 25.4/96, box[3] * 25.4/96
        elif width is None: width = height * box[2]/box[3]
        else: height = width * box[3]/box[2]
    return SourceInfo('svg', 'image/svg+xml', suggested_size_mm=(width, height), size_origin='document')


def render_svg(source: SourceAsset, preparation: PreparationSettings, grid: RasterGrid) -> RasterFrame:
    if preparation.crop_rect is not None: raise ValueError('CROP_UNSUPPORTED')
    root = validated_svg(source.data)
    try: import resvg_py
    except ImportError as error: raise ValueError('SVG_UNAVAILABLE: install requirements-visual.txt') from error
    from PIL import Image
    # The common sampler applies quarter turns and fractional physical padding once.
    width, height = (grid.height_px, grid.width_px) if preparation.quarter_turns % 2 else (grid.width_px, grid.height_px)
    if max(width, height) > 32767: raise ValueError('RASTER_LIMIT_EXCEEDED: SVG renderer dimension')
    rendered = resvg_py.svg_to_bytes(svg_string=source.data.decode('utf-8-sig'),
                                     width=width, height=height, dpi=96.0, **svg_font_options(root))
    with Image.open(BytesIO(rendered)) as image:
        return sample_image(image, preparation, grid)
