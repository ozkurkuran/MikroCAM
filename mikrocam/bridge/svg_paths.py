"""Strict bounded SVG syntax adaptation through the existing pinned svg.path parser."""
import math
import re

from svg.path import Arc, Close, CubicBezier, Line, Move, QuadraticBezier, parse_path

from mikrocam.core.svg_curves import flatten_arc, flatten_cubic, flatten_quadratic
from mikrocam.core.svg_models import MAX_ELEMENT_POINTS, SvgElement, SvgPath
from mikrocam.core.svg_paint import primitive_paths


_NUMBER = re.compile(r'[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?')
_FIELDS = {'M': 'nn', 'L': 'nn', 'H': 'n', 'V': 'n', 'C': 'nnnnnn',
           'S': 'nnnn', 'Q': 'nnnn', 'T': 'nn', 'A': 'nnnffnn'}
_SPACE = ' \t\r\n'


def _separator(text: str, index: int, comma: bool) -> int:
    while index < len(text) and text[index] in _SPACE:
        index += 1
    if index < len(text) and text[index] == ',':
        if not comma:
            raise ValueError('Unexpected SVG path comma')
        index += 1
        while index < len(text) and text[index] in _SPACE:
            index += 1
        if index == len(text) or text[index] in ',MmZzLlHhVvCcSsQqTtAa':
            raise ValueError('SVG path comma must separate arguments')
    return index


def _normalized(text: str) -> str:
    """Validate every character and split implicit groups before library allocation."""
    index, count, command = 0, 0, None
    groups = []
    while True:
        index = _separator(text, index, bool(groups) and command is not None)
        if index == len(text):
            break
        if text[index] in 'MmZzLlHhVvCcSsQqTtAa':
            command, index = text[index], index + 1
            if not groups and command not in 'Mm':
                raise ValueError('SVG path must start with moveto')
            if command in 'Zz':
                groups.append(command)
                count += 1
                command = None
                if count > 2 * MAX_ELEMENT_POINTS:
                    raise ValueError('SVG path syntax budget exceeded')
                continue
            index = _separator(text, index, False)
        elif command is None:
            raise ValueError('Expected SVG path command')
        values = []
        for field in _FIELDS[command.upper()]:
            index = _separator(text, index, bool(values))
            if field == 'f':
                if index == len(text) or text[index] not in '01':
                    raise ValueError('SVG arc flags must be zero or one')
                value, index = text[index], index + 1
            else:
                match = _NUMBER.match(text, index)
                if match is None or match.end() - index > 64:
                    raise ValueError('Invalid or oversized SVG path number')
                value, index = match.group(), match.end()
                number = float(value)
                if not math.isfinite(number) or abs(number) > 1e9:
                    raise ValueError('SVG path number exceeds finite bounds')
            count += 1
            if count > 2 * MAX_ELEMENT_POINTS:
                raise ValueError('SVG path syntax budget exceeded')
            values.append(value)
        if command.upper() == 'A' and any(float(value) < 0 for value in values[:2]):
            raise ValueError('SVG arc radii must be nonnegative')
        groups.append(command + ' '.join(values))
        if command in 'Mm':
            command = 'l' if command == 'm' else 'L'
    return ' '.join(groups)


def _point(value: complex) -> tuple[float, float]:
    point = (value.real, value.imag)
    if any(not math.isfinite(number) or abs(number) > 1e9 for number in point):
        raise ValueError('SVG relative coordinates exceed finite bounds')
    return point


def _segment_points(segment: object, tolerance: float) -> tuple[tuple[float, float], ...]:
    start, end = _point(segment.start), _point(segment.end)
    if isinstance(segment, (Line, Close)):
        return start, end
    if isinstance(segment, CubicBezier):
        return flatten_cubic(start, _point(segment.control1), _point(segment.control2), end, tolerance)
    if isinstance(segment, QuadraticBezier):
        return flatten_quadratic(start, _point(segment.control), end, tolerance)
    if isinstance(segment, Arc):
        if start == end:
            return (start,)
        if segment.radius.real == 0 or segment.radius.imag == 0:
            return start, end
        radius = segment.radius * segment.radius_scale
        return flatten_arc(_point(segment.center), _point(radius), segment.rotation,
                           segment.theta, segment.delta, start, end, tolerance)
    raise ValueError('Unsupported SVG path component')


def _paths(segments: object, tolerance: float) -> tuple[SvgPath, ...]:
    paths, points, count = [], [], 0
    for segment in segments:
        if isinstance(segment, Move):
            if len(points) >= 2:
                paths.append(SvgPath(tuple(points)))
            points = [_point(segment.end)]
            count += 1
        else:
            vertices = _segment_points(segment, tolerance)
            if not points:
                points = [vertices[0]]
                count += 1
            count += len(vertices) - 1
            if count > MAX_ELEMENT_POINTS:
                raise ValueError('SVG element point budget exceeded')
            points.extend(vertices[1:])
            if isinstance(segment, Close):
                if len(points) < 4:
                    raise ValueError('Degenerate closed SVG subpath is unsupported')
                paths.append(SvgPath(tuple(points), True))
                points = []
        if count > MAX_ELEMENT_POINTS:
            raise ValueError('SVG element point budget exceeded')
    if len(points) >= 2:
        paths.append(SvgPath(tuple(points)))
    return tuple(paths)


def element_paths(element: SvgElement, tolerance_local: float) -> tuple[SvgPath, ...]:
    """Return bounded local paths; transforms and material policy remain in the core."""
    if type(element) is not SvgElement:
        raise ValueError('SVG path adapter requires an immutable element')
    if type(tolerance_local) not in (float, int) or not 0 < tolerance_local <= 1e9:
        raise ValueError('SVG local tolerance must be positive and finite')
    if element.kind != 'path':
        return primitive_paths(element.kind, element.attributes, tolerance_local)
    normalized = _normalized(dict(element.attributes).get('d', ''))
    try:
        segments = parse_path(normalized)
    except (ValueError, AssertionError, IndexError, OverflowError, ZeroDivisionError) as error:
        raise ValueError('Invalid SVG path syntax or unsupported arc precision') from error
    return _paths(segments, tolerance_local)
