"""Finite local clip definitions with definition-owned presentation inheritance."""
import xml.etree.ElementTree as ET

from mikrocam.core.svg_models import SvgClip, SvgElement, SvgPaint, MAX_SVG_ELEMENTS, MAX_SVG_REFERENCE_DEPTH
from mikrocam.core.svg_transform import compose_affine, parse_svg_length, parse_svg_numbers, parse_svg_transform
from .svg_css import SvgCssRule, cascade_attributes
from .svg_style import resolve_style

_SHAPES = {'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon'}
_SVG = 'http://www.w3.org/2000/svg'


def _bbox_length(value: str) -> float:
    token = value.strip()
    if len(token) > 128:
        raise ValueError('SVG bounding-box clip length exceeds numeric budget')
    numbers = parse_svg_numbers(token[:-1] if token.endswith('%') else token)
    if len(numbers) != 1 or abs(numbers[0]) > 1e9:
        raise ValueError('SVG bounding-box clip lengths require finite unitless numbers or percentages')
    return numbers[0] / 100 if token.endswith('%') else numbers[0]


def clip_shape_attributes(element: SvgElement, units: str) -> tuple[tuple[str, str], ...]:
    """Normalize bbox lengths for decoding while retaining the element's original attributes."""
    if units == 'userSpaceOnUse':
        return element.attributes
    if units != 'objectBoundingBox':
        raise ValueError('Unsupported SVG clipping units')
    lengths = {'x', 'y', 'width', 'height', 'cx', 'cy', 'r', 'rx', 'ry', 'x1', 'x2', 'y1', 'y2'}
    return tuple((key, repr(_bbox_length(value)) if key in lengths else value)
                 for key, value in element.attributes)


class SvgClipBuilder:
    def __init__(self, root: ET.Element, ids: dict[str, ET.Element], rules: tuple[SvgCssRule, ...]) -> None:
        self.ids, self.rules = ids, rules
        self.parents = {child: parent for parent in root.iter() for child in parent}
        self.visits = 0
        self.applications = 0

    def _style(self, node: ET.Element, parent: dict | None) -> dict[str, str]:
        kind = node.tag.rsplit('}', 1)[-1]
        return resolve_style(cascade_attributes(kind, dict(node.attrib), self.rules), parent, clip_mode=True)

    def build(self, identifier: str, matrix: tuple) -> SvgClip:
        node = self.ids.get(identifier)
        if node is None or node.tag not in ('clipPath', f'{{{_SVG}}}clipPath'):
            raise ValueError('SVG clip reference must resolve to a local clipPath')
        self.applications += 1
        if self.applications > MAX_SVG_ELEMENTS:
            raise ValueError('SVG clip application budget exceeded')
        ancestors, parent = [], self.parents.get(node)
        while parent is not None:
            ancestors.append(parent)
            parent = self.parents.get(parent)
        style = None
        for ancestor in reversed(ancestors):
            style = self._style(ancestor, style)
        style = self._style(node, style)
        if style['clip-path'] != 'none':
            raise ValueError('Nested clipping inside a clip definition is unsupported')
        elements = []
        units = node.get('clipPathUnits', 'userSpaceOnUse')
        if units not in ('userSpaceOnUse', 'objectBoundingBox'):
            raise ValueError('Unsupported SVG clipping units')
        local = parse_svg_transform(node.get('transform'))
        if style['display'] != 'none':
            for child in node:
                self._walk(child, local, style, (identifier,), elements, units)
        return SvgClip(f'clip-{self.applications}', identifier,
                       units, matrix, tuple(elements))

    def _walk(self, node: ET.Element, matrix: tuple, parent_style: dict,
              references: tuple[str, ...], elements: list[SvgElement], units: str) -> None:
        self.visits += 1
        if self.visits > MAX_SVG_ELEMENTS * 4:
            raise ValueError('SVG expanded clip traversal budget exceeded')
        kind = node.tag.rsplit('}', 1)[-1]
        if kind in ('title', 'desc', 'metadata'):
            return
        if node.tag.startswith('{') and not node.tag.startswith(f'{{{_SVG}}}'):
            raise ValueError('Unsupported foreign SVG clip content')
        style = self._style(node, parent_style)
        if style['clip-path'] != 'none':
            raise ValueError('Nested clipping inside a clip definition is unsupported')
        if style['display'] == 'none':
            return
        matrix = compose_affine(matrix, parse_svg_transform(node.get('transform')))
        if kind == 'use':
            self._use(node, matrix, style, references, elements, units)
            return
        if kind not in _SHAPES or len(node):
            raise ValueError('SVG clip definitions support basic shapes and local shape use only')
        if style['visibility'] != 'visible':
            return
        if len(elements) >= 64:
            raise ValueError('SVG clip definition exceeds 64 shapes')
        identifier = f'{len(elements) + 1}:{node.get("id", kind)}'[:256]
        elements.append(SvgElement(identifier, kind, tuple(node.attrib.items()), matrix,
                                   SvgPaint(fill=True, stroke=False, fill_rule=style['clip-rule'])))

    def _use(self, node: ET.Element, matrix: tuple, style: dict,
             references: tuple[str, ...], elements: list[SvgElement], units: str) -> None:
        href = node.get('href', node.get('{http://www.w3.org/1999/xlink}href', ''))
        if not href.startswith('#') or len(href) < 2 or href[1:] not in self.ids:
            raise ValueError('SVG clip use requires an existing local shape reference')
        identifier = href[1:]
        if identifier in references or len(references) >= MAX_SVG_REFERENCE_DEPTH:
            raise ValueError('Cyclic or excessive SVG clip shape reference')
        if len(node):
            raise ValueError('Nested content in SVG clip use is unsupported')
        length = _bbox_length if units == 'objectBoundingBox' else parse_svg_length
        translation = (1., 0., 0., 1., length(node.get('x', '0')), length(node.get('y', '0')))
        self._walk(self.ids[identifier], compose_affine(matrix, translation), style,
                   references + (identifier,), elements, units)
