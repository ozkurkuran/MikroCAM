"""Geometry-only millimetre SVG with an explicit local Y-down frame."""
import math
import xml.etree.ElementTree as ET

from .laser_paths import CancelCheck, LaserPath, check_cancelled, check_path_count
from .placement import _finite_real


def _bounds(value: tuple[float, float, float, float]) -> tuple[float, ...]:
    try:
        result = tuple(_finite_real(number, 'export bound') for number in value)
    except TypeError as error:
        raise ValueError('Export bounds require four finite numbers') from error
    if len(result) != 4:
        raise ValueError('Export bounds require four finite numbers')
    width, height = result[2]-result[0], result[3]-result[1]
    if any(not math.isfinite(extent) or extent < 0 for extent in (width, height)):
        raise ValueError('Export extents must be finite and nonnegative')
    return result


def _title(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError('SVG pass name must be nonempty text')
    if any(not (ord(char) in (9, 10, 13) or 32 <= ord(char) <= 0xD7FF
                or 0xE000 <= ord(char) <= 0xFFFD or 0x10000 <= ord(char) <= 0x10FFFF) for char in text):
        raise ValueError('SVG pass name contains unsupported XML characters')
    return text


def svg_document(paths: tuple[LaserPath, ...], bounds: tuple[float, float, float, float],
                  pass_name: str, cancelled: CancelCheck = None) -> str:
    """Serialize placed paths without applying Placement or adding registration marks."""
    if not isinstance(paths, tuple) or not paths:
        raise ValueError('SVG requires a nonempty tuple of laser paths')
    check_path_count(len(paths))
    xmin, ymin, xmax, ymax = _bounds(bounds)
    width, height = xmax-xmin or 1.0, ymax-ymin or 1.0
    root = ET.Element('svg', {'xmlns': 'http://www.w3.org/2000/svg', 'version': '1.1',
                             'width': f'{width:.17g}mm', 'height': f'{height:.17g}mm',
                             'viewBox': f'0 0 {width:.17g} {height:.17g}'})
    ET.SubElement(root, 'title').text = _title(pass_name)
    for path in paths:
        check_cancelled(cancelled)
        if not isinstance(path, LaserPath):
            raise ValueError('SVG paths must be LaserPath values')
        if any(not (xmin <= x <= xmax and ymin <= y <= ymax) for x, y in path.points):
            raise ValueError('SVG bounds must cover every placed path')
        points = ' '.join(f'{x-xmin:.17g},{ymax-y:.17g}' for x, y in path.points)
        ET.SubElement(root, 'polyline', {'points': points, 'fill': 'none', 'stroke': '#000000',
                                       'stroke-width': '0.01'})
    check_cancelled(cancelled)
    return ET.tostring(root, encoding='unicode', xml_declaration=True)
