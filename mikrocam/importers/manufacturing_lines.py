"""Bounded Excellon lines shared by evidence inspection and legacy parsing."""
from io import StringIO
from mikrocam.core.manufacturing_models import MAX_MANUFACTURING_BYTES

MAX_LINES = 100000
MAX_LINE_BYTES = 1048576


def excellon_lines(data: bytes) -> tuple[str, ...]:
    """Read at most one bounded line beyond the cap, without a full split allocation."""
    if type(data) is not bytes or not 1 <= len(data) <= MAX_MANUFACTURING_BYTES:
        raise ValueError('Excellon lines require 1..16MiB immutable bytes')
    if any(byte < 32 and byte not in (9, 10, 13) for byte in data):
        raise ValueError('Excellon source contains unsupported control bytes')
    result = []
    with StringIO(data.removeprefix(b'\xef\xbb\xbf').decode('latin1'), newline='') as stream:
        while line := stream.readline(MAX_LINE_BYTES + 1):
            if len(result) >= MAX_LINES:
                raise ValueError('Excellon line count exceeds limit')
            if len(line) > MAX_LINE_BYTES:
                raise ValueError('Excellon line size exceeds limit')
            result.append(line)
    return tuple(result)
