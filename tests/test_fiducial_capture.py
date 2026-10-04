"""Machine fiducial capture only reads the single owner's fresh verified snapshot."""
from dataclasses import replace

import pytest

from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.fiducial_capture import capture_machine_xy, capture_work_offset_xy
from mikrocam.machine.models import ConnectionState, MachineSnapshot, MachineState


class Clock:
    value = 0.

    def __call__(self):
        return self.value


def connected(**options):
    clock = Clock()
    fake = FakeGRBL(**options)
    controller = MachineController(fake, clock)
    controller.connect()
    for _ in range(8):
        clock.value += .1
        controller.tick()
    return controller, fake, clock


def test_capture_uses_machine_position_and_sends_nothing():
    controller, fake, _ = connected(machine_position=(-120.5, -80.25, -3.), offsets={'G54': (-100., -50., -2.)})
    snapshot = controller.snapshot()
    writes = list(fake.writes)
    assert capture_machine_xy(snapshot) == pytest.approx((-120.5, -80.25))
    assert capture_work_offset_xy(snapshot) == pytest.approx((-100., -50.))
    assert fake.writes == writes
    controller.disconnect()


def test_inch_reports_are_converted_by_the_controller_before_capture():
    controller, _, _ = connected(report_units='inch', machine_position=(-25.4, 50.8, 0.))
    assert capture_machine_xy(controller.snapshot()) == pytest.approx((-25.4, 50.8))
    controller.disconnect()


def ready():
    return MachineSnapshot(connection=ConnectionState.CONNECTED, state=MachineState.IDLE,
                           machine_position_mm=(1., 2., 3.), work_position_mm=(0., 0., 0.),
                           work_offset_mm=(1., 2., 3.), report_units='mm', stale=False,
                           last_report_at=1.)


@pytest.mark.parametrize('change', [dict(connection=ConnectionState.DISCONNECTED),
                                    dict(connection=ConnectionState.ERROR),
                                    dict(state=MachineState.JOG), dict(state=MachineState.RUNNING),
                                    dict(state=MachineState.ALARM), dict(state=MachineState.UNKNOWN),
                                    dict(stale=True), dict(report_units=None),
                                    dict(machine_position_mm=None)])
def test_ineligible_snapshots_are_refused(change):
    assert capture_machine_xy(ready()) == (1., 2.)
    with pytest.raises(ValueError):
        capture_machine_xy(replace(ready(), **change))


def test_missing_work_offset_and_wrong_type_are_refused():
    with pytest.raises(ValueError):
        capture_work_offset_xy(replace(ready(), work_offset_mm=None))
    with pytest.raises(ValueError):
        capture_machine_xy(None)
