"""Wire validation and bounded framing without Qt, serial devices or settings."""
from dataclasses import FrozenInstanceError, replace

import pytest

from mikrocam.machine.grbl import LineFramer, parse_report_units, parse_status
from mikrocam.machine.models import ConnectionState, GrblStatus, MachineSnapshot, MachineState
from mikrocam.machine.transport import Transport


def test_snapshot_defaults_are_unavailable_and_frozen():
    snapshot = MachineSnapshot()
    assert snapshot.connection is ConnectionState.DISCONNECTED
    assert snapshot.state is MachineState.UNKNOWN
    assert snapshot.raw_state == snapshot.diagnostic == ''
    assert snapshot.stale is True
    assert snapshot.report_units is snapshot.last_report_at is None
    assert snapshot.machine_position_mm is snapshot.work_position_mm is snapshot.work_offset_mm is None
    with pytest.raises(FrozenInstanceError):
        snapshot.stale = False


@pytest.mark.parametrize('raw,state', [
    ('Idle', MachineState.IDLE), ('Jog', MachineState.JOG), ('Run', MachineState.RUNNING),
    ('Hold:0', MachineState.PAUSED), ('Hold:1', MachineState.PAUSED),
    ('Alarm', MachineState.ALARM), ('Home', MachineState.HOMING),
    ('Check', MachineState.CHECK), ('Sleep', MachineState.SLEEP),
    ('Door:0', MachineState.DOOR), ('Door:3', MachineState.DOOR),
    ('Error', MachineState.ERROR), ('Vendor:2', MachineState.UNKNOWN),
    ('Probe', MachineState.UNKNOWN), ('idle', MachineState.UNKNOWN),
])
def test_state_mapping_preserves_original_text(raw, state):
    result = parse_status(f'<{raw}|MPos:1,2,3>')
    assert result.state is state
    assert result.raw_state == raw
    assert result.machine_position == (1.0, 2.0, 3.0)
    with pytest.raises(FrozenInstanceError):
        result.raw_state = 'Idle'


def test_work_position_reordered_fields_and_wire_units_unchanged():
    result = parse_status('<Run|FS:120,10000|WCO:1.25,-2,0|WPos:-.5,+2.0,3.|Bf:15,128>')
    assert result.work_position == (-.5, 2., 3.)
    assert result.machine_position is None
    assert result.work_offset == (1.25, -2., 0.)


def test_machine_position_without_offset_does_not_invent_work_position():
    result = parse_status('<Idle|MPos:0,0,0>')
    assert result.machine_position == (0., 0., 0.)
    assert result.work_position is result.work_offset is None


@pytest.mark.parametrize('line', [
    '', 'ok', 'error:1', '[MSG:hello]', 'Idle|MPos:1,2,3', '<Idle>',
    '<|MPos:1,2,3>', '<Idle|WCO:1,2,3>', '<Idle|MPos:1,2,3|WPos:1,2,3>',
    '<Idle|MPos:1,2,3|MPos:1,2,3>', '<Idle|WPos:1,2,3|WPos:1,2,3>',
    '<Idle|MPos:1,2,3|WCO:0,0,0|WCO:0,0,0>', '<Idle|MPos:1,2>',
    '<Idle|MPos:1,2,3,4>', '<Idle|MPos:1,,3>', '<Idle|MPos:NaN,2,3>',
    '<Idle|MPos:inf,2,3>', '<Idle|MPos:1e3,2,3>', '<Idle|MPos:0x1,2,3>',
    '<Idle|MPos:1, 2,3>', '<Idle|MPos:1,2,3|WCO:0,0,nan>',
    '<Idle|MPos:1,2,3||FS:0,0>', '<Idle|MPos:1,2,3|garbage>',
    '<Idle|MPos:1,2,3|>', '<Idle|MPos:1,2,3>tail', ' <Idle|MPos:1,2,3>',
    '<Idle|MPos:1,2,3>\n', '<Idle|MPos:١,2,3>', '<Idle|MPos:1,2,3\x00>',
    '<Idle|MPos:' + '9' * 400 + ',2,3>', '<Idle|MPos:1,2,3|X:' + 'a' * 512 + '>',
])
def test_invalid_status_never_yields_authoritative_coordinates(line):
    with pytest.raises(ValueError):
        parse_status(line)


@pytest.mark.parametrize('line,units', [('$13=0', 'mm'), ('$13=1', 'inch'),
                                      ('$130=100', None), ('ok', None), ('', None)])
