"""grblHAL motion gate and character-counting budget from $I evidence (spec 043, research R2/R10)."""
import pytest

from mikrocam.machine.firmware import FirmwareFamily, capabilities_for, identify
from mikrocam.machine.job_stream import verified_capacity

HAL_BANNER = "GrblHAL 1.1f ['$' or '$HELP' for help]"
VER = '[VER:1.1f.20261004:]'
OPT = '[OPT:VNMSL+,35,1024,3,0]'
AXS = '[AXS:3:XYZ]'
NEWOPT = '[NEWOPT:ENUMS,RT+,HOME,SED]'
FULL = (VER, OPT, AXS, NEWOPT, '[FIRMWARE:grblHAL]', '[SIGNALS:XYZ]', '[DRIVER:STM32F407@168MHz]',
        '[BOARD:BTT SKR-2]')


def evidence(**replace):
    rows = {'VER': VER, 'OPT': OPT, 'AXS': AXS, 'NEWOPT': NEWOPT}
    rows.update(replace)
    return tuple(row for row in rows.values() if row) + FULL[4:]


def test_default_three_axis_grblhal_supports_motion_with_capped_budget():
    caps = identify(HAL_BANNER, FULL)
    assert caps.family is FirmwareFamily.GRBLHAL and caps.motion_supported
    assert (caps.planner_blocks, caps.rx_buffer_bytes, caps.streaming_rx_budget) == (35, 1024, 128)
    assert caps.note == '' and caps.options == 'VNMSL+'


def test_static_profile_documents_motion_and_extra_state():
    profile = capabilities_for(FirmwareFamily.GRBLHAL)
    assert profile.motion_supported and profile.extra_states == ('Tool',)
    assert dict(profile.realtime_commands)[0x87] == 'full-status'


def test_small_reported_rx_buffer_becomes_the_budget():
    caps = identify('', evidence(OPT='[OPT:VN,35,100,3,0]'))
    assert caps.motion_supported and caps.streaming_rx_budget == 100


@pytest.mark.parametrize('replace,reason', [
    (dict(OPT='[OPT:VN,35,1024,4,0]'), 'axis'),
    (dict(OPT='[OPT:VN,35,1024]'), 'axis'),
    (dict(AXS='[AXS:4:XYZA]'), 'XYZ'),
    (dict(AXS='[AXS:3:XYA]'), 'XYZ'),
    (dict(NEWOPT='[NEWOPT:ENUMS,RT+,LATHE,SED]'), 'lathe'),
    (dict(NEWOPT='[NEWOPT:ENUMS,RT-,SED]'), 'RT+'),
    (dict(NEWOPT=''), 'RT+'),
])
def test_unsupported_board_configuration_keeps_motion_disabled_with_reason(replace, reason):
    caps = identify(HAL_BANNER, evidence(**replace))
    assert caps.family is FirmwareFamily.GRBLHAL and not caps.motion_supported
    assert reason.lower() in caps.note.lower()


def test_non_extended_banner_reply_is_identified_but_motion_needs_axis_evidence():
    caps = identify(HAL_BANNER, ('[VER:1.1f.20240101:]', '[OPT:VN,35,1024]'))
    assert caps.family is FirmwareFamily.GRBLHAL and not caps.motion_supported
    assert 'axis' in caps.note.lower()


def test_compatibility_mode_reply_stays_unknown_and_motion_disabled():
    caps = identify("Grbl 1.1f ['$' for help]", ('[VER:1.1f.20261004:]', '[OPT:VNMSL,35,1024]'))
    assert caps.family is FirmwareFamily.UNKNOWN and not caps.motion_supported
    assert caps.streaming_rx_budget is None


@pytest.mark.parametrize('opt,expected', [('VNMSL+,35,1024,3,0', 128), ('VN0,35,100,3,8', 100),
                                          ('V,15,128', 128)])
def test_job_capacity_accepts_grblhal_axis_and_tool_fields(opt, expected):
    assert verified_capacity({'ver': '1.1f.20261004:', 'opt': opt}) == expected


@pytest.mark.parametrize('opt', ['VN,35,1024,3,0,1', 'VN,35,1024,x', 'VN,35,1024,3,'])
def test_job_capacity_rejects_malformed_extended_fields(opt):
    with pytest.raises(ValueError):
        verified_capacity({'ver': '1.1f.20261004:', 'opt': opt})
