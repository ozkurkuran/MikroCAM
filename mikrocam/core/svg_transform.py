"""Strict SVG source lengths and affine viewport mapping, independent of machine Placement."""
import math
import re
from .placement import Affine2D, Point2D
from .svg_models import MAX_ELEMENT_POINTS, SvgNotice, SvgViewport, _point, validate_affine, validate_attributes
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
_NUMBER = '[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?'
_TOKEN = re.compile(_NUMBER)
_SEPARATOR = re.compile(r'(?:\s*,\s*|\s+)')
_UNITS = {'': 1.0, 'px': 1.0, 'mm': 96.0 / 25.4, 'cm': 960.0 / 25.4, 'in': 96.0, 'pt': 96.0 / 72, 'pc': 16.0}

def _numeric(text: str) -> float:
    if len(text) > 64:
        raise ValueError('SVG numeric token exceeds 64 characters')
    value = float(text)
    if not math.isfinite(value):
        raise ValueError('SVG number must be finite')
    return value

def parse_svg_length(text: str) -> float:
    if type(text) is not str:
        raise ValueError('SVG length must be text')
    match = re.fullmatch(f'({_NUMBER})(px|mm|cm|in|pt|pc)?', text.strip())
    if match is None:
        raise ValueError('SVG length requires a complete number and supported absolute unit')
    value = _numeric(match[1]) * _UNITS[match[2] or '']
    if not math.isfinite(value) or abs(value) > 1000000000.0:
        raise ValueError('SVG local length exceeds supported magnitude')
    return value

def parse_svg_numbers(text: str) -> tuple[float, ...]:
    if type(text) is not str:
        raise ValueError('SVG number list must be text')
    text = text.strip()
    if not text:
        return ()
    values, offset = ([], 0)
    while offset < len(text):
        if len(values) >= 2 * MAX_ELEMENT_POINTS:
            raise ValueError('SVG number list exceeds element point budget')
        match = _TOKEN.match(text, offset)
        if match is None:
            raise ValueError('Malformed SVG number list')
        values.append(_numeric(match[0]))
        offset = match.end()
        if offset == len(text):
            break
        separator = _SEPARATOR.match(text, offset)
        if separator is None:
            raise ValueError('SVG numbers require comma or whitespace separation')
        offset = separator.end()
        if offset == len(text):
            raise ValueError('SVG number list has trailing separator')
    return tuple(values)

def compose_affine(outer: Affine2D, inner: Affine2D) -> Affine2D:
    validate_affine(outer)
    validate_affine(inner)
    a, b, d, e, x, y = outer
    p, q, r, s, u, v = inner
    result = (a * p + b * r, a * q + b * s, d * p + e * r, d * q + e * s, a * u + b * v + x, d * u + e * v + y)
    validate_affine(result)
    return result

def apply_svg_point(matrix: Affine2D, point: Point2D) -> Point2D:
    validate_affine(matrix)
    x, y = _point(point)
    a, b, d, e, u, v = matrix
    return _point((a * x + b * y + u, d * x + e * y + v))

def affine_scale_bound(matrix: Affine2D) -> float:
    validate_affine(matrix)
    return math.hypot(*matrix[:4])

def non_scaling_stroke_width(width_px: float, matrix: Affine2D) -> float:
    """Map a root-viewport CSS-pixel stroke width to user units through a similarity user->mm matrix.

    Stroking a similarity-mapped path in user space with the returned width equals stroking the
    mapped path in the physical frame with width_px * 25.4/96 mm (SVG non-scaling-stroke at zoom 1).
    """
    validate_affine(matrix)
    if type(width_px) not in (int, float) or not math.isfinite(width_px) or width_px < 0:
        raise ValueError('Non-scaling stroke width must be a finite nonnegative number')
    a, b, d, e = matrix[:4]
    first, second = math.hypot(a, d), math.hypot(b, e)
    if (not math.isclose(first, second, rel_tol=1e-9)
            or abs(a * b + d * e) > first * second * 1e-9):
        raise ValueError('SVG non-scaling-stroke under non-uniform scale or skew is ambiguous for '
                         'CAM; use a uniform transform or outline the stroke in the source editor')
    return width_px * 25.4 / 96 / ((first + second) / 2)

