"""Real simulator behavior for bounded manual GRBL commands; no physical I/O."""
import pytest

from mikrocam.machine.fake import FakeGRBL


def exchange(fake, command):
    assert fake.write(command) == len(command)
    return fake.read(4096)


def opened(**kwargs):
    fake = FakeGRBL(**kwargs)
    fake.open()
    return fake


def test_default_reads_remain_byte_compatible():
    fake = opened()
    assert exchange(fake, b'?') == b'<Idle|MPos:0,0,0|WCO:0,0,0>\r\n'
    assert exchange(fake, b'$$\n') == b'$13=0\r\nok\r\n'
    assert exchange(fake, b'$N\n') == b'$N0=\r\n$N1=\r\nok\r\n'
    modal = exchange(fake, b'$G\n')
    assert modal == b'[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]\r\nok\r\n'


def test_startup_blocks_are_reported_not_executed():
    fake = opened(startup_blocks=('G0 X5', 'M3 S100'))
    assert exchange(fake, b'$N\n') == b'$N0=G0 X5\r\n$N1=M3 S100\r\nok\r\n'
    assert fake.machine_position == (0., 0., 0.)
    assert fake.spindle == 'M5'


@pytest.mark.parametrize('report_units, divisor', [('mm', 1), ('inch', 25.4)])
def test_complete_parameters_and_status_use_report_units_once(report_units, divisor):
    fake = opened(report_units=report_units, machine_position=(25.4, 50.8, 76.2),
                  offsets={'G54': (2.54, 5.08, 7.62)}, g92=(.254, .508, .762), tlo=2.54)
    lines = exchange(fake, b'$#\n').decode().splitlines()
    assert len(lines) == 9 and lines[-1] == 'ok'
    assert [line.split(':')[0] for line in lines[:-1]] == [
        '[G54', '[G55', '[G56', '[G57', '[G58', '[G59', '[G92', '[TLO']
    g54 = tuple(float(x) for x in lines[0][5:-1].split(','))
    assert g54 == pytest.approx(tuple(x / divisor for x in fake.offsets['G54']))
    status = exchange(fake, b'?').decode()
    position = tuple(float(x) for x in status.split('MPos:')[1].split('|')[0].split(','))
    assert position == pytest.approx(tuple(x / divisor for x in fake.machine_position))


def test_output_off_and_g54_preserve_distance_and_units_modes():
    fake = opened(work_system='G55')
    fake.units, fake.distance, fake.spindle, fake.coolant = 'G20', 'G91', 'M3', ('M7', 'M8')
    assert exchange(fake, b'M5 M9\n') == b'ok\r\n'
    assert exchange(fake, b'G54\n') == b'ok\r\n'
    modal = exchange(fake, b'$G\n')
    assert b'G54' in modal and b'G20 G91' in modal and b'M5 M9' in modal


@pytest.mark.parametrize('command, axes', [(b'G10 L20 P1 X0 Y0\n', (0, 1)),
                                         (b'G10 L20 P1 Z0\n', (2,)),
                                         (b'G10 L20 P1 X0 Y0 Z0\n', (0, 1, 2))])
def test_zero_composes_g92_tlo_and_preserves_other_offsets(command, axes):
    fake = opened(machine_position=(10., 20., 30.), offsets={'G54': (1., 2., 3.),
                  'G55': (4., 5., 6.)}, g92=(.5, 1., 1.5), tlo=2.)
    assert exchange(fake, command) == b'ok\r\n'
    expected = [1., 2., 3.]
    for axis in axes:
        expected[axis] = fake.machine_position[axis] - fake.g92[axis] - (fake.tlo if axis == 2 else 0)
    assert fake.offsets['G54'] == tuple(expected)
    assert fake.offsets['G55'] == (4., 5., 6.)
    assert fake.g92 == (.5, 1., 1.5) and fake.tlo == 2.


@pytest.mark.parametrize('axis', ['X', 'Y', 'Z'])
@pytest.mark.parametrize('distance', ['0.1', '-10'])
def test_jog_ack_then_one_jog_report_then_idle_endpoint(axis, distance):
    fake = opened(machine_position=(2., 3., 4.))
    fake.units, fake.distance = 'G20', 'G90'
    assert exchange(fake, f'$J=G21 G91 {axis}{distance} F100\n'.encode()) == b'ok\r\n'
    assert exchange(fake, b'?').startswith(b'<Jog|')
    assert fake.machine_position == (2., 3., 4.)
    assert exchange(fake, b'?').startswith(b'<Idle|')
    expected = [2., 3., 4.]
    expected['XYZ'.index(axis)] += float(distance)
    assert fake.machine_position == tuple(expected)
    assert fake.units == 'G20' and fake.distance == 'G90'


