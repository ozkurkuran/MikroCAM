"""Finite SVG presentation inheritance; unsupported appearance is explicit."""
import re

from mikrocam.core.svg_models import SvgPaint
from mikrocam.core.svg_transform import parse_svg_length, parse_svg_numbers


_DEFAULTS = {'fill': 'black', 'stroke': 'none', 'stroke-width': '1',
             'stroke-linecap': 'butt', 'stroke-linejoin': 'miter', 'stroke-miterlimit': '4',
             'fill-rule': 'nonzero', 'fill-opacity': '1', 'stroke-opacity': '1',
             'visibility': 'visible', 'display': 'inline', 'opacity': '1', 'color': 'black',
             'clip-path': 'none', 'clip-rule': 'nonzero', 'vector-effect': 'none'}
_UNSUPPORTED = {'clip', 'mask', 'filter', 'marker', 'marker-start', 'marker-mid',
                'marker-end', 'stroke-dasharray', 'mix-blend-mode'}
_STYLE_GEOMETRY = {'transform', 'transform-origin', 'transform-box', 'width', 'height',
                   'x', 'y', 'r', 'rx', 'ry', 'cx', 'cy', 'd'}


def _enable_background(value: str) -> None:
    """Validate SVG 1.1 accumulate | new [x y width height]; it never changes positive material."""
    words = value.lower().split()
    if words in (['accumulate'], ['new'], ['inherit']):
        return
    if words[:1] == ['new'] and len(words) == 5:
        numbers = [parse_svg_numbers(word) for word in words[1:]]
        if all(len(number) == 1 for number in numbers) and numbers[2][0] >= 0 and numbers[3][0] >= 0:
            return
    raise ValueError('Malformed SVG enable-background declaration')


def _inline(text: str) -> dict[str, str]:
    if len(text) > 16384:
        raise ValueError('SVG inline style exceeds supported limit')
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.DOTALL)
    if '/*' in text or '*/' in text:
        raise ValueError('Malformed SVG CSS comment')
    result = {}
    for declaration in text.split(';'):
        if not declaration.strip():
            continue
        key, separator, value = declaration.partition(':')
        key, value = key.strip().lower(), value.strip()
        if not separator or not key or not value:
            raise ValueError('Malformed SVG inline style declaration')
        value = re.sub(r'\s*!important\s*$', '', value).strip()
        if key in _STYLE_GEOMETRY:
            raise ValueError(f'Unsupported SVG CSS geometry property: {key}; use attributes')
        if key == 'enable-background':
            _enable_background(value)
            continue  # Filter-only background setup, written by Illustrator; filters stay unsupported.
        if key not in _DEFAULTS and key not in _UNSUPPORTED and key not in (
                'overflow', 'stroke-dashoffset', 'paint-order'):
            raise ValueError(f'Unsupported SVG CSS property: {key}')
        result[key] = value
    return result


def _opacity(value: str) -> str:
    numbers = parse_svg_numbers(value)
    if len(numbers) != 1 or numbers[0] not in (0., 1.):
        raise ValueError('Only zero or fully opaque SVG material is supported')
    return str(int(numbers[0]))


def _solid_paint(value: str, *, color: bool = False) -> str:
    value = value.strip().lower()
    if value == 'transparent' or (not color and value in ('none', 'currentcolor')):
        return value
    # Color is positive material in this CAM importer, never a subtraction operator.
    if (re.fullmatch(r'#[0-9a-f]{3}(?:[0-9a-f]{3})?', value)
            or value.lower() in ('black', 'white', 'red', 'green', 'blue', 'yellow', 'gray',
                                 'grey', 'orange', 'purple', 'pink', 'brown', 'cyan', 'magenta',
                                 'lime', 'navy', 'teal', 'olive', 'maroon', 'silver', 'aqua', 'fuchsia')):
        return value
    function = re.fullmatch(r'(rgb|hsl)\(([^()]*)\)', value)
    if function is not None:
        channels = tuple(component.strip() for component in function[2].split(','))
        if len(channels) != 3:
            raise ValueError('SVG rgb/hsl requires exactly three comma-separated components')
        percentages = tuple(component.endswith('%') for component in channels)
        if ((function[1] == 'rgb' and len(set(percentages)) != 1)
                or (function[1] == 'hsl' and percentages != (False, True, True))):
            raise ValueError('SVG rgb requires consistent channel units; hsl requires percentage saturation/lightness')
        for component, percent in zip(channels, percentages):
            numbers = parse_svg_numbers(component[:-1] if percent else component)
            if len(numbers) != 1:
                raise ValueError('SVG color component requires one finite number')
        return value  # Out-of-range channels clamp to an opaque color, still positive CAM material.
    raise ValueError(f'Unsupported SVG paint: {value[:80]}; use a solid color or none')


