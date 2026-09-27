"""Adversarial real-controller read-back and phase-specific disconnect behavior."""
import pytest

from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.manual_models import JogRequest, SelectG54Request, ZeroRequest
from mikrocam.machine.models import ConnectionState, ManualPhase
from test_machine_manual_controller import Clock, connected, drive


def assert_no_replay(controller, fake, clock, command):
    assert fake.writes.count(command) == 1
    for _ in range(16):
        clock.now += .25
        controller.tick()
        assert controller.snapshot().manual.phase is not ManualPhase.COMPLETE
    assert fake.writes.count(command) == 1


@pytest.mark.parametrize('report_units', ['mm', 'inch'])
@pytest.mark.parametrize('position', [(1.02, 0., 0.), (1., .02, 0.), (1., 0., -.02)])
def test_wrong_terminal_endpoint_on_any_axis_fails_without_motion_replay(report_units, position):
    controller, fake, clock = connected(report_units=report_units)
    controller.request_manual(JogRequest('X', 1., 100.))
    drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.MOVING)
    divisor = 25.4 if report_units == 'inch' else 1.
    xyz = ','.join(format(value / divisor, '.12g') for value in position)
    fake.status = f'<Idle|MPos:{xyz}|WCO:0,0,0>\n'.encode('ascii')
    result = drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.FAILED)
    assert 'unexpected position' in result.manual.diagnostic.lower()
    assert result.manual.stop_unverified and not result.manual.can_jog
    assert_no_replay(controller, fake, clock, b'$J=G21 G91 X1 F100\n')


class CorruptAfterParameters(FakeGRBL):
    """Change only the actual post-write query reply, retaining real pre-write evidence."""

    def __init__(self, fault, report_units):
        super().__init__(report_units=report_units, machine_position=(10., 20., 30.),
                         offsets={'G54': (1., 2., 3.), 'G55': (4., 5., 6.)},
                         g92=(.25, .5, .75), tlo=1.25)
        self.fault, self.parameter_queries = fault, 0

    def write(self, data):
        start = len(self._incoming)
        result = super().write(data)
        if data != b'$#\n':
            return result
        self.parameter_queries += 1
        if self.parameter_queries != 2:
            return result
        rows = bytes(self._incoming[start:]).decode('ascii').splitlines()
        if self.fault == 'missing':
            rows = [row for row in rows if not row.startswith('[G59:')]
        elif self.fault == 'duplicate':
            rows.insert(1, rows[0])
        elif self.fault == 'nonfinite':
            rows[0] = '[G54:NaN,0,0]'
        elif self.fault == 'missing_ack':
            rows.remove('ok')
        else:
            name, axis = {'selected': ('G54', 0), 'omitted': ('G54', 2),
                          'other_wcs': ('G55', 0), 'g92': ('G92', 1),
                          'tlo': ('TLO', 0)}[self.fault]
            index = next(i for i, row in enumerate(rows) if row.startswith(f'[{name}:'))
            values = [float(value) for value in rows[index].split(':')[1][:-1].split(',')]
            values[axis] += .1 if self.report_units == 'mm' else .1 / 25.4
            rows[index] = f'[{name}:' + ','.join(format(value, '.12g') for value in values) + ']'
        del self._incoming[start:]
        self.inject(('\n'.join(rows) + '\n').encode('ascii'))
        return result


@pytest.mark.parametrize('report_units', ['mm', 'inch'])
@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'nonfinite', 'missing_ack',
                                  'selected', 'omitted', 'other_wcs', 'g92', 'tlo'])
def test_postwrite_inventory_fault_cannot_claim_zero_or_replay_persistent_write(fault, report_units):
    fake, clock = CorruptAfterParameters(fault, report_units), Clock()
    controller = MachineController(fake, clock)
    controller.connect()
    controller.tick()
    controller.request_manual(ZeroRequest(('X', 'Y')))
    result = drive(controller, clock, lambda snap: snap.manual.phase is ManualPhase.FAILED)
    assert fake.parameter_queries == 2
    assert not result.manual.can_zero and not result.manual.can_jog
    assert result.manual.diagnostic
    assert_no_replay(controller, fake, clock, b'G10 L20 P1 X0 Y0\n')


DISCONNECT_PHASES = [
    ('jog', 'begin'), ('jog', 'startup'), ('jog', 'off'), ('jog', 'modal_off'),
    ('jog', 'jog_ready'),
    ('zero', 'begin'), ('zero', 'startup'), ('zero', 'modal_zero'),
    ('zero', 'parameters_before'), ('zero', 'zero_ready'), ('zero', 'zero'),
    ('zero', 'parameters_after'), ('zero', 'zero_done'),
    ('select', 'begin'), ('select', 'startup'), ('select', 'select'),
    ('select', 'modal_selected'), ('select', 'select_done'),
]


@pytest.mark.parametrize('action, phase', DISCONNECT_PHASES)
def test_disconnect_at_each_nonmoving_phase_discards_operation_without_additional_write(action, phase):
    controller, fake, clock = connected(machine_position=(10., 20., 30.),
                                         offsets={'G54': (1., 2., 3.)})
    request = {'jog': JogRequest('X', 1., 100.), 'zero': ZeroRequest(('X', 'Y')),
               'select': SelectG54Request()}[action]
    controller.request_manual(request)
    if phase != 'begin':
        # Inspect the real transaction checkpoint; assertions below observe public state/wire I/O.
        drive(controller, clock, lambda _snap: controller._manual.transaction == phase
              or controller._manual.waiting_status == phase)
    before = tuple(fake.writes)
    assert not any(command.startswith(b'$J=') for command in before)
    zero_count = sum(command.startswith(b'G10 ') for command in before)
    controller.disconnect()
    result = controller.snapshot()
    assert result.connection is ConnectionState.DISCONNECTED and not fake.is_open
    assert result.manual.phase is ManualPhase.FAILED
    assert not result.manual.can_jog and not result.manual.can_zero
    assert result.machine_position_mm is None and result.work_position_mm is None
    assert tuple(fake.writes) == before
    for _ in range(8):
        clock.now += .25
        controller.tick()
    assert tuple(fake.writes) == before
    assert sum(command.startswith(b'G10 ') for command in fake.writes) == zero_count