def _operation(name: str, values: tuple[float, ...]) -> Affine2D:
    if name == 'translate' and len(values) in (1, 2):
        result = (1.0, 0.0, 0.0, 1.0, values[0], values[1] if len(values) == 2 else 0.0)
    elif name == 'scale' and len(values) in (1, 2):
        result = (values[0], 0.0, 0.0, values[-1], 0.0, 0.0)
    elif name == 'matrix' and len(values) == 6:
        a, b, c, d, e, f = values
        result = (a, c, b, d, e, f)
    elif name == 'rotate' and len(values) in (1, 3):
        angle = math.radians(math.remainder(values[0], 360.0))
        c, s = (math.cos(angle), math.sin(angle))
        x, y = values[1:] if len(values) == 3 else (0.0, 0.0)
        result = (c, -s, s, c, x - c * x + s * y, y - s * x - c * y)
    elif name in ('skewX', 'skewY') and len(values) == 1:
        angle = math.remainder(values[0], 180.0)
        if abs(angle) == 90:
            raise ValueError('SVG skew is undefined at 90 degrees')
        tangent = math.tan(math.radians(angle))
        result = (1.0, tangent if name == 'skewX' else 0.0, tangent if name == 'skewY' else 0.0, 1.0, 0.0, 0.0)
    else:
        raise ValueError('Unsupported SVG transform or argument count')
    validate_affine(result)
    return result

def parse_svg_transform(text: str | None) -> Affine2D:
    if text is None:
        return IDENTITY
    if type(text) is not str or len(text) > 4096:
        raise ValueError('SVG transform must be text within 4096 characters')
    remaining, result, count = (text.strip(), IDENTITY, 0)
    while remaining:
        match = re.match('([A-Za-z]+)\\s*\\(([^()]*)\\)', remaining)
        if match is None or count >= 128:
            raise ValueError('Malformed or oversized SVG transform list')
        result = compose_affine(result, _operation(match[1], parse_svg_numbers(match[2])))
        count += 1
        remaining = remaining[match.end():].lstrip()
        if remaining.startswith(','):
            remaining = remaining[1:].lstrip()
            if not remaining:
                raise ValueError('SVG transform list has trailing separator')
    return result

def resolve_svg_viewport(attributes: tuple[tuple[str, str], ...]) -> SvgViewport:
    validate_attributes(attributes)
    attrs = dict(attributes)
    viewbox = parse_svg_numbers(attrs['viewBox']) if 'viewBox' in attrs else None
    if viewbox is not None and (len(viewbox) != 4 or viewbox[2] <= 0 or viewbox[3] <= 0 or any((abs(v) > 1000000000.0 for v in viewbox))):
        raise ValueError('SVG viewBox requires finite origin and positive bounded dimensions')
    width = parse_svg_length(attrs['width']) if 'width' in attrs else None
    height = parse_svg_length(attrs['height']) if 'height' in attrs else None
    inferred = width is None or height is None
    if inferred:
        if viewbox is None:
            raise ValueError('SVG root requires both dimensions or a viewBox for inference')
        if width is height is None:
            width, height = viewbox[2:]
        elif width is None:
            width = height * viewbox[2] / viewbox[3]
        else:
            height = width * viewbox[3] / viewbox[2]
    if width <= 0 or height <= 0:
        raise ValueError('SVG viewport dimensions must be positive')
    aspect = attrs.get('preserveAspectRatio', 'xMidYMid meet').split()
    alignments = {x + y: (i / 2, j / 2) for i, x in enumerate(('xMin', 'xMid', 'xMax')) for j, y in enumerate(('YMin', 'YMid', 'YMax'))}
    if aspect == ['none']:
        alignment = None
    elif len(aspect) in (1, 2) and aspect[0] in alignments and (len(aspect) == 1 or aspect[1] == 'meet'):
        alignment = alignments[aspect[0]]
    else:
        raise ValueError('SVG preserveAspectRatio supports only none or aligned meet')
    mm = 25.4 / 96
    width_mm, height_mm = (width * mm, height * mm)
    if viewbox is None:
        matrix = (mm, 0.0, 0.0, mm, 0.0, 0.0)
    else:
        x, y, vw, vh = viewbox
        sx, sy = (width_mm / vw, height_mm / vh)
        if alignment is None:
            tx, ty = (-x * sx, -y * sy)
        else:
            sx = sy = min(sx, sy)
            tx = -x * sx + (width_mm - vw * sx) * alignment[0]
            ty = -y * sy + (height_mm - vh * sy) * alignment[1]
        matrix = (sx, 0.0, 0.0, sy, tx, ty)
    notices = (SvgNotice('inferred-size', 'SVG viewport dimensions inferred from viewBox'),) if inferred else ()
    return SvgViewport(width_mm, height_mm, matrix, notices)
