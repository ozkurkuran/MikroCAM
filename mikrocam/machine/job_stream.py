"""Original bounded source FIFO; protocol facts only, no firmware implementation."""
from collections import deque
from dataclasses import dataclass, replace
import math
import re


def verified_capacity(records: dict) -> int:
    version, options = records.get("ver", ""), records.get("opt", "")
    if re.fullmatch(r"1\.1[a-z]?(?:\.[0-9]{8})?:[^\r\n]{0,200}", version) is None:
        raise ValueError("Character counting requires verified GRBL 1.1 build evidence")
    match = re.fullmatch(r"[A-Za-z02+*$#]{0,64},([0-9]{1,5}),([0-9]{1,5})", options)
    if match is None or not 1 <= int(match[1]) <= 65535 or not 1 <= int(match[2]) <= 65535:
        raise ValueError("Character counting requires valid reported RX capacity")
    return min(int(match[2]), 128)


@dataclass(frozen=True)
class PendingBlock:
    index: int
    byte_count: int
    deadline: float


class JobStream:
    def __init__(self, capacity: int):
        if type(capacity) is not int or not 1 <= capacity <= 128:
            raise ValueError("Source window capacity must be 1..128 bytes")
        self.capacity = capacity
        self.pending = deque()
        self.used = self.next_index = 0

    def fits(self, wire: bytes) -> bool:
        return self.used + len(wire) <= self.capacity

    def reserve(self, wire: bytes, deadline: float) -> PendingBlock:
        if (type(wire) is not bytes or not wire.endswith(b"\n") or wire.count(b"\n") != 1
                or b"\r" in wire or len(wire) < 2 or len(wire) > self.capacity
                or any(c < 32 or c > 126 for c in wire[:-1])):
            raise ValueError("Source reservation requires one bounded canonical ASCII LF block")
        if not self.fits(wire) or not math.isfinite(deadline):
            raise ValueError("Source reservation exceeds capacity or has invalid deadline")
        entry = PendingBlock(self.next_index, len(wire), deadline)
        self.pending.append(entry)
        self.used += entry.byte_count
        self.next_index += 1
        return entry

    def cancel_last(self, entry: PendingBlock) -> None:
        if not self.pending or self.pending[-1] is not entry:
            raise ValueError("Only the latest proven-unsent reservation may be cancelled")
        self.pending.pop()
        self.used -= entry.byte_count
        self.next_index -= 1

    def ack(self) -> PendingBlock:
        if not self.pending:
            raise ValueError("Unexpected or duplicate source acknowledgement")
        entry = self.pending.popleft()
        self.used -= entry.byte_count
        return entry

    def expired(self, now: float) -> bool:
        return bool(self.pending and now >= self.pending[0].deadline)

    def extend(self, seconds: float) -> None:
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("Hold deadline extension must be finite and nonnegative")
        self.pending = deque(replace(e, deadline=e.deadline + seconds) for e in self.pending)
