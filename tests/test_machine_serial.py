"""Physical serial adapter behavior without opening any hardware device."""
from dataclasses import FrozenInstanceError
import importlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


class Backend:
    def __init__(self):
        self.port = None
        self.events = []
        self.read_bytes = b''
        self.open_error = self.read_error = self.write_error = self.close_error = None
        self.write_count = 'complete'

    def __setattr__(self, name, value):
        if name in {'dtr', 'rts', 'break_condition'}:
            raise AssertionError('Adapter must not manipulate controller lines')
        super().__setattr__(name, value)

    def open(self):
        self.events.append(('open', self.port))
        if self.open_error:
            raise self.open_error

    def read(self, size):
        self.events.append(('read', size))
        if self.read_error:
            raise self.read_error
        return self.read_bytes

    def write(self, data):
        self.events.append(('write', data))
        if self.write_error:
            raise self.write_error
        return len(data) if self.write_count == 'complete' else self.write_count

    def close(self):
        self.events.append(('close',))
        if self.close_error:
            raise self.close_error


@pytest.fixture
def backend(monkeypatch):
    import serial
    handle = Backend()
    factory = Mock(return_value=handle)
    monkeypatch.setattr(serial, 'Serial', factory)
    return handle, factory


def test_construction_and_unused_close_never_import_or_open_serial(monkeypatch):
    import builtins
    from mikrocam.bridge import serial_transport
    original = builtins.__import__
    def guarded_import(name, *args, **kwargs):
        if name == 'serial' or name.startswith('serial.'):
            pytest.fail('Inert module/constructor must not import hardware backend')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guarded_import)
    module = importlib.reload(serial_transport)
    transport = module.SerialIO('COM7')
    transport.close()
    transport.close()


@pytest.mark.parametrize('port', ['', '  ', None, 7, 'socket://host:23', 'rfc2217://host',
                                  'COM1\n', 'COM1\x00', 'COM1\x7f', 'COM1\u0085'])
def test_invalid_or_network_ports_are_rejected_before_backend_access(backend, port):
    from mikrocam.bridge.serial_transport import SerialIO
    with pytest.raises(ValueError):
        SerialIO(port)
    backend[1].assert_not_called()


@pytest.mark.parametrize('port', ['COM7', r'\\.\COM12', '/dev/ttyUSB0', '/dev/serial/by-id/controller'])
def test_explicit_open_uses_only_selected_port_and_fixed_bounded_configuration(backend, port):
    from mikrocam.bridge.serial_transport import SerialIO
    handle, factory = backend
    transport = SerialIO(port)
    factory.assert_not_called()
    transport.open()
    factory.assert_called_once_with(port=None, baudrate=115200, timeout=.05, write_timeout=.5)
    assert handle.events == [('open', port)]
    with pytest.raises(ValueError):
        transport.open()
    assert handle.events == [('open', port)]
    transport.close()
    transport.close()
    assert handle.events[-1] == ('close',)
    assert handle.events.count(('close',)) == 1


def test_port_busy_releases_attempt_and_can_be_reopened(backend):
    from mikrocam.bridge.serial_transport import SerialIO
    handle, factory = backend
    transport = SerialIO('COM7')
    handle.open_error = OSError('port busy')
    with pytest.raises(OSError, match='port busy'):
        transport.open()
    assert handle.events == [('open', 'COM7'), ('close',)]
    handle.open_error = None
    transport.open()
    transport.close()
    assert factory.call_count == 2


@pytest.mark.parametrize('size', [0, -1, 4097, True, 1.5, None])
def test_read_bound_is_checked_before_any_io(backend, size):
    from mikrocam.bridge.serial_transport import SerialIO
    handle, factory = backend
    transport = SerialIO('COM7')
    with pytest.raises(ValueError):
        transport.read(size)
    assert handle.events == []
    factory.assert_not_called()


def test_read_timeout_is_empty_bytes_and_read_errors_are_visible(backend):
    from mikrocam.bridge.serial_transport import SerialIO
    handle, _ = backend
    transport = SerialIO('COM7')
    transport.open()
    assert transport.read(4096) == b''
    handle.read_bytes = b'<Idle|MPos:1,2,3>\n'
    assert transport.read(100) == handle.read_bytes
    handle.read_error = OSError('read disconnected')
    with pytest.raises(OSError, match='read disconnected'):
        transport.read(1)
    transport.close()


@pytest.mark.parametrize('data', [b'?', b'$$\n'])
def test_only_two_read_requests_can_be_written(backend, data):
    from mikrocam.bridge.serial_transport import SerialIO
    handle, _ = backend
    transport = SerialIO('COM7')
    transport.open()
    assert transport.write(data) == len(data)
    assert handle.events[-1] == ('write', data)
    transport.close()


