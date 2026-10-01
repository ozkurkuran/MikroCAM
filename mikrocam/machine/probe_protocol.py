"""Narrow generated probe motion and independently correlated GRBL reports."""
import math
import re

_DECIMAL = r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)'
_COMMAND = re.compile(rf'G21 G90 G94 (G1|G38\.2) (Z({_DECIMAL})|X({_DECIMAL}) Y({_DECIMAL})) F({_DECIMAL})\n\Z')
_RESULT = re.compile(rf'\[PRB:({_DECIMAL}),({_DECIMAL}),({_DECIMAL}):([01])\]\Z')


def _number(value: object, *, feed: bool = False) -> float:
    if type(value) not in (int, float) or abs(value) > 1e6 or not math.isfinite(value):
        raise ValueError('Probe values require finite bounded numbers')
    if feed and not .01 <= value <= 10000:
        raise ValueError('Probe feed requires .01..10000 mm/min')
    return float(value)


def validate_probe_command(data: bytes) -> None:
    """Accept only one bounded absolute-mm vertical probe or linear Z/XY travel."""
    if type(data) is not bytes or len(data) > 120:
        raise ValueError('Probe command requires at most120 ASCII bytes')
    try:
        match = _COMMAND.fullmatch(data.decode('ascii'))
    except UnicodeDecodeError as error:
        raise ValueError('Probe command requires ASCII') from error
    if match is None or (match[1] == 'G38.2' and match[3] is None):
        raise ValueError('Unsupported probe command')
    for text in match.group(3, 4, 5):
        if text is not None:
            _number(float(text))
    _number(float(match[6]), feed=True)


def probe_move(*, feed: float, x: float | None = None, y: float | None = None,
               z: float | None = None, probing: bool = False) -> bytes:
    """Generate one explicit-feed Z or paired XY move; probes are vertical only."""
    if type(probing) is not bool:
        raise ValueError('Probe selection requires boolean')
    def word(value: float) -> str:
        return format(_number(value), '.9f').rstrip('0').rstrip('.') or '0'
    if z is not None and x is None and y is None:
        axes = 'Z' + word(z)
    elif not probing and z is None and x is not None and y is not None:
        axes = 'X' + word(x) + ' Y' + word(y)
    else:
        raise ValueError('Probe motion requires only Z or paired XY')
    mode = 'G38.2' if probing else 'G1'
    data = f'G21 G90 G94 {mode} {axes} F{word(_number(feed, feed=True))}\n'.encode('ascii')
    validate_probe_command(data)
    return data


def parse_probe_record(line: str, units: str) -> tuple[tuple[float, float, float], bool] | None:
    """Parse bounded current or cached evidence; the caller owns transaction meaning."""
    if type(line) is not str or len(line) > 512 or units not in ('mm', 'inch'):
        raise ValueError('Probe result requires bounded text and verified units')
    if not line.startswith('[PRB'):
        return None
    match = _RESULT.fullmatch(line)
    if match is None:
        raise ValueError('Probe result malformed')
    factor = 25.4 if units == 'inch' else 1.
    return tuple(_number(float(match[index]) * factor) for index in (1, 2, 3)), match[4] == '1'


def parse_probe_result(line: str, units: str) -> tuple[float, float, float] | None:
    """Successful PRB machine coordinates, converted from verified $13 units once."""
    record = parse_probe_record(line, units)
    if record is None:
        return None
    if not record[1]:
        raise ValueError('Probe contact was not reached')
    return record[0]
