"""Strict offline XMP page evidence, preserving original SVG root attributes."""
import math
import xml.etree.ElementTree as ET

from mikrocam.core.svg_models import MAX_SVG_ELEMENTS, SvgNotice, validate_attributes
from mikrocam.core.svg_transform import parse_svg_length, parse_svg_numbers

_PAGE = '{http://ns.adobe.com/xap/1.0/t/pg/}MaxPageSize'
_DIM = '{http://ns.adobe.com/xap/1.0/sType/Dimensions#}'
_FACTORS = {'mm': 1., 'millimeter': 1., 'millimeters': 1.,
            'cm': 10., 'centimeter': 10., 'centimeters': 10.,
            'in': 25.4, 'inch': 25.4, 'inches': 25.4,
            'pt': 25.4 / 72, 'point': 25.4 / 72, 'points': 25.4 / 72,
            'pc': 25.4 / 6, 'pica': 25.4 / 6, 'picas': 25.4 / 6,
            'px': 25.4 / 96, 'pixel': 25.4 / 96, 'pixels': 25.4 / 96}


def _positive(text: str, limit: float = 1e9) -> float:
    if type(text) is not str or len(text) > 128:
        raise ValueError('Page dimension requires bounded numeric text')
    values = parse_svg_numbers(text)
    if len(values) != 1 or not 0 < values[0] <= limit:
        raise ValueError('Page dimension must be one positive finite bounded number')
    return values[0]


def _page(root: ET.Element) -> tuple[float, float] | None:
    pages = []
    for count, node in enumerate(root.iter(), 1):
        if count > MAX_SVG_ELEMENTS:
            raise ValueError('SVG metadata traversal exceeds element budget')
    for metadata in root:
        if metadata.tag not in ('metadata', '{http://www.w3.org/2000/svg}metadata'):
            continue
        pages.extend(node for node in metadata.iter() if node.tag == _PAGE)
    if not pages:
        return None
    if len(pages) != 1:
        raise ValueError('XMP page metadata must contain exactly one MaxPageSize')
    values = {name: [] for name in ('w', 'h', 'unit')}
    for node in pages[0].iter():
        for name in values:
            if _DIM + name in node.attrib:
                values[name].append(node.attrib[_DIM + name])
            if node.tag == _DIM + name:
                if len(node):
                    raise ValueError('XMP dimensions must be simple fields')
                values[name].append(node.text or '')
    if any(len(value) != 1 for value in values.values()):
        raise ValueError('XMP page needs exactly one width, height and unit field')
    if len(values['unit'][0]) > 128:
        raise ValueError('XMP page unit exceeds text budget')
    unit = values['unit'][0].strip().lower()
    if unit not in _FACTORS:
        raise ValueError('XMP page uses an unsupported physical unit')
    dimensions = tuple(_positive(values[name][0], math.inf) * _FACTORS[unit] for name in ('w', 'h'))
    if any(not math.isfinite(value) or not 0 < value <= 1e9 for value in dimensions):
        raise ValueError('XMP page dimensions exceed millimetre bounds')
    return dimensions


def resolve_page_attributes(root: ET.Element) -> tuple[tuple[tuple[str, str], ...], tuple[SvgNotice, ...]]:
    """Use unambiguous XMP only for unavailable axes; explicit dimensions remain primary."""
    if not isinstance(root, ET.Element):
        raise ValueError('SVG page metadata requires an XML element')
    validate_attributes(tuple(root.attrib.items()))
    effective = dict(root.attrib)
    missing, percentages, explicit = [], [], {}
    for axis in ('width', 'height'):
        token = root.get(axis)
        if token is None:
            missing.append(axis)
        elif token.strip().endswith('%'):
            percent = token.strip()
            if len(percent) > 128 or any(character.isspace() for character in percent):
                raise ValueError('SVG percentage dimension must be one bounded numeric token')
            _positive(percent[:-1])
            percentages.append(axis)
        else:
            length = parse_svg_length(token)
            if length <= 0:
                raise ValueError('Explicit SVG page dimensions must be positive')
            explicit[axis] = length * 25.4 / 96
    try:
        page = _page(root)
    except ValueError as error:
        if missing or percentages:
            raise
        return tuple(effective.items()), (SvgNotice('xmp-invalid', f'Unused invalid XMP page metadata: {error}'),)
    if page is None:
        if percentages:
            raise ValueError('Percentage SVG page dimensions require valid XMP MaxPageSize')
        return tuple(effective.items()), ()
    notices = []
    for axis, dimension in zip(('width', 'height'), page):
        if axis in missing or axis in percentages:
            effective[axis] = repr(dimension) + 'mm'
            notices.append(SvgNotice('xmp-page-size', f'SVG {axis} uses XMP page dimension {dimension:g} mm.'))
        elif not math.isclose(explicit[axis], dimension, rel_tol=1e-9, abs_tol=1e-9):
            notices.append(SvgNotice('xmp-conflict', f'Explicit SVG {axis} overrides conflicting XMP page dimension.'))
    return tuple(effective.items()), tuple(notices)
