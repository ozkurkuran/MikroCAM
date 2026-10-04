"""Bounded SVG producer metadata inspection without loading external resources."""
import re
from xml.etree import ElementTree as ET

from mikrocam.core.cad_source import CadSourceEvidence, MAX_CAD_SOURCE_BYTES
from .svg_doctype import strip_svg_doctype
from .cad_producer import classify_producer, desc_declaration, is_inkscape_version, producer_declaration


MAX_XML_ELEMENTS = 10000
MAX_XML_DEPTH = 64
_SVG = 'http://www.w3.org/2000/svg'
_INK_VERSION = '{http://www.inkscape.org/namespaces/inkscape}version'
_CREATOR = '{http://ns.adobe.com/xap/1.0/}CreatorTool'


def _text(source: bytes) -> str:
    if type(source) is not bytes or len(source) > MAX_CAD_SOURCE_BYTES:
        raise ValueError('SVG producer inspection exceeds byte limit')
    try:
        text = source.decode('utf-8-sig')
    except UnicodeError as error:
        raise ValueError('SVG producer inspection requires UTF-8') from error
    declaration = re.match(r'''\s*<\?xml\s+[^?]*encoding\s*=\s*["']([^"']+)''', text)
    if declaration and declaration[1].lower() not in ('utf-8', 'utf8', 'us-ascii', 'ascii'):
        raise ValueError('SVG producer inspection requires UTF-8 declaration')
    return strip_svg_doctype(text)  # Shared offline SVG 1.0/1.1 allowlist (spec 041).


def _parse(source: bytes) -> tuple[ET.Element, tuple[tuple[str, ET.Element], ...]]:
    text = _text(source)
    parser = ET.XMLPullParser(events=('start', 'end', 'comment'))
    root, depth, count, ended = None, 0, 0, False
    candidates = []
    try:
        for offset in range(0, len(text), 4096):
            parser.feed(text[offset:offset + 4096])
            for event, node in parser.read_events():
                if event == 'start':
                    count, depth = count + 1, depth + 1
                    if count > MAX_XML_ELEMENTS or depth > MAX_XML_DEPTH:
                        raise ValueError('SVG producer XML element/depth limit exceeded')
                    if root is None:
                        root = node
                        candidates.append(('root', node))
                elif event == 'end':
                    if depth == 2 and node.tag in ('metadata', f'{{{_SVG}}}metadata',
                                                  'desc', f'{{{_SVG}}}desc'):
                        candidates.append(('node', node))
                    depth -= 1
                    ended = ended or depth == 0
                elif not ended and depth <= 1:
                    candidates.append(('comment', node))
                    if len(candidates) > MAX_XML_ELEMENTS:
                        raise ValueError('SVG producer comment limit exceeded')
        parser.close()
    except ET.ParseError as error:
        raise ValueError('Malformed SVG producer metadata') from error
    if root is None or root.tag not in ('svg', f'{{{_SVG}}}svg'):
        raise ValueError('SVG producer metadata requires an SVG root')
    return root, tuple(candidates)


def _evidence(records: list[CadSourceEvidence], field: str, value: str,
              producer: str | None = None) -> None:
    record = CadSourceEvidence(classify_producer(value if producer is None else producer), field, value)
    if record not in records:
        if len(records) >= 32:
            raise ValueError('SVG producer evidence limit exceeded')
        records.append(record)


def _metadata(node: ET.Element, records: list[CadSourceEvidence]) -> None:
    pending = [node]
    while pending:
        child = pending.pop()
        if child is not node and child.tag.rsplit('}', 1)[-1] == 'metadata':
            continue  # A nested metadata section has its own provenance context.
        pending.extend(reversed(child))
        if _CREATOR in child.attrib:
            _evidence(records, 'svg.xmp.CreatorTool', child.attrib[_CREATOR])
        if child.tag == _CREATOR:
            if len(child):
                raise ValueError('SVG CreatorTool requires a simple text value')
            _evidence(records, 'svg.xmp.CreatorTool', child.text or '')


def svg_source_evidence(source: bytes) -> tuple[CadSourceEvidence, ...]:
    """Extract actual fields; a namespace, page dimension or filename is never a producer."""
    root, candidates = _parse(source)
    records = []
    for kind, child in candidates:
        if kind == 'root':
            version = root.get(_INK_VERSION)
            if version is not None:
                if not is_inkscape_version(version):
                    raise ValueError('SVG Inkscape version metadata is malformed')
                _evidence(records, 'svg.inkscape.version', version, 'Inkscape')
        elif child.tag in ('metadata', f'{{{_SVG}}}metadata'):
            _metadata(child, records)
        elif kind == 'comment' or not len(child):
            value = child.text or ''
            producer = producer_declaration(value) if kind == 'comment' else desc_declaration(value)
            if producer is not None:
                field = 'svg.generator-comment' if kind == 'comment' else 'svg.desc'
                _evidence(records, field, value, producer)
    return tuple(records)
