"""Compare captured default-preprocessor words without interpreting machine state."""
from dataclasses import dataclass
from fractions import Fraction
import re

from .reference_compare import _tolerance


MAX_GCODE_BYTES = 32 * 1024 * 1024
MAX_BLOCKS = 500_000
_WORD = re.compile(r'([GMXYZFSTPIJKRN])([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))', re.IGNORECASE)
Word = tuple[str, Fraction]


def _words(block: str) -> tuple[Word, ...]:
    if block == '%':
        return (('%', Fraction(0)),)
    words, position = [], 0
    while position < len(block):
        if block[position].isspace():
            position += 1
            continue
        match = _WORD.match(block, position)
        if match is None:
            raise ValueError(f'Unsupported default-preprocessor syntax at column {position + 1}')
        letter, number = match.groups()
        if len(number) > 64:
            raise ValueError('G-code numeric token exceeds the resource limit')
        words.append((letter.upper(), Fraction(number)))
        position = match.end()
    return tuple(words)


def _blocks(text: str) -> tuple[tuple[Word, ...], ...]:
    if not isinstance(text, str) or len(text) > MAX_GCODE_BYTES:
        raise ValueError('G-code text exceeds the resource limit or is not a string')
    try:
        if len(text.encode('utf-8')) > MAX_GCODE_BYTES:
            raise ValueError('G-code text exceeds the resource limit')
    except UnicodeError as error:
        raise ValueError('G-code requires valid text') from error
    blocks, depth = [], 0
    for line in text.splitlines():
        executable = []
        for character in line:
            if character == '(':
                depth += 1
                if depth > 64:
                    raise ValueError('G-code comment nesting exceeds the resource limit')
            elif character == ')':
                if depth == 0:
                    raise ValueError('Unmatched G-code comment terminator')
                depth -= 1
            elif character == ';' and depth == 0:
                break
            elif depth == 0:
                executable.append(character)
        block = ''.join(executable).strip()
        if block:
            blocks.append(_words(block))
            if len(blocks) > MAX_BLOCKS:
                raise ValueError('G-code block count exceeds the resource limit')
    if depth:
        raise ValueError('Unclosed G-code comment')
    if not blocks or not any(word[0] != '%' for block in blocks for word in block):
        raise ValueError('G-code must contain executable words')
    return tuple(blocks)


@dataclass(frozen=True)
class GcodeComparison:
    """Zero-based executable block indices, independent of comment/blank line count."""
    matches: bool
    differing_blocks: tuple[int, ...]
    expected_count: int
    actual_count: int


def _differs(first: tuple[Word, ...], second: tuple[Word, ...], tolerance: Fraction) -> bool:
    if len(first) != len(second):
        return True
    for (letter, value), (other, number) in zip(first, second):
        if letter != other:
            return True
        if letter in {'X', 'Y'}:
            if abs(value - number) > tolerance:
                return True
        elif value != number:
            return True
    return False


def compare_gcode(expected: str, actual: str, *, distance_mm: float) -> GcodeComparison:
    """Tolerate X/Y spelling/noise while preserving actual Z/feed/spindle/dwell/modes.

    This handles only numeric words from the captured default preprocessor. It does
    not evaluate modal state, macros, safety, timing, machine limits or coordinates.
    Unsupported text raises ValueError rather than pretending those words match.
    """
    tolerance = Fraction(str(_tolerance(distance_mm, 'distance_mm')))
    first, second = _blocks(expected), _blocks(actual)
    differing = tuple(index for index in range(max(len(first), len(second)))
                      if index >= len(first) or index >= len(second)
                      or _differs(first[index], second[index], tolerance))
    return GcodeComparison(not differing, differing, len(first), len(second))
