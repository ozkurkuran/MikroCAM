"""Offline allowlist for the standard SVG 1.0/1.1 public document type declaration.

The XML parser never sees a DTD: one allowlisted prolog DOCTYPE is blanked before parsing, so no
external subset is fetched and no entity can be declared or expanded.
"""
import re


SVG_PUBLIC_DOCTYPES = (
    ('-//W3C//DTD SVG 1.0//EN', 'http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd'),
    ('-//W3C//DTD SVG 1.1//EN', 'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd'),
)
_SPACE = '[ \t\r\n]'
_PROLOG_ITEM = re.compile(rf'''{_SPACE}+|<\?.*?\?>|<!--.*?-->''', re.DOTALL)
_HEADER = re.compile(rf'''<!DOCTYPE{_SPACE}+([^ \t\r\n\[>]+)'''
                     rf'''(?:{_SPACE}+(PUBLIC|SYSTEM)(?:{_SPACE}+("[^"]*"|'[^']*'))?'''
                     rf'''(?:{_SPACE}+("[^"]*"|'[^']*'))?)?{_SPACE}*([\[>])''')
_STANDARD = 'only the standard SVG 1.0/1.1 public DOCTYPE without internal subset is accepted'


def _prolog_end(text: str) -> int:
    position = 0
    while (match := _PROLOG_ITEM.match(text, position)) is not None:
        position = match.end()
    return position


def _check_header(match: re.Match | None) -> None:
    if match is not None and match[5] == '[':
        raise ValueError('SVG DOCTYPE internal subset/entity declarations are unsupported')
    if match is None or match[1] != 'svg' or match[2] != 'PUBLIC' or match[4] is None:
        raise ValueError(f'Unsupported SVG DOCTYPE; {_STANDARD}')
    if (match[3][1:-1], match[4][1:-1]) not in SVG_PUBLIC_DOCTYPES:
        raise ValueError('Rejected unknown SVG DOCTYPE public/system identifiers; '
                         'only the W3C SVG 1.0/1.1 DTD identifiers are accepted')


def strip_svg_doctype(text: str) -> str:
    """Blank one allowlisted prolog DOCTYPE in place; reject every other DTD construct."""
    if type(text) is not str:
        raise ValueError('SVG DOCTYPE inspection requires decoded text')
    start = _prolog_end(text)
    if text.startswith('<!DOCTYPE', start):
        header = _HEADER.match(text, start)
        _check_header(header)
        blank = re.sub(r'[^\r\n]', ' ', header[0])
        text = text[:start] + blank + text[header.end():]
    upper = text.upper()
    if '<!DOCTYPE' in upper or '<!ENTITY' in upper:
        raise ValueError('SVG document/entity declarations are unsupported outside one standard '
                         'SVG 1.0/1.1 prolog DOCTYPE')
    return text
