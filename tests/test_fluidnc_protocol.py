"""Pure FluidNC serial protocol differences (spec 044, research R1-R9)."""
import pytest

from mikrocam.machine import fluidnc
from mikrocam.machine.firmware import FirmwareFamily, capabilities_for, identify
from mikrocam.machine.job_protocol import validate_job_command
from mikrocam.machine.manual_protocol import parse_parameter, validate_command
from mikrocam.machine.probe_protocol import validate_probe_command
from mikrocam.machine.startup_evidence import StartupEvidence
from test_job_control import prepared

FNC4 = ('[VER:4.1 FluidNC v4.1.1 (esp32-wifi) :]', '[OPT:PHSEW]', '[CLUSTER:16]')
FNC39 = ('[VER:3.9 FluidNC v3.9.9:]', '[OPT:PHSEW]')
ROM = ('ets Jul 29 2019 12:21:46', 'rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)',
       'ESP-ROM:esp32s3-20210327', '[MSG:INFO: FluidNC v4.1.1 https://github.com/bdring/FluidNC]')


@pytest.mark.parametrize('lines', [FNC4, FNC39, ('[VER:3.7 FluidNC v3.7.8:]', '[OPT:MPHSEW]')])
def test_fluidnc_3x_and_4x_enable_motion_without_rx_budget(lines):
    caps = identify('', lines)
    assert caps.family is FirmwareFamily.FLUIDNC and caps.motion_supported
    assert caps.rx_buffer_bytes is None and caps.streaming_rx_budget is None
    assert 'Starting' in caps.extra_states


def test_other_fluidnc_major_versions_are_identified_but_motion_stays_disabled():
    caps = identify('', ('[VER:5.0 FluidNC v5.0.1 (esp32-wifi) :]', '[OPT:PHSEW]'))
    assert caps.family is FirmwareFamily.FLUIDNC and not caps.motion_supported
    assert '5.0' in caps.note and caps.streaming_rx_budget is None


def test_fluidnc_macro_bytes_are_named_and_can_never_be_written():
    commands = dict(capabilities_for(FirmwareFamily.FLUIDNC).realtime_commands)
    assert [commands[code] for code in (0x87, 0x88, 0x89, 0x8A)] == ['macro-0', 'macro-1', 'macro-2', 'macro-3']
    for code in (0x87, 0x88, 0x89, 0x8A):
        for validator in (validate_command, validate_job_command, validate_probe_command):
            with pytest.raises(ValueError):
                validator(bytes([code]))


@pytest.mark.parametrize('command', [*fluidnc.STARTUP_QUERIES, b'$CD\n'])
def test_fluidnc_readonly_queries_are_on_the_exact_allowlist(command):
    validate_command(command)


@pytest.mark.parametrize('command', [b'$RI=0\n', b'$/macros/after_reset=G0X0\n', b'$CD=x\n',
                                     b'$/macros/macro0\n', b'$X\n', b'$H\n', b'$Config/Dump\n'])
def test_fluidnc_writes_and_unsupported_commands_stay_rejected(command):
    with pytest.raises(ValueError):
        validate_command(command)


@pytest.mark.parametrize('line', ROM)
def test_boot_markers_are_independent_of_the_custom_greeting(line):
    assert fluidnc.is_boot_marker(line)


@pytest.mark.parametrize('line', ["Grbl 4.1 [FluidNC v4.1.1 (esp32-wifi) '$' for help]", '[MSG:INFO: Machine x]',
                                  '[MSG: Machine: Fake]', 'ok', '<Idle|MPos:0,0,0>', 'Hello mill'])
def test_ordinary_lines_are_not_boot_markers(line):
    assert not fluidnc.is_boot_marker(line)


@pytest.mark.parametrize('line,free', [('My mill ready', True), ('  x:', True), ('configsip: 0', True),
                                       ('ok', False), ('error:3', False), ('ALARM:14', False),
                                       ('<Idle|MPos:0,0,0>', False), ('[MSG:INFO: x]', False),
                                       ('$13=0', False), ('>G54:ok', False), ('', False)])
def test_free_text_is_anything_not_shaped_like_a_protocol_record(line, free):
    assert fluidnc.is_free_text(line) is free


