"""Job-specific grammar and planner acceptance are distinct from manual writes."""
from unittest.mock import Mock

import pytest

from mikrocam.bridge.serial_transport import SerialIO
from mikrocam.machine.fake import FakeGRBL


@pytest.mark.parametrize('payload', [b'G1X1F60\n', b'!', b'~'])
def test_serial_job_boundary_is_separate_and_exact(payload):
    transport = SerialIO('COM7')
    connection = Mock()
    connection.write.return_value = len(payload)
    transport._serial = connection
    assert transport.write_job(payload) == len(payload)
    connection.write.assert_called_once_with(payload)
    with pytest.raises(ValueError):
        transport.write(payload)


@pytest.mark.parametrize('payload', [b'G10L20P1X0\n', b'M6\n', b'G1X1\nM3\n', b'$X\n', b'G1X1;!\n',
                                    b'G1 X1\n', b'G1X1\r\n', b'M7\n', b'\x18', b'G1X123456789\n'])
def test_job_boundary_rejects_unreviewable_payload_before_write(payload):
    transport = SerialIO('COM7')
    connection = Mock()
    transport._serial = connection
    with pytest.raises(ValueError):
        transport.write_job(payload)
    connection.write.assert_not_called()


def test_partial_job_write_raises_without_retry():
    transport = SerialIO('COM7')
    connection = Mock()
    connection.write.return_value = 2
    transport._serial = connection
    with pytest.raises(OSError):
        transport.write_job(b'G1X1F60\n')
    assert connection.write.call_count == 1


def test_fake_acceptance_precedes_endpoint_and_hold_does_not_turn_outputs_off():
    fake = FakeGRBL()
    fake.open()
    for block in (b'G21G90G17G94\n', b'S100M3\n', b'G1X1F60\n', b'G1X2\n'):
        fake.write_job(block)
        assert fake.read(4096) == b'ok\r\n'
    assert fake.machine_position == (0.,0.,0.)
    fake.write_job(b'!')
    fake.write(b'?')
    assert b'Hold:1' in fake.read(4096)
    fake.write(b'?')
    assert b'Hold:0' in fake.read(4096)
    assert fake.spindle == 'M3' and fake.machine_position == (0.,0.,0.)
    fake.write_job(b'~')
    fake.write(b'?')
    assert b'Run' in fake.read(4096)
    fake.write(b'?')
    assert b'Idle' in fake.read(4096)
    assert fake.machine_position == (2.,0.,0.)


def test_fake_reset_flushes_queued_job_and_does_not_auto_resume():
    fake = FakeGRBL()
    fake.open()
    fake.write_job(b'G21G90G17G94\n')
    fake.write_job(b'G1X2F60\n')
    fake.read(4096)
    fake.write(b'\x18')
    fake.write(b'?')
    assert fake.machine_position == (0.,0.,0.)
    assert fake.job_writes == [b'G21G90G17G94\n',b'G1X2F60\n']
