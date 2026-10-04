"""Pure firmware classification from banner and $I evidence (spec 042, research R1-R3)."""
from dataclasses import FrozenInstanceError

import pytest

from mikrocam.machine.firmware import (
    FirmwareCapabilities, FirmwareFamily, FirmwareObservation, IdentificationPhase,
    banner_consistent, capabilities_for, identify, is_reset_banner, parse_banner)

GRBL_BANNER = "Grbl 1.1h ['$' for help]"
GRBL_11H = ('[VER:1.1h.20190830:]', '[OPT:V,15,128]')
HAL_BANNER = "GrblHAL 1.1f ['$' or '$HELP' for help]"
HAL_FULL = ('[VER:1.1f.20261004:]', '[OPT:VNMSL,35,1024,3,0]', '[AXS:3:XYZ]',
            '[NEWOPT:ENUMS,RT+,HOME,SED]', '[FIRMWARE:grblHAL]', '[SIGNALS:XYZ]',
            '[FREE MEMORY:120K]', '[DRIVER:STM32F407@168MHz]', '[DRIVER VERSION:260901]',
            '[BOARD:BTT SKR-2]', '[MAX STEP RATE:200000 Hz]', '[AUX IO:0,0,0,0]')
FNC4_BANNER = "Grbl 4.1 [FluidNC v4.1.1 (esp32-wifi) '$' for help]"
FNC4 = ('[VER:4.1 FluidNC v4.1.1 (esp32-wifi) :]', '[OPT:PHSEW]', '[CLUSTER:16]')
FNC37 = ('[VER:3.7 FluidNC v3.7.8:]', '[OPT:MPHSEW]')


def test_grbl_11h_source_format_is_motion_capable_with_conservative_budget():
    caps = identify(GRBL_BANNER, GRBL_11H)
    assert caps.family is FirmwareFamily.GRBL
    assert (caps.version, caps.build, caps.protocol, caps.build_info) == ('1.1h', '20190830', '1.1h', '')
    assert (caps.options, caps.planner_blocks, caps.rx_buffer_bytes) == ('V', 15, 128)
    assert caps.streaming_rx_budget == 128 and caps.motion_supported
    assert caps.extra_states == () and caps.extended_options == ()


def test_grbl_wiki_examples_and_existing_fake_reply_are_grbl_11():
    caps = identify('', ('[VER:1.1d.20161014:Some string]', '[OPT:VL,15,128]'))
    assert caps.family is FirmwareFamily.GRBL and caps.build_info == 'Some string'
    assert identify('', ('[VER:1.1d.20161014:]', '[OPT:,15,128]')).options == ''
    fake = identify('', ('[VER:1.1h:FakeGRBL]', '[OPT:V,15,128]'))
    assert fake.family is FirmwareFamily.GRBL and fake.build == '' and fake.build_info == 'FakeGRBL'


def test_grbl_option_letters_from_source_including_plus_and_zero_are_accepted():
    caps = identify('', ('[VER:1.1h.20190830:]', '[OPT:VNMCPZHTAD0SRL+*$#IEW2,15,128]'))
    assert caps.family is FirmwareFamily.GRBL and caps.options.endswith('W2')


def test_grbl_without_opt_has_no_budget_but_keeps_existing_motion_support():
    caps = identify(GRBL_BANNER, ('[VER:1.1h.20190830:]',))
    assert caps.family is FirmwareFamily.GRBL and caps.motion_supported
    assert caps.rx_buffer_bytes is None and caps.streaming_rx_budget is None


def test_grbl_mega_255_byte_buffer_budget_stays_capped_at_128():
    caps = identify('', ('[VER:1.1h.20190830:]', '[OPT:VNM,15,255]'))
    assert caps.rx_buffer_bytes == 255 and caps.streaming_rx_budget == 128


def test_grblhal_full_build_info_is_identified_with_motion_and_capped_budget():
    caps = identify(HAL_BANNER, HAL_FULL)
    assert caps.family is FirmwareFamily.GRBLHAL
    assert (caps.version, caps.build, caps.protocol) == ('1.1f', '20261004', '1.1f')
    assert (caps.planner_blocks, caps.rx_buffer_bytes) == (35, 1024)
    assert caps.extended_options == ('ENUMS', 'RT+', 'HOME', 'SED')
    assert caps.streaming_rx_budget == 128 and caps.motion_supported  # spec 043
    assert caps.note == '' and 'Tool' in caps.extra_states


def test_grblhal_banner_identifies_non_extended_reply():
    caps = identify(HAL_BANNER, ('[VER:1.1f.20240101:]', '[OPT:VN,35,1024]'))
    assert caps.family is FirmwareFamily.GRBLHAL and not caps.motion_supported