@pytest.mark.parametrize('line,record', [
    ('$/macros/startup_line0=', ('startup_line0', '')),
    ('$/macros/startup_line1=G54', ('startup_line1', 'G54')),
    ('$/macros/after_reset=G0 Z5&M3', ('after_reset', 'G0 Z5&M3')),
    ('[MSG:INFO: uart_channel0 auto reporting is off]', ('report_interval', 0)),
    ('[MSG:INFO: uart_channel0 auto report interval is 200 ms]', ('report_interval', 200)),
    ('[MSG:INFO: Something else]', None), ('ok', None)])
def test_startup_records_from_macro_readback_and_report_interval(line, record):
    assert fluidnc.parse_startup_record(line) == record


@pytest.mark.parametrize('line', ['$/macros/macro0=', '$/macros/after_unlock=', '$N0=', '$13=0', 'é'])
def test_unexpected_startup_records_fail_closed(line):
    with pytest.raises(ValueError):
        fluidnc.parse_startup_record(line)


EMPTY = {'startup_line0': '', 'startup_line1': '', 'after_reset': '', 'report_interval': 0}


@pytest.mark.parametrize('change,needle', [
    ({'after_reset': 'G0 X0'}, 'after_reset'), ({'startup_line0': 'G54'}, 'startup_line0'),
    ({'report_interval': 100}, '$RI'), ({'report_interval': None}, 'Message/Level'),
    ({'after_reset': None}, 'incomplete')])
def test_startup_problem_requires_empty_macros_and_auto_report_off(change, needle):
    records = dict(EMPTY)
    for key, value in change.items():
        if value is None:
            del records[key]
        else:
            records[key] = value
    assert needle in fluidnc.startup_problem(records)
    assert fluidnc.startup_problem(EMPTY) is None


def test_grbl_startup_evidence_keeps_the_single_n_query():
    evidence = StartupEvidence(FirmwareFamily.GRBL)
    assert evidence.next_query() == b'$N\n' and evidence.next_query() is None
    assert evidence.record('$N0=') == (0, '') and evidence.record('[MSG:x]') is None
    evidence.add({0: '', 1: ''})
    assert evidence.problem('grbl message') is None
    other = StartupEvidence(FirmwareFamily.GRBL)
    other.add({0: 'G54', 1: ''})
    assert other.problem('grbl message') == 'grbl message'


def test_fluidnc_startup_evidence_walks_three_macros_then_report_interval():
    evidence = StartupEvidence(FirmwareFamily.FLUIDNC)
    queries = []
    while (query := evidence.next_query()) is not None:
        queries.append(query)
    assert queries == [b'$/macros/startup_line0\n', b'$/macros/startup_line1\n',
                       b'$/macros/after_reset\n', b'$RI\n']
    for key, value in EMPTY.items():
        evidence.add({key: value})
    assert evidence.problem('unused') is None
    with pytest.raises(ValueError):
        evidence.add({'after_reset': ''})


@pytest.mark.parametrize('line,value', [('[TLO:1.500]', 1.5), ('[TLO:0.000,0.000,-2.250]', -2.25)])
def test_tlo_scalar_or_fluidnc_v4_vector_with_zero_xy(line, value):
    assert parse_parameter(line, 'mm').value == value


@pytest.mark.parametrize('line', ['[TLO:0.100,0.000,1.000]', '[TLO:0,0,1,0]', '[TLO:0,1]'])
def test_tlo_vector_with_xy_or_extra_axes_is_rejected(line):
    with pytest.raises(ValueError):
        parse_parameter(line, 'mm')


def test_fluidnc_settings_use_proxies_and_never_require_31():
    job = prepared('G21 G90 G17 G94\nM3 S800\nG1 X1 F60\nM5\nM2\n')
    fluidnc.verify_settings({13: 0., 30: 1000., 32: 0., 10: 1., 20: 0.}, job, 'mm')
    fluidnc.verify_settings({13: 1., 30: 1000., 32: 0.}, job, 'inch')
    for records, needle in (({13: 0., 30: 1000.}, 'Missing'), ({13: 0., 30: 1000., 32: 1.}, 'laser'),
                            ({13: 1., 30: 1000., 32: 0.}, 'report units'),
                            ({13: 0., 30: 500., 32: 0.}, 'outside'), ({13: 0., 30: 0., 32: 0.}, 'Invalid')):
        with pytest.raises(ValueError, match=needle):
            fluidnc.verify_settings(records, job, 'mm')


@pytest.mark.parametrize('protocol,supported', [('3.9', True), ('4.1', True), ('3.4', True), ('5.0', False),
                                                ('2.0', False), ('', False)])
def test_motion_version_gate(protocol, supported):
    assert fluidnc.motion_version_supported(protocol) is supported
