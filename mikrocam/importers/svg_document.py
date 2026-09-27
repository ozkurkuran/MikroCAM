"""Bounded offline XML/reference traversal into immutable SVG source facts."""
from dataclasses import replace
import hashlib
import re
import xml.etree.ElementTree as ET

from mikrocam.core.svg_models import (SvgDocument, SvgElement, SvgNotice, MAX_SVG_BYTES,
                                     MAX_SVG_ELEMENTS, MAX_SVG_DEPTH, MAX_SVG_REFERENCE_DEPTH)
from mikrocam.core.svg_transform import (compose_affine, parse_svg_transform, parse_svg_length,
                                        resolve_svg_viewport)
from .svg_style import resolve_style, style_paint, style_fill_is_white
from .svg_metadata import resolve_page_attributes
from .svg_css import parse_stylesheets, cascade_attributes
from .svg_clips import SvgClipBuilder


_SVG = 'http://www.w3.org/2000/svg'
_XLINK = '{http://www.w3.org/1999/xlink}href'
_SHAPES = {'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon'}
_METADATA = {'metadata', 'title', 'desc', 'namedview'}


def _tag(node: ET.Element) -> str:
    return node.tag.rsplit('}', 1)[-1]


def _parse_xml(source: bytes) -> ET.Element:
    if type(source) is not bytes or len(source) > MAX_SVG_BYTES:
        raise ValueError('SVG source must be bytes within the source size limit')
    try:
        text = source.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise ValueError('SVG source must use UTF-8 encoding') from error
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('SVG document/entity declarations are unsupported')
    if re.search(r'<\?xml-stylesheet\b', text, re.IGNORECASE):
        raise ValueError('SVG external stylesheet instructions are unsupported')
    declaration = re.match(r'\s*<\?xml\s+[^?]*encoding\s*=\s*[\'"]([^\'"]+)', text)
    if declaration and declaration.group(1).lower() not in ('utf-8', 'utf8', 'us-ascii', 'ascii'):
        raise ValueError('SVG source must declare UTF-8 encoding')
    parser = ET.XMLPullParser(events=('start', 'end'))
    count = depth = 0
    root = None
    try:
        for offset in range(0, len(text), 4096):
            parser.feed(text[offset:offset + 4096])
            for event, node in parser.read_events():
                if event == 'start':
                    count, depth = count + 1, depth + 1
                    if root is None:
                        root = node
                    if count > MAX_SVG_ELEMENTS or depth > MAX_SVG_DEPTH:
                        raise ValueError('SVG element count/depth limit exceeded')
                else:
                    depth -= 1
        parser.close()
    except ET.ParseError as error:
        raise ValueError(f'Invalid SVG XML: {error}') from error
    if root is None or root.tag not in ('svg', f'{{{_SVG}}}svg'):
        raise ValueError('Expected an SVG root element')
    return root


def _id_index(root: ET.Element) -> dict[str, ET.Element]:
    result = {}
    for node in root.iter():
        identifier = node.get('id')
        if identifier is not None:
            if not identifier or len(identifier) > 256 or identifier in result:
                raise ValueError('SVG IDs must be unique nonempty bounded strings')
            result[identifier] = node
    return result


