"""Bounded offline SVG selectors and presentation cascade; no CSS layout engine."""
from dataclasses import dataclass
import re
from xml.etree import ElementTree as ET

from mikrocam.importers.svg_style import _clip_reference, _inline


MAX_CSS_CHARS = 65536
MAX_CSS_SELECTORS = 256
_IDENTIFIER = r'-?[A-Za-z_][A-Za-z0-9_-]*'
_SELECTOR = re.compile(rf'(?:\*|[.#]?{_IDENTIFIER})\Z')


def _specificity(selector: str) -> int:
    if isinstance(selector, str) and len(selector) > MAX_CSS_CHARS:
        raise ValueError('SVG CSS selector exceeds supported limit')
    if not isinstance(selector, str) or not _SELECTOR.fullmatch(selector):
        raise ValueError('Unsupported SVG CSS selector; use tag, *, .class or #id')
    return 100 if selector.startswith('#') else 10 if selector.startswith('.') else 0 if selector == '*' else 1


def _comments(text: str) -> str:
    cleaned = re.sub(r'/\*.*?\*/', ' ', text, flags=re.DOTALL)
    if '/*' in cleaned or '*/' in cleaned:
        raise ValueError('Malformed SVG CSS comment')
    return cleaned


def _validate_declaration(key: str, value: str) -> None:
    if (isinstance(key, str) and isinstance(value, str)
            and len(key) + len(value) + 1 > 16384):
        raise ValueError('SVG CSS declaration exceeds supported limit')
    if (not isinstance(key, str) or not isinstance(value, str) or not key or not value
            or key != key.strip().lower() or value != value.strip()
            or any(char in key + value for char in ';{}!\\@')):
        raise ValueError('Malformed SVG CSS declaration')
    declaration = f'{key}:{value}'
    _inline(declaration)  # One grammar authority for supported property names.
    if key == 'clip-path' and value != 'inherit':
        _clip_reference(value)
    # Paint semantics depend on the winning value and clipping/material context.


@dataclass(frozen=True)
class SvgCssRule:
    selector: str
    declarations: tuple[tuple[str, str, bool], ...]
    specificity: int
    order: int

    def __post_init__(self) -> None:
        expected = _specificity(self.selector)
        if (type(self.specificity) is not int or self.specificity != expected
                or type(self.order) is not int or not 0 <= self.order < MAX_CSS_SELECTORS
                or type(self.declarations) is not tuple or len(self.declarations) > MAX_CSS_CHARS):
            raise ValueError('Invalid SVG CSS rule record')
        chars = 0
        for declaration in self.declarations:
            if (type(declaration) is not tuple or len(declaration) != 3
                    or type(declaration[2]) is not bool):
                raise ValueError('Invalid SVG CSS declaration record')
            key, value, _ = declaration
            _validate_declaration(key, value)
            chars += len(key) + len(value) + 2
            if chars > MAX_CSS_CHARS:
                raise ValueError('SVG CSS declarations exceed supported limit')


def _declarations(text: str) -> tuple[tuple[str, str, bool], ...]:
    text = _comments(text)
    result = []
    for declaration in text.split(';'):
        if not declaration.strip():
            continue
        key, separator, value = declaration.partition(':')
        key, value = key.strip().lower(), value.strip()
        if not separator:
            raise ValueError('Malformed SVG CSS declaration')
        important = re.search(r'\s*!\s*important\s*$', value, re.IGNORECASE)
        if important is not None:
            value = value[:important.start()].strip()
        _validate_declaration(key, value)
        result.append((key, value, important is not None))
    return tuple(result)


def _style_text(root: ET.Element) -> tuple[str, ...]:
    if not isinstance(root, ET.Element):
        raise ValueError('SVG CSS requires an XML element')
    texts, chars = [], 0
    pending = [root]
    while pending:
        element = pending.pop()
        if not isinstance(element.tag, str) or element.tag.rsplit('}', 1)[-1] == 'metadata':
            continue
        pending.extend(reversed(element))
        if element.tag not in ('style', '{http://www.w3.org/2000/svg}style'):
            continue
        if (len(element) or any(key.rsplit('}', 1)[-1] in ('href', 'src') for key in element.attrib)
                or element.get('type', 'text/css').strip().lower() != 'text/css'
                or element.get('media', 'all').strip().lower() not in ('', 'all')):
            raise ValueError('External, conditional or structured SVG CSS is unsupported')
        text = element.text or ''
        chars += len(text)
        if chars > MAX_CSS_CHARS:
            raise ValueError('SVG CSS text exceeds supported limit')
        texts.append(text)
    return tuple(texts)


def parse_stylesheets(root: ET.Element) -> tuple[SvgCssRule, ...]:
    """Compile embedded style elements, rejecting unsupported syntax before traversal."""
    result = []
    for text in _style_text(root):
        text = _comments(text)
        if '@' in text or '\\' in text:
            raise ValueError('SVG CSS @rules and escapes are unsupported')
        position = 0
        while text[position:].strip():
            opening = text.find('{', position)
            closing = text.find('}', opening + 1) if opening >= 0 else -1
            if opening < 0 or closing < 0:
                raise ValueError('Malformed SVG CSS rule')
            selectors, body = text[position:opening].strip(), text[opening + 1:closing]
            if '{' in body or '}' in selectors:
                raise ValueError('Nested or malformed SVG CSS rules are unsupported')
            declarations = _declarations(body)
            for selector in selectors.split(','):
                selector = selector.strip()
                specificity = _specificity(selector)
                if len(result) >= MAX_CSS_SELECTORS:
                    raise ValueError('SVG CSS selector count exceeds supported limit')
                result.append(SvgCssRule(selector, declarations, specificity, len(result)))
            position = closing + 1
    return tuple(result)


def _matches(selector: str, tag: str, attributes: dict[str, str]) -> bool:
    if selector == '*':
        return True
    if selector.startswith('#'):
        return attributes.get('id') == selector[1:]
    if selector.startswith('.'):
        return selector[1:] in attributes.get('class', '').split()
    return selector == tag


def cascade_attributes(tag: str, attributes: dict[str, str], rules: tuple[SvgCssRule, ...]) -> dict[str, str]:
    """Return resolved inline declarations without replacing retained source attributes."""
    if (not isinstance(tag, str) or not tag or type(attributes) is not dict
            or any(not isinstance(k, str) or not isinstance(v, str) for k, v in attributes.items())
            or type(rules) is not tuple or len(rules) > MAX_CSS_SELECTORS
            or any(type(rule) is not SvgCssRule for rule in rules)):
        raise ValueError('Invalid SVG CSS cascade input')
    if len(attributes.get('class', '')) > MAX_CSS_CHARS:
        raise ValueError('SVG CSS class list exceeds supported limit')
    inline = attributes.get('style', '')
    if len(inline) > 16384:
        raise ValueError('SVG inline style exceeds supported limit')
    winners = {}
    candidates = [(rule.declarations, rule.specificity, rule.order) for rule in rules
                  if _matches(rule.selector, tag, attributes)]
    candidates.append((_declarations(inline), 1000, MAX_CSS_SELECTORS))
    for declarations, specificity, order in candidates:
        for index, (key, value, important) in enumerate(declarations):
            rank = (important, specificity, order, index)
            if key not in winners or rank >= winners[key][0]:
                winners[key] = (rank, value)
    output = dict(attributes)
    if winners:
        output['style'] = ';'.join(f'{key}:{winners[key][1]}' for key in sorted(winners))
        if len(output['style']) > 16384:
            raise ValueError('Resolved SVG inline style exceeds supported limit')
    return output
