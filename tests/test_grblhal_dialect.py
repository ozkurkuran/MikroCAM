"""grblHAL status sub-states and query-record dialect (spec 043, research R4-R7)."""
import pytest

from mikrocam.machine.grbl import parse_status
from mikrocam.machine.grblhal import normalize_query_line
from mikrocam.machine.job_preparation import query_record
from mikrocam.machine.models import MachineState

POS = '|MPos:0.000,0.000,0.000'


@pytest.mark.parametrize('raw,state', [
    ('Run:1', MachineState.RUNNING), ('Run:2', MachineState.RUNNING),
    ('Alarm:1', MachineState.ALARM), ('Alarm:11', MachineState.ALARM), ('Alarm:255', MachineState.ALARM),
    ('Tool', MachineState.UNKNOWN), ('Hold:0', MachineState.PAUSED), ('Door:3', MachineState.DOOR),
    ('Run:3', MachineState.UNKNOWN), ('Alarm:0', MachineState.UNKNOWN), ('Alarm:256', MachineState.UNKNOWN),
    ('Idle', MachineState.IDLE),
])
def test_grblhal_substates_map_only_documented_codes(raw, state):
    status = parse_status(f'<{raw}{POS}|Bf:35,1023|FS:0,0,0>', grblhal=True)
    assert status.state is state and status.raw_state == raw


@pytest.mark.parametrize('raw', ['Run:1', 'Run:2', 'Alarm:11', 'Tool'])
def test_grbl_mode_is_unchanged_for_grblhal_only_states(raw):
    assert parse_status(f'<{raw}{POS}>').state is MachineState.UNKNOWN


def test_grblhal_valueless_auto_report_field_and_multi_spindle_fields():
    line = f'<Idle{POS}|FS:0,0|SP1:0,,|Ov:100,100,100|A:|AR|MPG:0|H:0|WCO:1.000,2.000,3.000>'
    with pytest.raises(ValueError):
        parse_status(line.replace('|A:', ''))
    status = parse_status(line.replace('|A:', ''), grblhal=True)
    assert status.work_offset == (1., 2., 3.) and status.state is MachineState.IDLE
    with pytest.raises(ValueError):
        parse_status(f'<Idle{POS}|AR>')


@pytest.mark.parametrize('line', [f'<Idle{POS}|AX>', f'<Idle{POS}||FS:0,0>', '<Idle|MPos:1,2,3,4>',
                                  f'<Idle{POS}|SD:5.0,my file.nc>'])
def test_grblhal_mode_still_rejects_malformed_reports(line):
    with pytest.raises(ValueError):
        parse_status(line, grblhal=True)


DEFAULT_GC = '[GC:G0 G54 G17 G21 G90 G94 G40 G49 G98 G50 M5 M9 T0 F0 S0]'


@pytest.mark.parametrize('raw,expected', [
    (DEFAULT_GC, '[GC:G0 G54 G17 G21 G90 G94 G40 G49 M5 M9 T0 F0 S0]'),
    ('[GC:G81 G54 G92 G17 G21 G90 G94 G40 G43.1 G99 G50 M60 M5 M9 M50 M51 M56 T1 F100 S0]',
     '[GC:G54 G17 G21 G90 G94 G40 G43.1 M5 M9 T1 F100 S0]'),
    ('[GC:G5.1 G54 G17 G21 G90 G94 G40 G49 G98 G50 M5 M9 T0 F0]',
     '[GC:G54 G17 G21 G90 G94 G40 G49 M5 M9 T0 F0]'),
])
def test_neutral_modal_words_are_removed(raw, expected):
    assert normalize_query_line(raw) == expected
    assert query_record('modal', normalize_query_line(raw), 'mm')[1].spindle == 'M5'


@pytest.mark.parametrize('word', ['G7', 'G8', 'G43', 'G43.2', 'G41', 'G42.1', 'G51:XY', 'G66', 'G95',
                                  'G96', 'G97', 'G59.1', 'M6', 'M53', 'G710'])
def test_non_neutral_grblhal_modal_words_are_still_rejected(word):
    line = normalize_query_line(DEFAULT_GC.replace('G40', f'G40 {word}'))
    with pytest.raises(ValueError):
        query_record('modal', line, 'mm')


@pytest.mark.parametrize('raw,expected', [
    ('[G59.1:0.000,0.000,0.000]', None), ('[G59.2:1.000,0.000,0.000]', None), ('[G59.3:0,0,0]', None),
    ('[TLO:0.000,0.000,1.500]', '[TLO:1.500]'), ('[TLO:-0.000,0.000,0.000]', '[TLO:0.000]'),
    ('[TLO:2.000]', '[TLO:2.000]'), ('[G54:1.000,2.000,3.000]', '[G54:1.000,2.000,3.000]'),
    ('[G28:0.000,0.000,0.000]', '[G28:0.000,0.000,0.000]'), ('[HOME:0.000,0.000,0.000:7]',
                                                             '[HOME:0.000,0.000,0.000:7]'),
    ('$300=grblHAL', None), ('$396=N/A', None), ('$302=192.168.5.1', None), ('$70=', None),
    ('$13=0', '$13=0'), ('$341=0', '$341=0'), ('$100=250.000', '$100=250.000'),
    ('$N0=', '$N0='), ('[MSG:Info: grblHAL]', '[MSG:Info: grblHAL]'), ('ok', 'ok'),
    ('[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]', '[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]'),
])
def test_parameter_and_settings_dialect(raw, expected):
    assert normalize_query_line(raw) == expected


@pytest.mark.parametrize('line', ['[TLO:1.000,0.000,0.000]', '[TLO:0.000,0.001,0.000]',
                                  '[TLO:0,0,0,0]', '[TLO:x,0,0]'])
def test_non_z_tool_length_offsets_stay_unparseable(line):
    normalized = normalize_query_line(line)
    with pytest.raises(ValueError):
        query_record('parameters', normalized, 'mm')


def test_grblhal_settings_inventory_after_dialect_matches_grbl_records():
    lines = ['$0=5.0', '$13=0', '$30=1000.000', '$31=0.000', '$32=0', '$300=grblHAL', '$396=N/A', '$481=0']
    records = dict(query_record('settings', line, 'mm') for line in map(normalize_query_line, lines)
                   if line is not None)
    assert records == {0: 5., 13: 0., 30: 1000., 31: 0., 32: 0., 481: 0.}