def test_grblhal_compatibility_mode_reply_is_not_mistaken_for_gnea_grbl():
    caps = identify("Grbl 1.1f ['$' for help]", ('[VER:1.1f.20240101:]', '[OPT:VN,35,1024]'))
    assert caps.family is FirmwareFamily.UNKNOWN and not caps.motion_supported
    assert caps.version == '1.1f' and '255' in caps.note


@pytest.mark.parametrize('banner,lines', [
    (FNC4_BANNER, FNC4), ('', FNC37), ("Grbl 3.7 [FluidNC v3.7.8 (wifi) '$' for help]", FNC37),
    ("Grbl 3.9 [FluidNC v3.9.9 (main-abc1234-dirty) (esp32-wifi) '$' for help]",
     ('[VER:3.9 FluidNC v3.9.9 (main-abc1234-dirty) (esp32-wifi) :My mill]', '[OPT:PHSEW]', '[CLUSTER:16]'))])
def test_fluidnc_presents_as_grbl_but_is_identified_as_fluidnc(banner, lines):
    caps = identify(banner, lines)
    assert caps.family is FirmwareFamily.FLUIDNC
    assert caps.rx_buffer_bytes is None and caps.streaming_rx_budget is None
    assert caps.motion_supported and caps.note == ''  # Enabled by spec 044 (D3).
    assert 'Starting' in caps.extra_states


def test_fluidnc_version_fields_and_build_info():
    caps = identify('', ('[VER:3.9 FluidNC v3.9.9 (main-abc1234-dirty) (esp32-wifi) :My mill]', '[OPT:PHSEW]'))
    assert (caps.version, caps.protocol, caps.build_info, caps.options) == ('3.9.9', '3.9', 'My mill', 'PHSEW')
    assert identify('', FNC37).version == '3.7.8'


@pytest.mark.parametrize('banner,lines', [
    (FNC4_BANNER, GRBL_11H),                                    # FluidNC greeting, GRBL $I
    ("Grbl 1.1f ['$' for help]", GRBL_11H),                       # version contradiction
    (HAL_BANNER, FNC4),                                          # grblHAL greeting, FluidNC $I
    ('', ('[VER:3.8 FluidNC v3.7.8:]',)),                        # protocol/version mismatch
    ('', FNC4 + ('[FIRMWARE:grblHAL]',)),                       # two families
    ('', ('[VER:1.1f.20240101:]', '[OPT:VN,35,1024]', '[FIRMWARE:Other]')),
    ('', ('[VER:1.3a.20210424:]', '[OPT:VNMHS,15,128]')),          # Grbl_ESP32-like 1.3a
    ('', ('[0.9j.20160316:]',)),                                 # GRBL 0.9 $I
    ('', ()),                                                    # no evidence
    ('', ('[OPT:V,15,128]',)),                                   # OPT without VER
    ('', GRBL_11H + ('[VER:1.1h.20190830:]',)),                  # duplicate VER
    ('', ('[VER:1.1h.20190830:]', '[OPT:V,15,128,3]')),          # extra OPT field without grblHAL
    ('', ('[VER:1.1h.20190830:]', '[OPT:V,15,999]')),            # uint8 overflow
    ('', ('[VER:1.1h.20190830:]', '[OPT:V,0,128]')),             # zero planner
    ('', ('[VER:1.1h.20190830:]', '[OPT:Vx,15,128]')),           # unknown option letter
    ('', GRBL_11H + ('[AXS:3:XYZ]',)),                           # extra tag without grblHAL
    ('', ('[VER:1.1h.20190830:]', '[OPT:V,15,128')),             # unterminated
])
def test_contradictory_incomplete_or_unsupported_evidence_is_unknown(banner, lines):
    caps = identify(banner, lines)
    assert caps.family is FirmwareFamily.UNKNOWN
    assert not caps.motion_supported and caps.streaming_rx_budget is None and caps.note


def test_unknown_keeps_seen_version_token_for_display():
    assert identify('', ('[VER:1.3a.20210424:]', '[OPT:VNMHS,15,128]')).version == '1.3a'


@pytest.mark.parametrize('line,expected', [
    ("Grbl 1.1h ['$' for help]", ('Grbl', '1.1h')),
    (HAL_BANNER, ('GrblHAL', '1.1f')),
    (FNC4_BANNER, ('Grbl', '4.1')),
    ("Grbl 3.4 [FluidNC v3.4.0 (wifi) '$' for help]", ('Grbl', '3.4')),
    ('ok', None), ('Grbl', None), ('Grblx 1.1h', None), ('[MSG:Grbl 1.1h]', None),
])
def test_banner_parsing(line, expected):
    assert parse_banner(line) == expected


