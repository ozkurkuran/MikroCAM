"""grblHAL query-record dialect mapped onto the strict GRBL 1.1 evidence parsers (spec 043).

Formats come from grblHAL/core c3a887e3 (specs/043-grblhal-serial/research.md R5-R7); no firmware
code is copied. Only provably neutral differences are removed. Every other grblHAL-only word or
record is passed through unchanged so the existing strict parsers reject it (fail-closed). The raw
bytes stay in the wire log; this function only shapes evidence for manual/job/probe owners.
"""
import re

_DECIMAL = r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)'
# Neutral $G words: G92 activity flag (numeric G92 is verified from $#), canned-cycle return mode,
# scaling off, override-disable modes other than feed hold, pallet-change pause and persistent
# motion modes that MikroCAM's explicit jog/G10/G54/probe lines never rely on.
_NEUTRAL_MODAL = frozenset(('G92', 'G98', 'G99', 'G50', 'M50', 'M51', 'M56', 'M60', 'G5', 'G5.1',
                            'G33', 'G33.1', 'G73', 'G76', 'G81', 'G82', 'G83', 'G84', 'G85', 'G86',
                            'G89'))
_EXTRA_SYSTEM = re.compile(r'\[G59\.[123]:[^\[\]]*\]\Z')
_VECTOR_TLO = re.compile(rf'\[TLO:({_DECIMAL}),({_DECIMAL}),({_DECIMAL})\]\Z')
_SETTING = re.compile(r'\$[0-9]+=(.*)\Z')


def normalize_query_line(line: str) -> str | None:
    """Return the GRBL-shaped record, the unchanged line, or None for an ignorable grblHAL record."""
    if line.startswith('[GC:') and line.endswith(']'):
        words = [word for word in line[4:-1].split(' ') if word not in _NEUTRAL_MODAL]
        return '[GC:' + ' '.join(words) + ']'
    if _EXTRA_SYSTEM.match(line):
        return None
    vector = _VECTOR_TLO.match(line)
    if vector is not None:
        if float(vector[1]) == 0 and float(vector[2]) == 0:
            return f'[TLO:{vector[3]}]'
        return line
    setting = _SETTING.match(line)
    if setting is not None and re.fullmatch(_DECIMAL, setting[1]) is None:
        return None
    return line