def test_report_units_accepts_only_actual_setting(line, units):
    assert parse_report_units(line) == units


@pytest.mark.parametrize('line', ['$13', '$13=', '$13=2', '$13=-1', '$13=0.0', '$13=01',
                                  '$13=1extra', '$13=nan', '$13 =0', '$13=0\n', '$13=０'])
def test_malformed_report_units_rejected(line):
    with pytest.raises(ValueError):
        parse_report_units(line)


def test_framer_handles_crlf_multiple_records_and_partial_chunks():
    framer = LineFramer()
    assert framer.feed(b'<Idle|MPos:1,') == ()
    assert framer.feed(b'2,3>\r') == ('<Idle|MPos:1,2,3>',)
    assert framer.feed(b'\nok\n$13=0\r\nnext') == ('ok', '$13=0')
    assert framer.feed(b'\n') == ('next',)


def test_framer_exact_line_and_chunk_bounds():
    framer = LineFramer()
    assert framer.feed(b'a' * 512 + b'\n') == ('a' * 512,)
    assert framer.feed(b'x\n' * 2048) == ('x',) * 2048
    with pytest.raises(ValueError):
        framer.feed(b'x' * 4097)
    assert framer.feed(b'ok\n') == ('ok',)


def test_framer_oversized_partial_discards_until_delimiter_then_recovers():
    framer = LineFramer()
    assert framer.feed(b'a' * 512) == ()
    with pytest.raises(ValueError):
        framer.feed(b'b')
    assert framer.feed(b'not-a-new-record') == ()
    assert framer.feed(b'\r\nok\n') == ('ok',)


def test_framer_oversized_complete_line_recovers_next_feed():
    framer = LineFramer()
    with pytest.raises(ValueError):
        framer.feed(b'a' * 513 + b'\n')
    assert framer.feed(b'ok\n') == ('ok',)


def test_framer_invalid_ascii_resets_pending_buffer():
    framer = LineFramer()
    framer.feed(b'pending')
    with pytest.raises(ValueError):
        framer.feed(b'\xff')
    assert framer.feed(b'ok\n') == ('ok',)


def test_framer_invalid_ascii_cannot_end_oversized_record_discard():
    framer = LineFramer()
    with pytest.raises(ValueError):
        framer.feed(b'a' * 513)
    with pytest.raises(ValueError):
        framer.feed(b'\xff')
    assert framer.feed(b'<Idle|MPos:1,2,3>') == ()
    assert framer.feed(b'\nok\n') == ('ok',)


def test_framer_invalid_ascii_delimiter_finishes_oversized_discard():
    framer = LineFramer()
    with pytest.raises(ValueError):
        framer.feed(b'a' * 513)
    with pytest.raises(ValueError):
        framer.feed(b'\xff\n')
    assert framer.feed(b'ok\n') == ('ok',)


def test_framer_reset_clears_partial_and_discard_state():
    framer = LineFramer()
    framer.feed(b'pending')
    framer.reset()
    assert framer.feed(b'ok\n') == ('ok',)
    with pytest.raises(ValueError):
        framer.feed(b'a' * 513)
    framer.reset()
    assert framer.feed(b'ok\n') == ('ok',)


@pytest.mark.parametrize('value', [[1., 2., 3.], (1., 2.), (True, 2., 3.),
                                   (float('nan'), 2., 3.), (1., 2., float('inf'))])
def test_frozen_models_reject_mutable_or_invalid_coordinates(value):
    with pytest.raises(ValueError):
        GrblStatus(MachineState.IDLE, 'Idle', value, None, None)
    with pytest.raises(ValueError):
        replace(MachineSnapshot(), machine_position_mm=value)


def test_models_validate_units_timestamp_and_enum_types():
    for kwargs in ({'report_units': 'MM'}, {'last_report_at': float('nan')},
                   {'connection': 'connected'}, {'state': 'Idle'}, {'stale': 1}):
        with pytest.raises(ValueError):
            MachineSnapshot(**kwargs)


def test_model_overflowing_timestamp_is_a_validation_error():
    with pytest.raises(ValueError):
        MachineSnapshot(last_report_at=10 ** 400)


def test_control_characters_in_optional_status_fields_rejected():
    with pytest.raises(ValueError):
        parse_status('<Idle|MPos:1,2,3|Pn:\x7f>')


def test_transport_protocol_has_only_owned_io_boundary():
    assert all(callable(getattr(Transport, name)) for name in ('open', 'read', 'write', 'close'))
    assert not hasattr(Transport, 'send_command')