@pytest.mark.parametrize('line,reset', [
    ("Grbl 1.1h ['$' for help]", True), (HAL_BANNER, True), (FNC4_BANNER, True),
    ('ok', False), ('[MSG:Reset to continue]', False), ('GrblHALx', False),
])
def test_reset_banner_covers_grbl_and_grblhal(line, reset):
    assert is_reset_banner(line) is reset


def test_banner_consistency_decides_reidentification():
    grbl, hal, fnc = identify('', GRBL_11H), identify(HAL_BANNER, HAL_FULL), identify('', FNC4)
    assert banner_consistent(grbl, GRBL_BANNER)
    assert not banner_consistent(grbl, "Grbl 1.1f ['$' for help]")
    assert not banner_consistent(grbl, HAL_BANNER)
    assert not banner_consistent(grbl, FNC4_BANNER)
    assert banner_consistent(hal, HAL_BANNER) and banner_consistent(hal, "Grbl 1.1f ['$' for help]")
    assert banner_consistent(fnc, FNC4_BANNER)
    assert not banner_consistent(fnc, 'Grbl 4.1 custom message')
    assert not banner_consistent(FirmwareCapabilities(), GRBL_BANNER)


def test_realtime_commands_are_named_per_family_and_0x87_differs():
    grbl = dict(capabilities_for(FirmwareFamily.GRBL).realtime_commands)
    hal = dict(capabilities_for(FirmwareFamily.GRBLHAL).realtime_commands)
    fnc = dict(capabilities_for(FirmwareFamily.FLUIDNC).realtime_commands)
    common = {0x18: 'reset', ord('?'): 'status', ord('~'): 'cycle-start', ord('!'): 'feed-hold',
              0x84: 'safety-door', 0x85: 'jog-cancel'}
    for table in (grbl, hal, fnc):
        assert common.items() <= table.items()
    assert 0x87 not in grbl
    assert hal[0x87] == 'full-status' and fnc[0x87] == 'macro-0'
    assert dict(capabilities_for(FirmwareFamily.UNKNOWN).realtime_commands) == {}


def test_family_profiles_document_status_fields_and_extra_states():
    assert 'WCO' in capabilities_for(FirmwareFamily.GRBL).status_fields
    assert 'FW' in capabilities_for(FirmwareFamily.GRBLHAL).status_fields
    assert capabilities_for(FirmwareFamily.GRBLHAL).extra_states == ('Tool',)
    assert capabilities_for(FirmwareFamily.FLUIDNC).extra_states == ('Starting',)
    assert capabilities_for(FirmwareFamily.GRBL).motion_supported
    assert not capabilities_for(FirmwareFamily.UNKNOWN).motion_supported


def test_capability_record_is_frozen_and_validated():
    caps = identify('', GRBL_11H)
    with pytest.raises(FrozenInstanceError):
        caps.family = FirmwareFamily.UNKNOWN
    with pytest.raises(ValueError):
        FirmwareCapabilities(family='grbl')
    with pytest.raises(ValueError):
        FirmwareCapabilities(family=FirmwareFamily.GRBL, rx_buffer_bytes=0)
    with pytest.raises(ValueError):
        FirmwareCapabilities(family=FirmwareFamily.GRBL, rx_buffer_bytes=64, streaming_rx_budget=128)
    with pytest.raises(ValueError):
        FirmwareCapabilities(family=FirmwareFamily.GRBL, streaming_rx_budget=128)
    with pytest.raises(ValueError):
        FirmwareCapabilities(family=FirmwareFamily.UNKNOWN, motion_supported=True)
    with pytest.raises(ValueError):
        FirmwareCapabilities(note='x' * 257)


def test_observation_motion_requires_identified_supported_profile():
    caps = identify('', GRBL_11H)
    assert FirmwareObservation(IdentificationPhase.IDENTIFIED, caps).motion_allowed
    assert not FirmwareObservation(IdentificationPhase.PENDING, caps).motion_allowed
    assert not FirmwareObservation().motion_allowed
    hal = identify(HAL_BANNER, HAL_FULL)
    assert FirmwareObservation(IdentificationPhase.IDENTIFIED, hal).motion_allowed  # spec 043
    short = identify(HAL_BANNER, ('[VER:1.1f.20240101:]', '[OPT:VN,35,1024]'))
    assert not FirmwareObservation(IdentificationPhase.IDENTIFIED, short).motion_allowed
    with pytest.raises(ValueError):
        FirmwareObservation(IdentificationPhase.IDENTIFIED, FirmwareCapabilities())
    with pytest.raises(ValueError):
        FirmwareObservation(evidence=('x',) * 33)