@pytest.mark.parametrize('data', [b'', b'\r\n', b'$X\n', b'$13=0\n', b'G0 X1\n', b'! ', b'\x18',
                                  b'?\n', b'$$', b'$$\r\n', '?', bytearray(b'?')])
def test_write_allowlist_rejects_commands_without_io(backend, data):
    from mikrocam.bridge.serial_transport import SerialIO
    handle, factory = backend
    transport = SerialIO('COM7')
    with pytest.raises(ValueError):
        transport.write(data)
    assert handle.events == []
    factory.assert_not_called()


@pytest.mark.parametrize('count', [0, 2, True, None, '1'])
def test_short_or_invalid_write_count_is_a_visible_io_failure(backend, count):
    from mikrocam.bridge.serial_transport import SerialIO
    handle, _ = backend
    transport = SerialIO('COM7')
    transport.open()
    handle.write_count = count
    with pytest.raises(OSError, match='write'):
        transport.write(b'?')
    transport.close()


def test_backend_write_failure_is_not_hidden(backend):
    from mikrocam.bridge.serial_transport import SerialIO
    handle, _ = backend
    transport = SerialIO('COM7')
    transport.open()
    handle.write_error = OSError('write timeout')
    with pytest.raises(OSError, match='write timeout'):
        transport.write(b'$$\n')
    transport.close()


def test_close_failure_remains_visible_and_owned_handle_can_be_retried(backend):
    from mikrocam.bridge.serial_transport import SerialIO
    handle, factory = backend
    transport = SerialIO('COM7')
    transport.open()
    handle.close_error = OSError('release failed')
    with pytest.raises(OSError, match='release failed'):
        transport.close()
    with pytest.raises(ValueError):
        transport.open()
    factory.assert_called_once()
    handle.close_error = None
    transport.close()
    transport.close()
    assert handle.events.count(('close',)) == 2


def test_open_and_cleanup_failures_are_both_visible(backend):
    from mikrocam.bridge.serial_transport import SerialIO
    handle, _ = backend
    transport = SerialIO('COM7')
    handle.open_error = OSError('port busy')
    handle.close_error = OSError('release failed')
    with pytest.raises(OSError, match='release failed') as caught:
        transport.open()
    assert 'port busy' in str(caught.value.__context__)
    handle.close_error = None
    transport.close()


@pytest.mark.parametrize('operation', ['read', 'write'])
def test_closed_transport_does_not_implicitly_open(backend, operation):
    from mikrocam.bridge.serial_transport import SerialIO
    transport = SerialIO('COM7')
    with pytest.raises(OSError, match='open'):
        transport.read(1) if operation == 'read' else transport.write(b'?')
    backend[1].assert_not_called()


def test_enumeration_returns_frozen_metadata_refreshes_and_never_opens(backend, monkeypatch):
    from serial.tools import list_ports as enumeration
    from mikrocam.bridge.serial_transport import list_ports, PortInfo
    ports = Mock(side_effect=[[SimpleNamespace(device='COM7', description='USB controller')],
                              [SimpleNamespace(device='COM8', description=None)]])
    monkeypatch.setattr(enumeration, 'comports', ports)
    first, second = list_ports(), list_ports()
    assert first == (PortInfo('COM7', 'USB controller'),)
    assert second == (PortInfo('COM8', ''),)
    with pytest.raises(FrozenInstanceError):
        first[0].description = 'changed'
    assert ports.call_count == 2
    backend[1].assert_not_called()


@pytest.mark.parametrize('response', [b'too large', bytearray(b'x'), None, 'x'])
def test_invalid_backend_read_result_cannot_escape_the_bounded_bytes_boundary(backend, response):
    from mikrocam.bridge.serial_transport import SerialIO
    handle, _ = backend
    transport = SerialIO('COM7')
    transport.open()
    handle.read_bytes = response
    with pytest.raises(OSError, match='read'):
        transport.read(1)
    assert handle.events[-1] == ('read', 1)
    transport.close()


def test_enumeration_failure_is_visible_without_device_open(backend, monkeypatch):
    from serial.tools import list_ports as enumeration
    from mikrocam.bridge.serial_transport import list_ports
    monkeypatch.setattr(enumeration, 'comports', Mock(side_effect=OSError('metadata unavailable')))
    with pytest.raises(OSError, match='metadata unavailable'):
        list_ports()
    backend[1].assert_not_called()
