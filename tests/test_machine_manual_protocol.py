"""Exact bounded commands and independent controller evidence, without hardware."""
from dataclasses import FrozenInstanceError, replace
from itertools import product

import pytest

from mikrocam.machine.manual_models import (JogRequest, ModalState, ParameterRecord,
                                          SelectG54Request, StartupRecord, ZeroRequest)
from mikrocam.machine.manual_protocol import (encode_jog, encode_zero, parse_modal,
                                            parse_parameter, parse_startup,
                                            validate_command, verify_zero)
from mikrocam.machine.models import MachineSnapshot, ManualObservation, ManualPhase


@pytest.mark.parametrize('axis,distance,feed', list(product('XYZ', (.1, -.1, 1, -1, 10, -10), (100, 300, 600))))
def test_every_jog_preset_has_exact_canonical_mm_incremental_bytes(axis, distance, feed):
    request = JogRequest(axis, distance, feed)
    encoded = f'$J=G21 G91 {axis}{distance:g} F{feed}\n'.encode('ascii')
    assert encode_jog(request) == encoded
    assert validate_command(encoded) is None


@pytest.mark.parametrize('axes,command', [(('X', 'Y'), b'G10 L20 P1 X0 Y0\n'),
                                        (('Z',), b'G10 L20 P1 Z0\n'),
                                        (('X', 'Y', 'Z'), b'G10 L20 P1 X0 Y0 Z0\n')])
def test_zero_only_encodes_exact_chosen_axes(axes, command):
    assert encode_zero(ZeroRequest(axes)) == command
    validate_command(command)


@pytest.mark.parametrize('values', [('x', 1, 100), ('A', 1, 100), ('X', 0, 100),
                                   ('X', .2, 100), ('X', 11, 100), ('X', True, 100),
                                   ('X', 1, True), ('X', 1, 200), ('X', float('nan'), 100),
                                   ('X', 1, float('inf')), ([], 1, 100)])
def test_invalid_jog_values_rejected_at_construction(values):
    with pytest.raises(ValueError):
        JogRequest(*values)


@pytest.mark.parametrize('axes', [('X',), ('Y', 'X'), (), ['X', 'Y'], ('X', 'Y', 'Z', 'A'), 'XY'])
def test_invalid_zero_axes_rejected(axes):
    with pytest.raises(ValueError):
        ZeroRequest(axes)


@pytest.mark.parametrize('command', [b'?', b'$$\n', b'$G\n', b'$#\n', b'$N\n', b'M5 M9\n',
                                    b'G54\n', b'\x85', b'\x18', b'\x84'])
def test_fixed_commands_and_realtime_bytes_allowed(command):
    validate_command(command)


@pytest.mark.parametrize('command', [b'', b'??', '?', bytearray(b'?'), b'$13=0\n', b'$N0=\n',
                                    b'G0 X1\n', b'M3\n', b'M4\n', b'$H\n', b'$X\n', b'~',
                                    b'!', b'G55\n', b'$J=G21 G91 X0.10 F100\n',
                                    b'$J=G21 G91 X+1 F100\n', b'$J=G21 G91 X1 F100.0\n',
                                    b'$J=G21 G91 X11 F100\n', b'$J=G21 G91 X1 F601\n',
                                    b'$J=G20 G91 X1 F100\n', b'$J=G21 G90 X1 F100\n',
                                    b'$J=G21 G91 X1 Y1 F100\n', b'G10 L20 P1 X0\n',
                                    b'G10 L20 P2 X0 Y0\n', b'G10 L20 P1 X1 Y0\n',
                                    b'M5 M9\r\n', b'M5 M9 \n', b'?\n', b'\x85\n',
                                    b'G54\nM3\n', b'X' * 81])
def test_all_noncanonical_or_unsupported_commands_rejected(command):
    with pytest.raises(ValueError):
        validate_command(command)


def test_values_and_observations_are_frozen_with_safe_defaults():
    for value in (JogRequest('X', 1, 100), ZeroRequest(('Z',)), SelectG54Request(),
                  StartupRecord(0, ''), ParameterRecord('TLO', 0), ManualObservation()):
        with pytest.raises(FrozenInstanceError):
            value.extra = 1
    observation = MachineSnapshot().manual
    assert observation == ManualObservation()
    assert observation.phase is ManualPhase.READY and observation.action is None
    assert not any((observation.can_jog, observation.can_zero, observation.can_select_g54,
                    observation.can_cancel, observation.stop_unverified))


