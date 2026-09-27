"""Persistent G54 edits need complete read-back and causal work-coordinate evidence."""
import pytest

from mikrocam.machine.manual_models import SelectG54Request, ZeroRequest
from mikrocam.machine.models import ManualPhase
from test_machine_manual_controller import altered, complete, connected, drive


def test_explicit_g54_selection_changes_no_offset_and_connect_does_not_select():
    controller, fake, clock = connected(work_system='G55')
    before = dict(fake.offsets)
    assert fake.work_system == 'G55' and b'G54\n' not in fake.writes
    controller.request_manual(SelectG54Request())
    complete(controller, clock)
    assert fake.work_system == 'G54' and fake.offsets == before
    assert fake.writes.count(b'G54\n') == 1


@pytest.mark.parametrize('axes', [('X', 'Y'), ('Z',), ('X', 'Y', 'Z')])
@pytest.mark.parametrize('report_units', ['mm', 'inch'])
def test_zero_selected_axes_preserves_other_offsets_g92_and_tlo(axes, report_units):
    offsets = {f'G{i}': (float(i), float(i + 1), float(i + 2)) for i in range(54, 60)}
    controller, fake, clock = connected(machine_position=(100., 200., 300.), offsets=offsets,
                                         g92=(.25, .5, .75), tlo=1.25, report_units=report_units)
    original = dict(fake.offsets)
    before_work = controller.snapshot().work_position_mm
    controller.request_manual(ZeroRequest(axes))
    result = complete(controller, clock)
    for index, axis in enumerate('XYZ'):
        expected = 0.0 if axis in axes else before_work[index]
        assert result.work_position_mm[index] == pytest.approx(expected, abs=.005)
        if axis not in axes:
            assert fake.offsets['G54'][index] == original['G54'][index]
    assert {key: value for key, value in fake.offsets.items() if key != 'G54'} == {
        key: value for key, value in original.items() if key != 'G54'}
    assert fake.g92 == (.25, .5, .75) and fake.tlo == 1.25
    expected_command = ('G10 L20 P1 ' + ' '.join(f'{axis}0' for axis in axes) + '\n').encode()
    assert [line for line in fake.writes if line.startswith(b'G10')] == [expected_command]
    assert fake.writes.count(b'$#\n') == 2


def test_zero_does_not_implicitly_select_g54():
    controller, fake, clock = connected(work_system='G55')
    controller.request_manual(ZeroRequest(('Z',)))
    result = drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.FAILED)
    assert 'G54' in result.manual.diagnostic
    assert b'G54\n' not in fake.writes and not any(line.startswith(b'G10') for line in fake.writes)


@pytest.mark.parametrize('reply', [b'[G54:0,0,0]\nok\n', b'[G54:NaN,0,0]\nok\n',
                                  b'[G54:0,0,0]\n[G54:0,0,0]\nok\n', b'error:8\n'])
def test_bad_prewrite_parameter_inventory_never_changes_eeprom(reply):
    controller, fake, clock = altered(b'$#\n', reply)
    controller.request_manual(ZeroRequest(('X', 'Y')))
    drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.FAILED)
    assert not any(line.startswith(b'G10') for line in fake.writes)


@pytest.mark.parametrize('reply', [b'error:8\n', b'', b'ok\nok\n'])
def test_failed_or_ambiguous_zero_ack_is_not_replayed(reply):
    controller, fake, clock = altered(b'G10 L20 P1 Z0\n', reply)
    controller.request_manual(ZeroRequest(('Z',)))
    result = drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.FAILED)
    assert fake.writes.count(b'G10 L20 P1 Z0\n') == 1
    assert not result.manual.can_zero
    for _ in range(12):
        clock.now += .25
        controller.tick()
    assert fake.writes.count(b'G10 L20 P1 Z0\n') == 1
