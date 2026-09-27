"""Exact supported TX grammar and strict provisional manual-control read-back."""
from math import isfinite
import re

from .grbl import _DECIMAL, _vector
from .manual_models import (JogRequest, ModalState, ParameterRecord, StartupRecord,
                            ZeroRequest, PARAMETER_NAMES, WCS_NAMES)
from .models import XYZ, _validate_xyz


ZERO_TOLERANCE_MM = .005
_FIXED_COMMANDS = (b'?', b'$$\n', b'$G\n', b'$#\n', b'$N\n', b'M5 M9\n',
                   b'G54\n', b'\x85', b'\x18', b'\x84')
_ZERO_COMMANDS = (b'G10 L20 P1 X0 Y0\n', b'G10 L20 P1 Z0\n', b'G10 L20 P1 X0 Y0 Z0\n')
_JOG = re.compile(rb'\$J=G21 G91 [XYZ]-?(?:0\.1|1|10) F(?:100|300|600)\n\Z')
_OPTIONAL_G = ('G0', 'G1', 'G2', 'G3', 'G38.2', 'G38.3', 'G38.4', 'G38.5', 'G80',
               'G17', 'G18', 'G19', 'G40', 'G43.1', 'G49', 'G93', 'G94')
_OPTIONAL_GROUPS = (('motion', _OPTIONAL_G[:9]), ('plane', ('G17', 'G18', 'G19')),
                    ('cutter', ('G40',)), ('tool_length', ('G43.1', 'G49')),
                    ('feed_mode', ('G93', 'G94')))


def encode_jog(request: JogRequest) -> bytes:
    """Encode one exact finite mm incremental jog; never accept arbitrary wire text."""
    if not isinstance(request, JogRequest):
        raise ValueError('A typed jog request is required')
    checked = JogRequest(request.axis, request.distance_mm, request.feed_mm_min)
    return f'$J=G21 G91 {checked.axis}{checked.distance_mm:g} F{checked.feed_mm_min:g}\n'.encode('ascii')


def encode_zero(request: ZeroRequest) -> bytes:
    """Only selected G54 zero axes are transmitted in a single persistent write."""
    if not isinstance(request, ZeroRequest):
        raise ValueError('A typed zero request is required')
    checked = ZeroRequest(request.axes)
    return ('G10 L20 P1 ' + ' '.join(f'{axis}0' for axis in checked.axes) + '\n').encode('ascii')


def validate_command(data: bytes) -> None:
    """Shared controller/serial/simulator boundary for the complete bounded command set."""
    if type(data) is not bytes or len(data) > 80:
        raise ValueError('Command must be bytes of at most 80 bytes')
    if data in _FIXED_COMMANDS or data in _ZERO_COMMANDS or _JOG.fullmatch(data):
        return
    raise ValueError('Unsupported or noncanonical manual GRBL command')


def _line(line: str) -> None:
    if (not isinstance(line, str) or len(line) > 512
            or any(not 32 <= ord(char) <= 126 for char in line)):
        raise ValueError('Query record must be at most 512 printable ASCII bytes')


def _scalar(text: str) -> float:
    if _DECIMAL.fullmatch(text) is None:
        raise ValueError('Query numeric word must be a finite decimal')
    number = float(text)
    if not isfinite(number):
        raise ValueError('Query numeric word must be finite')
    return number