@pytest.mark.parametrize('kwargs', [{'phase': 'ready'}, {'can_jog': 1}, {'action': []},
                                    {'diagnostic': 'x' * 257}, {'stop_unverified': 0}])
def test_invalid_observation_rejected(kwargs):
    with pytest.raises(ValueError):
        ManualObservation(**kwargs)
    with pytest.raises(ValueError):
        MachineSnapshot(manual={})


def test_modal_full_and_reordered_records_preserve_wire_modes():
    expected = ModalState('G55', 'G20', 'G91', 'M5', ('M9',))
    assert parse_modal('[GC:G0 G55 G17 G20 G91 G94 M5 M9 T0 F100 S0]') == expected
    assert parse_modal('[GC:M9 G91 G20 M5 G55]') == expected
    assert parse_modal('[GC:G54 G21 G90 M3 M7 M8]').coolant == ('M7', 'M8')
    assert parse_modal('ok') is None


@pytest.mark.parametrize('line', ['[GC:G54 G21 G90 M5]', '[GC:G54 G55 G21 G90 M5 M9]',
                                  '[GC:G54 G21 G21 G90 M5 M9]', '[GC:G54 G21 G90 M5 M3 M9]',
                                  '[GC:G54 G21 G90 M5 M9 M7]', '[GC:G54 G21 G90 M5 M7 M7]',
                                  '[GC:G54 G21 G90 M5 M9 Fnan]', '[GC:G54 G21 G90 M5 M9 S1e3]',
                                  '[GC:G54 G21 G90 M5 M9 F-1]', '[GC:G54 G21 G90 M5 M9 T.5]',
                                  '[GC:G54 G21 G90 M5 M9 G60]', '[GC:G54 G21 G90 M5 M9]tail',
                                  '[GC:G54  G21 G90 M5 M9]', '[GC:G54 G21 G90 M5 M9\x00]',
                                  '[GC:G54 G21 G90 M5 M9 F' + '9' * 400 + ']', '[GC:'])
def test_malformed_modal_evidence_rejected(line):
    with pytest.raises(ValueError):
        parse_modal(line)


@pytest.mark.parametrize('extra', ['G0 G1', 'G17 G18', 'G93 G94', 'G43.1 G49', 'T0 T1'])
def test_conflicting_optional_modal_groups_rejected(extra):
    with pytest.raises(ValueError):
        parse_modal(f'[GC:G54 G21 G90 M5 M9 {extra}]')


@pytest.mark.parametrize('units,factor', [('mm', 1.), ('inch', 25.4)])
def test_parameter_parser_normalizes_xyz_and_tlo_once(units, factor):
    assert parse_parameter('[G54:1,-2,.5]', units) == ParameterRecord('G54', (factor, -2*factor, .5*factor))
    assert parse_parameter('[TLO:-1.5]', units) == ParameterRecord('TLO', -1.5*factor)
    for name in ('G55', 'G56', 'G57', 'G58', 'G59', 'G92'):
        assert parse_parameter(f'[{name}:0,0,0]', units).value == (0., 0., 0.)
    assert parse_parameter('[PRB:1,2,3:1]', units) is None
    assert parse_parameter('[MSG:hello]', units) is None


@pytest.mark.parametrize('line,units', [('[G54:1,2]', 'mm'), ('[G54:1,2,nan]', 'mm'),
                                        ('[G92:1,2,3]junk', 'mm'), ('[TLO:1,2,3]', 'mm'),
                                        ('[G54:1e2,2,3]', 'mm'), ('[TLO:inf]', 'mm'),
                                        ('[G54:1,2,3]', None), ('[G54:1,2,3]', 'MM'),
                                        ('[TLO:'+'9'*308+']', 'inch'), ('[G54]', 'mm')])
def test_parameter_invalid_or_overflowing_evidence_rejected(line, units):
    with pytest.raises(ValueError):
        parse_parameter(line, units)


@pytest.mark.parametrize('line', ['[G54 1,2,3]', '[TLO=0]', '[G92 0,0,0]'])
def test_malformed_recognized_parameter_prefix_is_not_unrelated(line):
    with pytest.raises(ValueError):
        parse_parameter(line, 'mm')


