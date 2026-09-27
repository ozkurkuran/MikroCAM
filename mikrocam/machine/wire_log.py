"""Bounded raw communication evidence; the controller alone owns the mutable ring."""
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
import math
from time import monotonic


MAX_RECORD_BYTES = 4096
MAX_ENTRIES = 512
MAX_PAYLOAD_BYTES = 262144


def _counter(value: int, label: str, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError(f'{label} must be an integer at least {minimum}')


@dataclass(frozen=True)
class WireRecord:
    sequence: int
    timestamp: float
    direction: str
    payload: bytes
    outcome: str
    diagnostic: str = ''
    omitted_bytes: int = 0

    def __post_init__(self) -> None:
        _counter(self.sequence, 'Sequence', 1)
        _counter(self.omitted_bytes, 'Omitted bytes')
        if isinstance(self.timestamp, bool) or not isinstance(self.timestamp, (int, float)):
            raise ValueError('Timestamp must be a finite number')
        try:
            timestamp = float(self.timestamp)
        except OverflowError as error:
            raise ValueError('Timestamp must be finite') from error
        if not math.isfinite(timestamp):
            raise ValueError('Timestamp must be finite')
        object.__setattr__(self, 'timestamp', timestamp)
        if type(self.payload) is not bytes or len(self.payload) > MAX_RECORD_BYTES:
            raise ValueError('Wire payload must be immutable bytes within record limit')
        if type(self.direction) is not str or type(self.outcome) is not str:
            raise ValueError('Direction and outcome must be exact strings')
        if (self.direction, self.outcome) not in (
                ('TX','complete'), ('TX','uncertain'), ('RX','received'), ('IO','error')):
            raise ValueError('Wire direction and outcome are inconsistent')
        if self.direction == 'IO' and self.payload:
            raise ValueError('Local I/O errors must have empty wire payload')
        if type(self.diagnostic) is not str or len(self.diagnostic) > 256:
            raise ValueError('Wire diagnostic must be text of at most 256 characters')


@dataclass(frozen=True)
class WireSnapshot:
    records: tuple[WireRecord, ...] = ()
    dropped_entries: int = 0
    dropped_bytes: int = 0

    def __post_init__(self) -> None:
        _counter(self.dropped_entries, 'Dropped entries')
        _counter(self.dropped_bytes, 'Dropped bytes')
        if (type(self.records) is not tuple or len(self.records) > MAX_ENTRIES
                or any(type(record) is not WireRecord for record in self.records)):
            raise ValueError('Wire snapshot requires a bounded immutable record tuple')
        if any(first.sequence >= second.sequence for first, second in zip(self.records,self.records[1:])):
            raise ValueError('Wire record sequence must be strictly increasing')
        if sum(len(record.payload) for record in self.records) > MAX_PAYLOAD_BYTES:
            raise ValueError('Wire retained payload exceeds snapshot limit')


class WireLog:
    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        if not callable(clock):
            raise ValueError('Wire clock must be callable')
        self._clock = clock
        self._records: deque[WireRecord] = deque()
        self.reset()

    def append(self, direction: str, payload: bytes, outcome: str, diagnostic: str = '') -> None:
        """Retain one bounded attempt/chunk; count omitted and evicted bytes only once."""
        if type(payload) is not bytes:
            raise ValueError('Wire payload must be immutable bytes')
        retained = payload[:MAX_RECORD_BYTES]
        record = WireRecord(self._sequence+1, self._clock(), direction, retained, outcome,
                            diagnostic, len(payload)-len(retained))
        if direction == 'RX' and not payload:
            return
        self._sequence = record.sequence
        self._records.append(record)
        self._retained_bytes += len(retained)
        self._dropped_bytes += record.omitted_bytes
        while len(self._records) > MAX_ENTRIES or self._retained_bytes > MAX_PAYLOAD_BYTES:
            evicted = self._records.popleft()
            size = len(evicted.payload)
            self._retained_bytes -= size
            self._dropped_entries += 1
            self._dropped_bytes += size

    def snapshot(self) -> WireSnapshot:
        return WireSnapshot(tuple(self._records), self._dropped_entries, self._dropped_bytes)

    def reset(self) -> None:
        """Begin a new explicit connection session; published snapshots remain immutable."""
        self._records.clear()
        self._sequence = self._retained_bytes = self._dropped_entries = self._dropped_bytes = 0
