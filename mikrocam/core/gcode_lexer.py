"""Strict bounded source-line lexer; comments cannot shield GRBL realtime bytes."""
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from decimal import Decimal
from io import StringIO
import math
import re

from .gcode_models import (MAX_LINES, MAX_LINE_LENGTH, MAX_NUMBER_LENGTH, MAX_MAGNITUDE,
                           PreflightCancelled)

_WORD = re.compile(r'([A-Za-z])([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))')


class GcodeError(ValueError):
    def __init__(self, line: int, code: str, message: str) -> None:
        super().__init__(message)
        self.line, self.code = line, code


@dataclass(frozen=True)
class Block:
    line: int
    words: tuple[tuple[str, float], ...]
    canonical: str = ''


def _executable(line: str, number: int) -> str:
    if len(line) > MAX_LINE_LENGTH:
        raise GcodeError(number, 'resource-limit', 'G-code line length exceeds limit')
    if any((ord(c) < 32 and c != '\t') or ord(c) >= 127 or c in '!?~' for c in line):
        raise GcodeError(number, 'unsafe-byte', 'Control, realtime or non-ASCII source byte is unsupported')
    result, comment = [], False
    for character in line:
        if character == '(':
            if comment:
                raise GcodeError(number, 'syntax', 'Nested comments are unsupported')
            comment = True
        elif character == ')':
            if not comment:
                raise GcodeError(number, 'syntax', 'Unmatched comment terminator')
            comment = False
        elif character == ';' and not comment:
            break
        elif not comment:
            result.append(character)
    if comment:
        raise GcodeError(number, 'syntax', 'Unclosed or multiline comment')
    return ''.join(result)


def _words(text: str, line: int) -> tuple[tuple[str, float], ...]:
    result, offset = [], 0
    while offset < len(text):
        if text[offset] in ' \t':
            offset += 1
            continue
        match = _WORD.match(text, offset)
        if match is None:
            raise GcodeError(line, 'syntax', f'Unsupported syntax at column {offset + 1}')
        letter, numeric = match.groups()
        if len(numeric) > MAX_NUMBER_LENGTH:
            raise GcodeError(line, 'resource-limit', 'Numeric token exceeds limit')
        value = float(numeric)
        if not math.isfinite(value) or abs(value) > MAX_MAGNITUDE:
            raise GcodeError(line, 'numeric-range', 'Numeric magnitude exceeds supported range')
        if letter.upper() in 'GMNT' and Decimal(numeric) != Decimal(str(value)):
            raise GcodeError(line, 'numeric-precision', 'Mode or integer metadata loses decimal precision')
        result.append((letter.upper(), value))
        offset = match.end()
    return tuple(result)


def iter_blocks(text: str, cancelled: Callable[[], bool] | None = None) -> Iterator[Block]:
    """Yield every executable block with original line identity; never drop unknown text."""
    for number, raw in enumerate(StringIO(text, newline=None), 1):
        if cancelled is not None and cancelled():
            raise PreflightCancelled('Preflight cancelled')
        if number > MAX_LINES:
            raise GcodeError(number, 'resource-limit', 'G-code line count exceeds limit')
        executable = _executable(raw.rstrip('\r\n'), number)
        words = _words(executable, number)
        if words:
            canonical = ''.join(m.group(1).upper()+m.group(2) for m in _WORD.finditer(executable))
            yield Block(number, words, canonical)