def test_startup_records_keep_nonempty_data_without_executing_it():
    assert parse_startup('$N0=') == StartupRecord(0, '')
    assert parse_startup('$N1=G0 X10 M3') == StartupRecord(1, 'G0 X10 M3')
    assert parse_startup('$N1=' + 'x'*80).block == 'x'*80
    assert parse_startup('ok') is None
    assert parse_startup('$130=1') is None


@pytest.mark.parametrize('line', ['$N0', '$N1=', '$N2=', '$N0='+ 'x'*81,
                                  '$N0=G0\nM3', '$N1=\xff', '$N1=\x7f'])
def test_invalid_startup_records_rejected(line):
    if line == '$N1=':
        assert parse_startup(line) == StartupRecord(1, '')
    else:
        with pytest.raises(ValueError):
            parse_startup(line)


@pytest.mark.parametrize('factory,args', [(ModalState, ('G60', 'G21', 'G90', 'M5', ('M9',))),
                                          (ModalState, ('G54', 'G21', 'G90', 'M5', ['M9'])),
                                          (ModalState, ('G54', 'G21', 'G90', 'M5', ('M9', 'M7'))),
                                          (ParameterRecord, ('G54', [1.,2.,3.])),
                                          (ParameterRecord, ('G54', (True,2.,3.))),
                                          (ParameterRecord, ('TLO', True)), (ParameterRecord, ('TLO', float('nan'))),
                                          (ParameterRecord, ('G60', (0.,0.,0.))),
                                          (StartupRecord, (True, '')), (StartupRecord, (2, '')),
                                          (StartupRecord, (0, []))])
def test_model_construction_rejects_mutable_invalid_or_boolean_values(factory, args):
    with pytest.raises(ValueError):
        factory(*args)


def inventory(g54=(1.,2.,3.), g92=(.5,1.,2.), tlo=4.):
    return tuple(ParameterRecord(name, g54 if name=='G54' else g92 if name=='G92' else (0.,0.,0.))
                 for name in ('G54','G55','G56','G57','G58','G59','G92')) + (ParameterRecord('TLO',tlo),)


@pytest.mark.parametrize('axes', [('X','Y'), ('Z',), ('X','Y','Z')])
def test_verify_zero_analytic_offset_composition_preserves_unselected_axes(axes):
    before = inventory()
    g54 = tuple((10.-.5,20.-1.,30.-2.-4.)[i] if axis in axes else (1.,2.,3.)[i]
                for i,axis in enumerate('XYZ'))
    after = inventory(g54)
    assert verify_zero(before, after, (10.,20.,30.), axes) is None
    assert before == inventory()


def test_verify_zero_tolerance_is_fixed_and_complete_unique_evidence_required():
    before = inventory()
    after = inventory((9.5,19.,3.))
    verify_zero(before, inventory((9.5049,19.,3.)), (10.,20.,30.), ('X','Y'))
    for invalid in (inventory((9.5051,19.,3.)), after[:-1], after + (after[0],),
                    tuple(replace(row,value=(.006,0.,0.)) if row.name=='G55' else row for row in after),
                    inventory((9.5,19.,3.006)), inventory((9.5,19.,3.),tlo=4.006)):
        with pytest.raises(ValueError):
            verify_zero(before, invalid, (10.,20.,30.), ('X','Y'))
    for invalid_before in (before[:-1], before+(before[0],), list(before)):
        with pytest.raises(ValueError):
            verify_zero(invalid_before, after, (10.,20.,30.), ('X','Y'))
    with pytest.raises(ValueError):
        verify_zero(before, after, [10.,20.,30.], ('X','Y'))


def test_zero_exact_tolerance_boundary_and_unchanged_temporary_offset_required():
    before = inventory((0.,0.,0.), (0.,0.,0.), 0.)
    verify_zero(before, inventory((.005,0.,0.), (0.,0.,0.), 0.), (0.,0.,0.), ('X','Y'))
    with pytest.raises(ValueError):
        verify_zero(before, inventory((0.,0.,0.), (.006,0.,0.), 0.), (0.,0.,0.), ('X','Y'))


def test_encoders_recheck_typed_values_and_reject_wrong_requests():
    for encode in (encode_jog, encode_zero):
        with pytest.raises(ValueError):
            encode('G0 X1')
    request = JogRequest('X', 1, 100)
    object.__setattr__(request, 'distance_mm', 20)
    with pytest.raises(ValueError):
        encode_jog(request)
