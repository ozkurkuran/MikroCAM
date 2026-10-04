"""Strict bounded GRBL status/settings parsing, independent of transport and Qt."""
from math import isfinite
import re

from .models import GrblStatus, MachineState, XYZ


MAX_LINE_BYTES = 512
MAX_CHUNK_BYTES = 4096
_DECIMAL = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z')
_STATE = re.compile(r'[A-Za-z][A-Za-z0-9]*(?::[0-9]+)?\Z')
_FIELD = re.compile(r'([A-Za-z][A-Za-z0-9]*):([^|<>\x00-\x20\x7f]+)\Z')
_STATES = {'Idle': MachineState.IDLE, 'Jog': MachineState.JOG,
           'Run': MachineState.RUNNING, 'Hold': MachineState.PAUSED,
           'Alarm': MachineState.ALARM, 'Home': MachineState.HOMING,
           'Check': MachineState.CHECK, 'Sleep': MachineState.SLEEP,
           'Door': MachineState.DOOR, 'Error': MachineState.ERROR}


def _ascii_line(line: str) -> None:
    if not isinstance(line, str) or len(line) > MAX_LINE_BYTES:
        raise ValueError('GRBL line must be ASCII and at most 512 bytes')
    try:
        line.encode('ascii')
    except UnicodeEncodeError as error:
        raise ValueError('GRBL line must contain ASCII only') from error


def _vector(text: str) -> XYZ:
    axes = text.split(',')
    if len(axes) != 3 or any(_DECIMAL.fullmatch(axis) is None for axis in axes):
        raise ValueError('GRBL position requires exactly three finite decimal coordinates')
    vector = tuple(float(axis) for axis in axes)
    if not all(isfinite(axis) for axis in vector):
        raise ValueError('GRBL coordinates must be finite')
    return vector


_GRBLHAL_SUBSTATE = re.compile(r'(?:Run:[12]|Alarm:(?:[1-9][0-9]?|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\Z')


def parse_status(line: str, *, grblhal: bool = False) -> GrblStatus:
    """Validate a three-axis report without inventing units, offsets or positions.

    ``grblhal`` (spec 043 research R4) maps only the documented ``Run:1/2`` and ``Alarm:<code>``
    sub-states to their base state and accepts grblHAL's value-less ``AR`` field.
    """
    _ascii_line(line)
    if not line.startswith('<') or not line.endswith('>'):
        raise ValueError('Not a GRBL status report')
    parts = line[1:-1].split('|')
    raw_state = parts[0]
    if _STATE.fullmatch(raw_state) is None:
        raise ValueError('Malformed GRBL state')
    vectors: dict[str, XYZ] = {}
    for field in parts[1:]:
        if grblhal and field == 'AR':
            continue
        match = _FIELD.fullmatch(field)
        if match is None:
            raise ValueError('Malformed GRBL status field')
        name, value = match.groups()
        if name in ('MPos', 'WPos', 'WCO'):
            if name in vectors:
                raise ValueError(f'Duplicate GRBL {name} field')
            vectors[name] = _vector(value)
    if ('MPos' in vectors) == ('WPos' in vectors):
        raise ValueError('GRBL status requires exactly one MPos or WPos')
    base = raw_state.split(':', 1)[0]
    state = _STATES.get(raw_state, MachineState.UNKNOWN)
    if base in ('Hold', 'Door') or (grblhal and _GRBLHAL_SUBSTATE.match(raw_state)):
        state = _STATES[base]
    return GrblStatus(state, raw_state, vectors.get('MPos'), vectors.get('WPos'), vectors.get('WCO'))


def parse_report_units(line: str) -> str | None:
    """Read only exact $13=0/1 evidence; unrelated records are not unit settings."""
    _ascii_line(line)
    if line == '$13=0':
        return 'mm'
    if line == '$13=1':
        return 'inch'
    if re.match(r'\$13(?:\D|$)', line):
        raise ValueError('Malformed GRBL $13 report-unit setting')
    return None


class LineFramer:
    """Incremental ASCII lines, with bounded accumulation and oversize recovery."""

    def __init__(self) -> None:
        self._pending = bytearray()
        self._discarding = False

    def reset(self) -> None:
        """Clear all framing evidence when a session closes or resets."""
        self._pending.clear()
        self._discarding = False

    def feed(self, chunk: bytes) -> tuple[str, ...]:
        """Emit CR/LF-delimited records; an oversized record is discarded to its delimiter."""
        if not isinstance(chunk, bytes) or len(chunk) > MAX_CHUNK_BYTES:
            self.reset()
            raise ValueError('GRBL read chunk must be bytes and at most 4096 bytes')
        try:
            chunk.decode('ascii')
        except UnicodeDecodeError as error:
            self._pending.clear()
            if self._discarding and any(byte in (10, 13) for byte in chunk):
                self._discarding = False
            raise ValueError('GRBL records must contain ASCII only') from error
        lines: list[str] = []
        oversized = False
        for byte in chunk:
            if byte in (10, 13):
                if self._discarding:
                    self._discarding = False
                elif self._pending:
                    lines.append(self._pending.decode('ascii'))
                self._pending.clear()
            elif not self._discarding:
                if len(self._pending) == MAX_LINE_BYTES:
                    self._pending.clear()
                    self._discarding = True
                    oversized = True
                else:
                    self._pending.append(byte)
        if oversized:
            self._pending.clear()
            raise ValueError('GRBL record exceeds 512 bytes')
        return tuple(lines)
