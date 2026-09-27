"""Bounded physical serial transport for supported GRBL read/manual commands."""
from dataclasses import dataclass
import unicodedata

from mikrocam.machine.manual_protocol import validate_command


@dataclass(frozen=True)
class PortInfo:
    device: str
    description: str


def _physical_port(port: object) -> str:
    if (not isinstance(port, str) or not port.strip() or '://' in port
            or any(unicodedata.category(character) == 'Cc' for character in port)):
        raise ValueError('Select a physical serial port without control characters')
    return port


def list_ports() -> tuple[PortInfo, ...]:
    """Refresh operating-system metadata without probing or opening devices."""
    from serial.tools.list_ports import comports
    return tuple(PortInfo(_physical_port(info.device), str(info.description or '')) for info in comports())


class SerialIO:
    """One-owner adapter; construction and unused closure never import/open serial."""

    def __init__(self, port: str):
        self._port = _physical_port(port)
        self._serial = None

    def open(self) -> None:
        if self._serial is not None:
            raise ValueError('Serial transport is already open or awaits successful close')
        import serial
        connection = serial.Serial(port=None, baudrate=115200, timeout=.05, write_timeout=.5)
        self._serial = connection
        try:
            connection.port = self._port
            connection.open()
        except BaseException:
            self.close()
            raise

    def _connection(self):
        if self._serial is None:
            raise OSError('Serial transport is not open')
        return self._serial

    def read(self, size: int) -> bytes:
        if type(size) is not int or not 1 <= size <= 4096:
            raise ValueError('Serial read size must be an integer from 1 to 4096')
        data = self._connection().read(size)
        if not isinstance(data, bytes) or len(data) > size:
            raise OSError('Serial read returned invalid or oversized bytes')
        return data

    def write(self, data: bytes) -> int:
        validate_command(data)
        written = self._connection().write(data)
        if type(written) is not int or written != len(data):
            raise OSError('Serial write did not complete the requested byte count')
        return written

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None