def parse_modal(line: str) -> ModalState | None:
    """Parse one complete $G record; the caller still owns its transaction ACK."""
    _line(line)
    if not line.startswith('[GC'):
        return None
    if not line.startswith('[GC:') or not line.endswith(']'):
        raise ValueError('Malformed modal query record')
    groups: dict[str, str] = {}
    coolant: list[str] = []
    for token in line[4:-1].split(' '):
        if token in WCS_NAMES:
            group = 'work_system'
        elif token in ('G20', 'G21'):
            group = 'units'
        elif token in ('G90', 'G91'):
            group = 'distance'
        elif token in ('M3', 'M4', 'M5'):
            group = 'spindle'
        elif token in ('M7', 'M8', 'M9'):
            if token in coolant or (coolant and ('M9' in coolant or token == 'M9')):
                raise ValueError('Duplicate or conflicting coolant modes')
            coolant.append(token)
            continue
        elif token in _OPTIONAL_G:
            group = next(name for name, words in _OPTIONAL_GROUPS if token in words)
        elif token[:1] in ('T', 'F', 'S'):
            number = _scalar(token[1:])
            if number < 0 or (token[0] == 'T' and (not number.is_integer() or number > 255)):
                raise ValueError('Invalid modal numeric word')
            group = token[0]
        else:
            raise ValueError('Unsupported or malformed modal word')
        if group in groups:
            raise ValueError(f'Duplicate modal {group} group')
        groups[group] = token
    required = ('work_system', 'units', 'distance', 'spindle')
    if any(group not in groups for group in required) or not coolant:
        raise ValueError('Incomplete modal query record')
    return ModalState(*(groups[group] for group in required), tuple(coolant))


def parse_parameter(line: str, report_units: str) -> ParameterRecord | None:
    """Convert the recognized $13 wire-unit inventory rows to mm exactly once."""
    _line(line)
    if report_units not in ('mm', 'inch'):
        raise ValueError('Verified report units are required for parameter evidence')
    if re.match(r'\[(?:G5[4-9]|G92|TLO)(?![A-Za-z0-9])', line) is None:
        return None
    match = re.fullmatch(r'\[(G5[4-9]|G92|TLO):([^\[\]]+)\]', line)
    if match is None:
        raise ValueError('Malformed recognized parameter record')
    name, text = match.groups()
    factor = 25.4 if report_units == 'inch' else 1.
    value = _scalar(text) * factor if name == 'TLO' else tuple(axis * factor for axis in _vector(text))
    return ParameterRecord(name, value)


def parse_startup(line: str) -> StartupRecord | None:
    """Retain startup block data for admission checks; never execute or rewrite it."""
    _line(line)
    if not line.startswith('$N'):
        return None
    match = re.fullmatch(r'\$N([01])=(.*)', line)
    if match is None:
        raise ValueError('Malformed startup query record')
    return StartupRecord(int(match[1]), match[2])


def _inventory(records: tuple[ParameterRecord, ...]) -> dict[str, XYZ | float]:
    if type(records) is not tuple or len(records) != len(PARAMETER_NAMES):
        raise ValueError('A complete immutable eight-row parameter inventory is required')
    result: dict[str, XYZ | float] = {}
    for record in records:
        if not isinstance(record, ParameterRecord) or record.name in result:
            raise ValueError('Parameter inventory must contain unique typed rows')
        checked = ParameterRecord(record.name, record.value)
        result[checked.name] = checked.value
    if set(result) != set(PARAMETER_NAMES):
        raise ValueError('Parameter inventory is incomplete')
    return result


def verify_zero(before: tuple[ParameterRecord, ...], after: tuple[ParameterRecord, ...],
                machine_position_mm: XYZ, axes: tuple[str, ...]) -> None:
    """Verify only the requested G54 axes changed, using full independent mm inventories."""
    selected = ZeroRequest(axes).axes
    if machine_position_mm is None:
        raise ValueError('A fresh machine position is required')
    _validate_xyz(machine_position_mm)
    old, new = _inventory(before), _inventory(after)
    for name in PARAMETER_NAMES:
        if name == 'G54':
            expected = tuple(machine_position_mm[index] - old['G92'][index]
                             - (old['TLO'] if index == 2 else 0.) if axis in selected
                             else old['G54'][index] for index, axis in enumerate('XYZ'))
        else:
            expected = old[name]
        left = (expected,) if name == 'TLO' else expected
        right = (new[name],) if name == 'TLO' else new[name]
        if any(not isfinite(a) or abs(a - b) > ZERO_TOLERANCE_MM for a, b in zip(left, right)):
            raise ValueError(f'Zero read-back mismatch for {name}')
