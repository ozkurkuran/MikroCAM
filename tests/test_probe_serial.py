import pytest
from mikrocam.bridge.serial_transport import SerialIO
from mikrocam.machine.probe_protocol import probe_move
from test_machine_serial import Backend


def test_real_boundary_writes_only_valid_probe_grammar_without_line_controls():
    transport = SerialIO('COM7')
    backend = Backend()
    transport._serial = backend
    data = probe_move(z=-1., feed=30., probing=True)
    assert transport.write_probe(data) == len(data)
    assert backend.events == [('write', data)]
    with pytest.raises(ValueError):
        transport.write_probe(b'M3\n')
    assert backend.events == [('write', data)]


@pytest.mark.parametrize('count', [0,1,True,None,-1])
def test_probe_adapter_short_or_invalid_write_count_is_not_success(count):
    transport = SerialIO('COM7')
    backend = Backend()
    backend.write_count = count
    transport._serial = backend
    with pytest.raises(OSError):
        transport.write_probe(probe_move(z=1.,feed=30.))
