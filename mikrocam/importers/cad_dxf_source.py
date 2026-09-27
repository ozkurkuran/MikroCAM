"""Bounded text-DXF producer declarations without interpreting entity geometry."""
import io
import re

from mikrocam.core.cad_source import CadSourceEvidence, MAX_CAD_SOURCE_BYTES
from .cad_producer import classify_producer, producer_declaration

MAX_DXF_PAIRS = 250000
MAX_DXF_LINE_LENGTH = 8192
_DECLARATION = re.compile(r'^\s*(?:Generator\s*:|Creator\s*:|Created\s+with\b|Generated\s+by\b)',
                          re.IGNORECASE)


def _pairs(source: bytes):
    if type(source) is not bytes:
        raise ValueError('DXF source must be exact bytes')
    if len(source) > MAX_CAD_SOURCE_BYTES:
        raise ValueError('DXF source exceeds byte budget')
    try:
        text = source.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise ValueError('DXF source must be ASCII or UTF-8 text') from error
    if any(ord(character) < 32 and character not in '\r\n\t' for character in text):
        raise ValueError('Binary or control-character DXF is unavailable')
    stream = io.StringIO(text, newline=None)
    for count, code_line in enumerate(stream, 1):
        if count > MAX_DXF_PAIRS:
            raise ValueError('DXF pair budget exceeded')
        value_line = stream.readline()
        if not value_line:
            raise ValueError('DXF requires complete code/value pairs')
        code, value = code_line.rstrip('\n'), value_line.rstrip('\n')
        if len(code) > MAX_DXF_LINE_LENGTH or len(value) > MAX_DXF_LINE_LENGTH:
            raise ValueError('DXF line budget exceeded')
        code = code.strip()
        if not re.fullmatch(r'[0-9]+', code):
            raise ValueError('DXF group code must be an ASCII integer')
        significant = code.lstrip('0') or '0'
        if len(significant) > 4 or int(significant) > 1071:
            raise ValueError('DXF group code must be in 0..1071')
        yield int(significant), value


def dxf_source_evidence(source: bytes) -> tuple[CadSourceEvidence, ...]:
    """Extract explicit header/outside comments only after complete framing validation."""
    pairs = iter(_pairs(source))
    section = None
    ended = False
    evidence, seen = [], set()
    for code, value in pairs:
        token = value.strip()
        if ended:
            raise ValueError('DXF EOF must be the final pair')
        if code == 0 and token == 'SECTION':
            if section is not None:
                raise ValueError('DXF sections cannot nest')
            name_code, name = next(pairs, (None, ''))
            if name_code != 2 or not name.strip():
                raise ValueError('DXF SECTION requires a group-2 name')
            section = name.strip()
        elif code == 0 and token == 'ENDSEC':
            if section is None:
                raise ValueError('DXF ENDSEC has no matching section')
            section = None
        elif code == 0 and token == 'EOF':
            if section is not None:
                raise ValueError('DXF EOF cannot occur inside a section')
            ended = True
        elif code == 999:
            if section in (None, 'HEADER') and _DECLARATION.match(value):
                declared = producer_declaration(value)
                if declared is not None:
                    key = (classify_producer(declared), 'dxf.999', value)
                    if key not in seen:
                        if len(evidence) >= 32:
                            raise ValueError('DXF producer evidence budget exceeded')
                        evidence.append(CadSourceEvidence(*key))
                        seen.add(key)
        elif section is None:
            raise ValueError('DXF data outside a section is unsupported')
    if not ended or section is not None:
        raise ValueError('DXF requires closed sections and a final EOF')
    return tuple(evidence)
