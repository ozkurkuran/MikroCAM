"""The single-owner I/O boundary shared by serial and simulated transports."""
from typing import Protocol


class Transport(Protocol):
    """Bounded I/O; implementations never send a connect/reset sequence."""

    def open(self) -> None:
        """Open the explicitly selected channel."""
        ...

    def read(self, size: int) -> bytes:
        """Read at most the positive bounded requested size."""
        ...

    def write(self, data: bytes) -> int:
        """Write bytes and report the actual written count."""
        ...

    def close(self) -> None:
        """Idempotently release the owned channel."""
        ...

    def write_job(self, data: bytes) -> int:
        """Write one separately validated CNC block or owner-controlled hold/resume."""
        ...

    def write_probe(self, data: bytes) -> int:
        """Write one narrowly validated probe or clearance/XY move from the owner."""
        ...
