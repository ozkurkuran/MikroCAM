"""Deterministic, hardware-free GRBL read simulator with explicit fault injection."""


class FakeGRBL:
    """Record exact requests and allow tests to supply delayed/chunked controller data."""

    def __init__(self, *, auto_respond: bool = True, report_units: str = 'mm',
                 status: bytes = b'<Idle|MPos:0,0,0|WCO:0,0,0>\r\n') -> None:
        if report_units not in ('mm', 'inch'):
            raise ValueError('Expected mm or inch report units')
        self.auto_respond = auto_respond
        self.report_units = report_units
        self.status = status
        self.writes: list[bytes] = []
        self.is_open = False
        self.open_count = 0
        self.open_error: OSError | None = None
        self.read_error: OSError | None = None
        self.write_error: OSError | None = None
        self.close_error: OSError | None = None
        self.short_write = False
        self._incoming = bytearray()

    def open(self) -> None:
        if self.is_open:
            raise OSError('Already open')
        if self.open_error:
            raise self.open_error
        self.is_open = True
        self.open_count += 1

    def inject(self, data: bytes) -> None:
        """Queue externally scripted bytes; an empty read represents a delayed reply."""
        if not isinstance(data, bytes) or len(self._incoming) + len(data) > 65536:
            raise ValueError('Simulator input exceeds 65536 bytes')
        self._incoming.extend(data)

    def read(self, size: int) -> bytes:
        if type(size) is not int or not 1 <= size <= 4096:
            raise ValueError('Read size must be 1..4096')
        if not self.is_open:
            raise OSError('Closed')
        if self.read_error:
            raise self.read_error
        data = bytes(self._incoming[:size])
        del self._incoming[:size]
        return data

    def write(self, data: bytes) -> int:
        if not self.is_open:
            raise OSError('Closed')
        if data not in (b'?', b'$$\n'):
            raise ValueError('Only read requests are supported')
        if self.write_error:
            raise self.write_error
        self.writes.append(data)
        if self.short_write:
            return len(data) - 1
        if self.auto_respond:
            if data == b'?':
                self.inject(self.status)
            else:
                self.inject(b'$13=' + (b'0' if self.report_units == 'mm' else b'1') + b'\r\nok\r\n')
        return len(data)

    def close(self) -> None:
        self.is_open = False
        self._incoming.clear()
        if self.close_error:
            raise self.close_error
