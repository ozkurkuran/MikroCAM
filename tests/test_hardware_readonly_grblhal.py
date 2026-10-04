"""No-hardware tests of the operator-only H2 capture with grblHAL replies (spec 043 FR-012)."""
from unittest.mock import MagicMock

import pytest

from hardware.test_readonly_grbl import COMMANDS, family_of, read_query
from mikrocam.machine.firmware import FirmwareFamily

HAL_I = (b'[VER:1.1f.20261004:]\r\n[OPT:VNMSL,35,1024,3,0]\r\n[AXS:3:XYZ]\r\n'
         b'[NEWOPT:ENUMS,RT+,HOME,SED]\r\n[FIRMWARE:grblHAL]\r\nok\r\n')


def query(command, reply, grblhal):
    transport = MagicMock()
    transport.write.return_value = len(command)
    transport.read.side_effect = [reply[i:i + 7] for i in range(0, len(reply), 7)]
    lines = read_query(transport, command, [], clock=lambda: 0, grblhal=grblhal)
    transport.write.assert_called_once_with(command)
    return lines


def test_identification_reply_selects_the_grblhal_dialect():
    lines = query(b'$I\n', HAL_I, False)
    assert family_of(lines) is FirmwareFamily.GRBLHAL
    assert family_of(['[VER:1.1h.20190830:]', '[OPT:V,15,128]', 'ok']) is FirmwareFamily.GRBL


@pytest.mark.parametrize('command,reply', [
    (b'?', b'<Alarm:11|MPos:0.000,0.000,0.000|Bf:35,1023|FS:0,0|AR|WCO:0.000,0.000,0.000>\r\n'),
    (b'$$\n', b'$0=5.0\r\n$13=0\r\n$300=grblHAL\r\n$396=N/A\r\nok\r\n'),
    (b'$G\n', b'[GC:G0 G54 G17 G21 G90 G94 G40 G49 G98 G50 M5 M9 T0 F0 S0]\r\nok\r\n'),
    (b'$#\n', b'[G54:0.000,0.000,0.000]\r\n[G59.1:0.000,0.000,0.000]\r\n'
              b'[TLO:0.000,0.000,0.000]\r\n[PRB:0.000,0.000,0.000:0]\r\nok\r\n'),
])
def test_grblhal_inventory_records_validate_only_in_grblhal_mode(command, reply):
    assert query(command, reply, True)
    if command != b'?':
        with pytest.raises(ValueError):
            query(command, reply, False)


def test_capture_command_set_is_unchanged_and_readonly():
    assert COMMANDS == (b'?', b'$I\n', b'$$\n', b'$G\n', b'$#\n')


@pytest.mark.parametrize('command,reply', [
    (b'$G\n', b'[GC:G0 G54 G17 G21 G90 G94 G40 G49 G98 G51:XY M5 M9 T0 F0 S0]\r\nok\r\n'),
    (b'$#\n', b'[G54:0.000,0.000,0.000]\r\n[TLO:1.000,0.000,0.000]\r\nok\r\n'),
])
def test_unsupported_grblhal_state_is_reported_by_the_capture(command, reply):
    with pytest.raises(ValueError):
        query(command, reply, True)
