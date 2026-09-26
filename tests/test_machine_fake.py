"""Hardware-independent read-only protocol simulator contract."""
import pytest

from mikrocam.machine.fake import FakeGRBL


def test_fake_records_exact_reads_and_returns_partial_chunks():
    fake = FakeGRBL()
    fake.open()
    assert fake.write(b'$$\n') == 3
    assert fake.read(4) == b'$13='
    assert fake.read(4096) == b'0\r\nok\r\n'
    fake.write(b'?')
    assert fake.read(4096).startswith(b'<Idle|MPos:')
    assert fake.writes == [b'$$\n', b'?']
    fake.close()
    fake.close()
    assert not fake.is_open


@pytest.mark.parametrize('command', [b'G0X1\n', b'\x18', b'$X\n', b'$13=0\n', b'?', b''])
def test_fake_requires_open_and_rejects_non_read_commands(command):
    fake = FakeGRBL()
    with pytest.raises(OSError):
        fake.write(command)
    fake.open()
    if command != b'?':
        with pytest.raises(ValueError):
            fake.write(command)


def test_fake_scripted_delay_reset_and_failure():
    fake = FakeGRBL(auto_respond=False)
    fake.open()
    fake.write(b'?')
    assert fake.read(512) == b''
    fake.inject(b'Grbl 1.1h [\'$\' for help]\r\n')
    assert fake.read(4096).startswith(b'Grbl ')
    fake.read_error = OSError('unplugged')
    with pytest.raises(OSError, match='unplugged'):
        fake.read(32)
    fake.close()


@pytest.mark.parametrize('size', [0, -1, 4097, True])
def test_fake_bounds_read(size):
    fake = FakeGRBL()
    fake.open()
    with pytest.raises(ValueError):
        fake.read(size)