def test_cancel_clears_target_without_ack_or_completion():
    fake = opened(machine_position=(2., 3., 4.))
    exchange(fake, b'$J=G21 G91 X10 F100\n')
    exchange(fake, b'?')
    assert exchange(fake, b'\x85') == b''
    assert exchange(fake, b'?').startswith(b'<Idle|MPos:2,3,4|')


def test_cancel_before_first_status_cannot_leave_a_queued_move():
    fake = opened()
    exchange(fake, b'$J=G21 G91 Y1 F600\n')
    assert exchange(fake, b'\x85') == b''
    for _ in range(3):
        assert exchange(fake, b'?') == b'<Idle|MPos:0,0,0|WCO:0,0,0>\r\n'


def test_cancel_does_not_unlock_external_alarm():
    fake = opened()
    fake.state = 'Alarm'
    assert exchange(fake, b'\x85') == b''
    assert exchange(fake, b'?').startswith(b'<Alarm|')


def test_reset_banner_clears_temporary_modes_but_preserves_stored_offsets():
    fake = opened(offsets={'G54': (1., 2., 3.)}, g92=(1., 1., 1.), tlo=2.)
    fake.units, fake.distance, fake.spindle = 'G20', 'G91', 'M3'
    exchange(fake, b'$J=G21 G91 X10 F100\n')
    assert exchange(fake, b'\x18') == b"Grbl 1.1h ['$' for help]\r\n"
    assert fake.g92 == (0., 0., 0.) and fake.tlo == 0.
    assert fake.units == 'G21' and fake.distance == 'G90' and fake.spindle == 'M5'
    assert fake.offsets['G54'] == (1., 2., 3.)
    assert exchange(fake, b'?').startswith(b'<Idle|')


def test_safety_door_clears_jog_and_outputs_without_reset_banner():
    fake = opened()
    fake.spindle, fake.coolant = 'M3', ('M8',)
    exchange(fake, b'$J=G21 G91 Z1 F300\n')
    assert exchange(fake, b'\x84') == b''
    assert exchange(fake, b'?').startswith(b'<Door:0|')
    assert fake.spindle == 'M5' and fake.coolant == ('M9',)
    assert fake.machine_position == (0., 0., 0.)


def test_static_status_and_scripted_mode_remain_under_test_control():
    fake = opened(status=b'<Alarm|MPos:8,9,10>\n')
    assert exchange(fake, b'?') == b'<Alarm|MPos:8,9,10>\n'
    scripted = opened(auto_respond=False)
    for command in (b'G54\n', b'$J=G21 G91 X1 F100\n', b'\x18', b'$#\n'):
        assert exchange(scripted, command) == b''
    assert scripted.machine_position == (0., 0., 0.)
    scripted.inject(b'ok\n')
    assert scripted.read(4096) == b'ok\n'


def test_short_write_and_write_error_do_not_apply_motion():
    fake = opened()
    fake.short_write = True
    command = b'$J=G21 G91 X1 F100\n'
    assert fake.write(command) == len(command) - 1
    assert fake.read(4096) == b''
    fake.short_write = False
    fake.write_error = OSError('lost')
    with pytest.raises(OSError, match='lost'):
        fake.write(b'$J=G21 G91 X1 F100\n')
    assert fake.machine_position == (0., 0., 0.)


@pytest.mark.parametrize('data', [b'M3\n', b'G0 X1\n', b'$X\n', b'$N0=\n',
                                b'$J=G21 G91 X1 Y1 F100\n', b'?\n', 'G54\n'])
def test_unsupported_bytes_are_rejected_without_recording(data):
    fake = opened()
    with pytest.raises(ValueError):
        fake.write(data)
    assert fake.writes == []


def test_all_auto_responses_use_bounded_incoming_buffer():
    fake = opened()
    fake.inject(b'x' * 65536)
    with pytest.raises(ValueError, match='65536'):
        fake.write(b'$N\n')


@pytest.mark.parametrize('kwargs', [
    {'machine_position': (1., 2., float('nan'))}, {'g92': (1., 2.)},
    {'tlo': True}, {'work_system': 'G60'}, {'offsets': {'G60': (0., 0., 0.)}},
    {'startup_blocks': ('bad\ncommand', '')}, {'startup_blocks': ('x' * 81, '')},
])
def test_invalid_initial_evidence_is_rejected(kwargs):
    with pytest.raises(ValueError):
        FakeGRBL(**kwargs)
