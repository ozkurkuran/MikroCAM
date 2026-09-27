"""Bounded Gerber statement boundaries shared by inspection and legacy parsing."""
from collections.abc import Iterator
from mikrocam.core.manufacturing_models import MAX_MANUFACTURING_BYTES

MAX_STATEMENTS = 100000
MAX_STATEMENT_BYTES = 1048576


def _tokens(text: str) -> Iterator[tuple[str, bool]]:
    offset, size = 0, len(text)
    while offset < size:
        if text[offset] in ' \t\r\n':
            offset += 1
            continue
        extended = text[offset] == '%'
        end = text.find('%' if extended else '*', offset + 1)
        if end < 0:
            raise ValueError('Gerber command has an unfinished delimiter')
        if end - offset + 1 > MAX_STATEMENT_BYTES:
            raise ValueError('Gerber statement exceeds byte limit')
        value = text[offset:end + 1].replace('\r', '').replace('\n', '')
        offset = end + 1
        if extended:
            if len(value) < 4 or not value.endswith('*%'):
                raise ValueError('Gerber extended command requires a complete statement')
            body = value[1:-1]
            if body.startswith('AM'):
                if not body[2:body.index('*')].strip():
                    raise ValueError('Gerber aperture macro requires a name')
                yield value, True
            else:
                position = 0
                while position < len(body):
                    stop = body.find('*', position)
                    command = body[position:stop].strip()
                    position = stop + 1
                    if not command:
                        raise ValueError('Gerber extended block contains an empty statement')
                    yield '%' + command + '*%', True
        else:
            if '%' in value and not value.startswith(('G04', 'G4 ')):
                raise ValueError('Gerber ordinary command contains an unexpected percent delimiter')
            if value == '*':
                raise ValueError('Gerber command is empty')
            yield value, False


def gerber_statements(data: bytes, *, retain_attributes: bool = False) -> tuple[str, ...]:
    """Keep AM blocks intact and never remove drawing commands adjacent to metadata."""
    if (type(data) is not bytes or not 1 <= len(data) <= MAX_MANUFACTURING_BYTES
            or type(retain_attributes) is not bool):
        raise ValueError('Gerber statements require bounded immutable bytes and a boolean policy')
    if any(byte < 32 and byte not in (9, 10, 13) for byte in data):
        raise ValueError('Gerber source contains unsupported control bytes')
    text = data.removeprefix(b'\xef\xbb\xbf').decode('latin1')
    result, count = [], 0
    for value, extended in _tokens(text):
        count += 1
        if count > MAX_STATEMENTS:
            raise ValueError('Gerber command count exceeds limit')
        if not retain_attributes and extended and value[1:3] in ('TF', 'TA', 'TO', 'TD'):
            continue
        result.append(value)
    if count == 0:
        raise ValueError('Gerber source contains no statements')
    return tuple(result)