def resolve_style(attributes: dict[str, str], parent: dict[str, str] | None = None, *,
                  clip_mode: bool = False) -> dict[str, str]:
    """Resolve supported inherited presentation values without evaluating external CSS."""
    parent = _DEFAULTS if parent is None else parent
    result = dict(parent)
    result.update({'display': 'inline', 'opacity': '1', 'vector-effect': 'none'})  # Not inherited.
    result['clip-path'] = 'none'  # Application scopes, rather than inheritance, clip descendants.
    supplied = {key: value for key, value in attributes.items()
                if key in _DEFAULTS or key in _UNSUPPORTED or key in ('overflow', 'stroke-dashoffset', 'paint-order')}
    supplied.update(_inline(attributes.get('style', '')))
    for key, value in supplied.items():
        if clip_mode and (key in ('fill', 'fill-rule', 'fill-opacity', 'opacity', 'color',
                                 'vector-effect', 'paint-order') or key.startswith('stroke')):
            continue  # Clipping uses geometric silhouettes, independent of painting.
        value = value.strip()
        if value.lower() == 'inherit':
            value = parent.get(key, _DEFAULTS.get(key, 'none'))
        if key == 'color' and value.lower() == 'currentcolor':
            value = parent.get('color', 'black')
        if key in _UNSUPPORTED and value not in ('none', 'normal'):
            raise ValueError(f'Unsupported SVG appearance: {key}')
        if key == 'overflow' and value != 'visible':
            raise ValueError('SVG viewport clipping is not supported in this import slice')
        if key == 'paint-order' and value != 'normal':
            raise ValueError('Custom SVG paint-order is unsupported')
        if key == 'stroke-dashoffset' and value not in ('0', '0.0'):
            raise ValueError('SVG dashed strokes are unsupported')
        if key in _DEFAULTS:
            result[key] = value
    if clip_mode:
        for key, value in _DEFAULTS.items():
            if key not in ('display', 'visibility', 'clip-path', 'clip-rule'):
                result[key] = value
    if result['clip-rule'] not in ('nonzero', 'evenodd'):
        raise ValueError('Unsupported SVG clip-rule')
    result['vector-effect'] = result['vector-effect'].lower()
    if result['vector-effect'] not in ('none', 'non-scaling-stroke'):
        raise ValueError(f"Unsupported SVG vector-effect: {result['vector-effect'][:64]}; "
                         'only none or non-scaling-stroke is supported')
    result['clip-path'] = _clip_reference(result['clip-path'])
    for key in ('opacity', 'fill-opacity', 'stroke-opacity'):
        result[key] = _opacity(result[key])
    if result['display'] not in ('none', 'inline', 'block'):
        raise ValueError('Unsupported SVG display value')
    if result['visibility'] not in ('visible', 'hidden', 'collapse'):
        raise ValueError('Unsupported SVG visibility value')
    result['color'] = _solid_paint(result['color'], color=True)
    result['fill'] = _solid_paint(result['fill'])
    result['stroke'] = _solid_paint(result['stroke'])
    style_paint(result)  # Validate widths, cap/join, winding and miter limit before geometry.
    return result


def _clip_reference(value: str) -> str:
    if value == 'none':
        return value
    match = re.fullmatch(r'''url\(\s*(['"]?)#([^\s()'"#]+)\1\s*\)''', value)
    if match is None or len(match[2]) > 256:
        raise ValueError('SVG clipping requires one local url(#id) reference or none')
    return f'url(#{match[2]})'


def style_paint(style: dict[str, str]) -> SvgPaint:
    """Convert resolved source facts to immutable geometry policy."""
    miter = parse_svg_numbers(style['stroke-miterlimit'])
    if len(miter) != 1:
        raise ValueError('SVG stroke-miterlimit requires one number')
    fill = style['color'] if style['fill'].lower() == 'currentcolor' else style['fill'].lower()
    stroke = style['color'] if style['stroke'].lower() == 'currentcolor' else style['stroke'].lower()
    return SvgPaint(fill=fill not in ('none', 'transparent') and style['fill-opacity'] == '1',
                    stroke=stroke not in ('none', 'transparent') and style['stroke-opacity'] == '1',
                    width=parse_svg_length(style['stroke-width']), linecap=style['stroke-linecap'],
                    linejoin=style['stroke-linejoin'], miterlimit=miter[0], fill_rule=style['fill-rule'])


def style_fill_is_white(style: dict[str, str]) -> bool | None:
    """Identify resolved active white fill without changing positive material semantics."""
    if (not style_paint(style).fill or style['opacity'] == '0'
            or style['display'] == 'none' or style['visibility'] != 'visible'):
        return None
    fill = style['color'] if style['fill'].lower() == 'currentcolor' else style['fill']
    fill = _solid_paint(fill)
    if fill in ('white', '#fff', '#ffffff'):
        return True
    function = re.fullmatch(r'(rgb|hsl)\(([^()]*)\)', fill)
    if function is None:
        return False
    channels = tuple(component.strip() for component in function[2].split(','))
    values = tuple(parse_svg_numbers(component.rstrip('%'))[0] for component in channels)
    if function[1] == 'hsl':
        return values[2] >= 100
    maximum = 100 if channels[0].endswith('%') else 255
    return all(value >= maximum for value in values)