class _Traversal:
    def __init__(self, root: ET.Element) -> None:
        self.ids = _id_index(root)
        self.rules = parse_stylesheets(root)
        self.clip_builder = SvgClipBuilder(root, self.ids, self.rules)
        self.layers: set[tuple[str, ...]] = set()
        self.elements: list[SvgElement] = []
        self.visits = 0

    def walk(self, node: ET.Element, matrix: tuple, parent_style: dict | None,
             references: tuple[str, ...] = (), depth: int = 0, clips: tuple = (),
             layers: tuple[str, ...] = ()) -> None:
        self.visits += 1
        if self.visits > MAX_SVG_ELEMENTS * 4 or depth > MAX_SVG_DEPTH:
            raise ValueError('SVG expanded traversal count/depth limit exceeded')
        kind = _tag(node)
        if kind in _METADATA or kind in ('defs', 'clipPath'):
            return
        if node.tag.startswith('{') and not node.tag.startswith(f'{{{_SVG}}}'):
            raise ValueError(f'Unsupported foreign SVG content: {kind}')
        attributes = cascade_attributes(kind, dict(node.attrib), self.rules)
        style = resolve_style(attributes, parent_style)
        if style['display'] == 'none' or style['opacity'] == '0':
            return
        matrix = compose_affine(matrix, parse_svg_transform(node.get('transform')))
        if style['clip-path'] != 'none':
            if len(clips) >= 8:
                raise ValueError('SVG clip chain exceeds eight applications')
            clips += (self.clip_builder.build(style['clip-path'][5:-1], matrix),)
        if kind == 'g':
            label = node.get('{http://www.inkscape.org/namespaces/inkscape}label',
                             node.get('data-name', node.get('id', '')))
            if label:
                layers += (label,)
            for child in node:
                self.walk(child, matrix, style, references, depth + 1, clips, layers)
        elif kind == 'use':
            self._use(node, matrix, style, references, depth, clips, layers)
        elif kind in _SHAPES:
            if style['visibility'] == 'visible':
                self._shape(node, kind, matrix, style, clips, layers)
            if len(node):
                raise ValueError('Nested content inside an SVG shape is unsupported')
        elif kind == 'style':
            return
        elif kind in ('text', 'tspan'):
            raise ValueError('SVG text requires font layout; convert text to paths in the source editor')
        else:
            raise ValueError(f'Unsupported SVG element: {kind}')

    def _shape(self, node: ET.Element, kind: str, matrix: tuple, style: dict,
               clips: tuple, layers: tuple[str, ...]) -> None:
        if len(self.elements) >= MAX_SVG_ELEMENTS:
            raise ValueError('SVG expanded element limit exceeded')
        name = node.get('id', kind)
        identifier = f'{len(self.elements) + 1}:{name}'[:256]
        self.elements.append(SvgElement(identifier, kind, tuple(node.attrib.items()), matrix,
                                        style_paint(style), style_fill_is_white(style), clips, layers))
        if layers:
            self.layers.add(layers)

    def _use(self, node: ET.Element, matrix: tuple, style: dict,
             references: tuple[str, ...], depth: int, clips: tuple,
             layers: tuple[str, ...]) -> None:
        href = node.get('href', node.get(_XLINK, ''))
        if not href.startswith('#') or len(href) < 2:
            raise ValueError('SVG use requires a local #id reference')
        identifier = href[1:]
        if identifier not in self.ids or identifier in references:
            raise ValueError('Missing or cyclic SVG use reference')
        if len(references) >= MAX_SVG_REFERENCE_DEPTH:
            raise ValueError('SVG reference depth limit exceeded')
        translation = (1., 0., 0., 1., parse_svg_length(node.get('x', '0')),
                       parse_svg_length(node.get('y', '0')))
        self.walk(self.ids[identifier], compose_affine(matrix, translation), style,
                  references + (identifier,), depth + 1, clips, layers)


def parse_svg_document(source: bytes, source_name: str) -> SvgDocument:
    """Resolve a finite source without reading files, loading fonts or following URLs."""
    root = _parse_xml(source)
    effective, page_notices = resolve_page_attributes(root)
    viewport = resolve_svg_viewport(effective)
    traversal = _Traversal(root)
    style = resolve_style(cascade_attributes('svg', dict(root.attrib), traversal.rules))
    # A root SVG transform is outside its viewBox, in viewport CSS-pixel coordinates.
    px_mm = 25.4 / 96
    to_mm = (px_mm, 0., 0., px_mm, 0., 0.)
    to_px = (1 / px_mm, 0., 0., 1 / px_mm, 0., 0.)
    outer = compose_affine(to_mm, compose_affine(parse_svg_transform(root.get('transform')), to_px))
    matrix = compose_affine(outer, viewport.matrix)
    if style['display'] != 'none' and style['opacity'] != '0':
        clips = (() if style['clip-path'] == 'none' else
                 (traversal.clip_builder.build(style['clip-path'][5:-1], matrix),))
        for child in root:
            traversal.walk(child, matrix, style, depth=1, clips=clips)
    notices = (SvgNotice('positive-material', 'Solid colors indicate positive CAM material; color overpainting '
                         'and viewport clipping are not inferred.'),) + page_notices
    # Reserve one omission notice and one later physical-flip notice.
    notices += tuple(SvgNotice('visible-layer', 'Visible source group/layer: ' + ' / '.join(path)[:470])
                     for path in sorted(traversal.layers)[:198 - len(notices)])
    if len(traversal.layers) + len(page_notices) + 1 > 198:
        notices += (SvgNotice('layers-truncated', 'Further source group/layer labels omitted.'),)
    return SvgDocument(source_name, hashlib.sha256(source).hexdigest(),
                        replace(viewport, matrix=matrix), tuple(traversal.elements), notices,
                        tuple(root.attrib.items()), effective)
