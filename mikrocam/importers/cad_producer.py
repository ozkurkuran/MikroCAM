"""Finite explicit application claims, independent of drawing/profile heuristics."""
import re


_NAMES = (('KiCad', r'KiCad|PCBNEW|Eeschema'),
          ('Illustrator', r'Adobe\s+Illustrator|Illustrator'),
          ('Inkscape', r'Inkscape'),
          ('Proteus', r'(?:Labcenter\s+)?Proteus(?:\s+Design\s+Suite)?'))
_DECLARATION = re.compile(r'(?:Generator\s*:|Creator\s*:|Image\s+generated\s+by\b|'
                          r'Generated\s+by\b|Created\s+with\b)\s*(.+)', re.I | re.S)
# Observed genuine Proteus SVG exports write <desc>Created by Proteus Design Suite</desc>.
_CREATED_BY = re.compile(r'Created\s+by\b\s*(.+)', re.I | re.S)


def is_inkscape_version(value: str) -> bool:
    """Require a version-shaped root value, not a bare namespace declaration."""
    return (type(value) is str and len(value) <= 512
            and re.fullmatch(r'\d[\w.+-]*(?:\s+[^\r\n]+)?', value) is not None)


def producer_declaration(value: str) -> str | None:
    """Extract an anchored producer declaration, never a vendor mention in drawing text."""
    if type(value) is not str:
        raise ValueError('Producer declaration must be text')
    match = _DECLARATION.fullmatch(value.strip())
    return match[1].strip() if match else None


def desc_declaration(value: str) -> str | None:
    """Root SVG desc also admits "Created by" only when it names a supported application."""
    declared = producer_declaration(value)
    if declared is not None:
        return declared
    match = _CREATED_BY.fullmatch(value.strip())
    if match is None or len(match[1].strip()) > 512:
        return None  # Authorship text such as "Created by Jane Doe" is not a producer claim.
    return match[1].strip() if classify_producer(match[1].strip()) != 'Unknown' else None


def classify_producer(value: str) -> str:
    """Recognize a supported application name with an optional version suffix."""
    if type(value) is not str or len(value) > 512:
        raise ValueError('Producer value must be bounded text')
    value = ' '.join(value.split())
    mentioned = {name for name, pattern in _NAMES
                 if re.search(rf'(?<!\w)(?:{pattern})(?!\w)', value, re.I)}
    if len(mentioned) != 1:
        return 'Unknown'
    for name, pattern in _NAMES:
        match = re.fullmatch(rf'(?:{pattern})(?:\s+(.+))?', value, re.I)
        if match is None:
            continue
        suffix = match[1]
        if suffix is None or re.match(r'(?:v?\d|CS\d|CC\b|\()', suffix, re.I):
            return name
    return 'Unknown'
