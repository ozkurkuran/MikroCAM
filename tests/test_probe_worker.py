"""Probe intents and final partial evidence stay on the existing Qt owner."""

from threading import Event, get_ident

import pytest

from mikrocam.core.probe_map import ProbePlan, uniform_grid
from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.manual_models import JogRequest
from mikrocam.machine.probe_models import ProbePhase, StartProbeGridRequest
from mikrocam.ui.machine_worker import MachineWorker


class OwnedFake(FakeGRBL):
    def __init__(self):
        super().__init__(machine_position=(0.0, 0.0, 5.0))
        self.owners = set()
        self.probe_writes = []
        self.pause = Event()
        self.entered = Event()
        self.release = Event()

    def open(self):
        self.owners.add(get_ident())
        return super().open()

    def close(self):
        self.owners.add(get_ident())
        return super().close()

    def read(self, size):
        self.owners.add(get_ident())
        if self.pause.is_set():
            self.entered.set()
            assert self.release.wait(2)
        return super().read(size)

    def write(self, data):
        self.owners.add(get_ident())
        return super().write(data)

    def write_probe(self, data):
        self.owners.add(get_ident())
        self.probe_writes.append(data)
        return super().write_probe(data)


@pytest.fixture
def session(qtbot):
    fake = OwnedFake()
    owners = []

    def factory():
        owners.append(get_ident())
        return MachineController(fake)

    worker = MachineWorker(factory)
    seen = []
    worker.snapshot_ready.connect(seen.append)
    worker.start()
    qtbot.waitUntil(lambda: bool(seen) and seen[-1].probe.can_start, timeout=4000)
    yield worker, fake, seen, owners
    fake.release.set()
    worker.stop()
    assert worker.wait(4000)


def request():
    return StartProbeGridRequest(
        ProbePlan(
            uniform_grid(0, 1, 2, 0, 1, 2),
            5,
            -1,
            50,
            100,
            (-10.0, -10.0, -10.0),
            (10.0, 10.0, 10.0),
            (0.0, 0.0, 5.0),
            (0.0, 0.0, 0.0),
        )
    )


def test_probe_worker_typed_complete_and_owned_io(session, qtbot):
    worker, fake, seen, owners = session
    assert worker.submit(request())
    assert not worker.submit(request()) and not worker.submit(JogRequest("X", 0.1, 100))
    qtbot.waitUntil(lambda: seen[-1].probe.phase is ProbePhase.COMPLETE, timeout=12000)
    assert seen[-1].probe.map.heights_mm == pytest.approx((0.0, 0.01, 0.02, 0.03))
    assert seen[-1].probe.map.origin == "simulated"
    assert fake.machine_position == (1.0, 1.0, 5.0)
    assert len(fake.owners) == 1 and fake.owners == set(owners)
    assert get_ident() not in fake.owners


@pytest.mark.parametrize("close", [False, True])
def test_stop_or_close_keeps_partial_map_and_no_more_probe_writes(
    session, qtbot, close
):
    worker, fake, seen, owners = session
    assert worker.submit(request())
    qtbot.waitUntil(lambda: seen[-1].probe.completed >= 1, timeout=6000)
    count = len(fake.probe_writes)
    if close:
        worker.stop()
        assert worker.wait(4000)
        final = worker.final_snapshot
    else:
        worker.stop_probe()
        qtbot.waitUntil(
            lambda: seen[-1].probe.phase is ProbePhase.ABORTED, timeout=4000
        )
        final = seen[-1]
    assert final.probe.map is not None
    assert 1 <= final.probe.completed < 4 and not final.probe.map.complete
    assert final.probe.stop_unverified
    assert len(fake.probe_writes) == count
    assert not worker.submit(request())


@pytest.mark.parametrize("priority", ["stop_probe", "stop"])
def test_priority_cancels_reserved_probe_before_any_motion(session, qtbot, priority):
    worker, fake, seen, owners = session
    fake.pause.set()
    qtbot.waitUntil(fake.entered.is_set)
    assert worker.submit(request())
    getattr(worker, priority)()
    fake.release.set()
    if priority == "stop":
        assert worker.wait(4000)
        final = worker.final_snapshot
    else:
        qtbot.waitUntil(
            lambda: seen[-1].probe.phase is ProbePhase.ABORTED, timeout=4000
        )
        final = seen[-1]
    assert final.probe.phase is ProbePhase.ABORTED
    assert final.probe.completed == 0
    assert not fake.probe_writes


def test_desktop_helper_contract_offscreen(qtbot, qapp, tmp_path):
    from types import SimpleNamespace
    from PyQt6 import QtWidgets
    from smoke_probe import probe_journey

    parent = QtWidgets.QMainWindow()
    qtbot.addWidget(parent)
    parent.show()
    (tmp_path / ".venv").mkdir()
    app = SimpleNamespace(ui=parent)

    def pump(application, predicate, errors, stage, timeout=20):
        qtbot.waitUntil(predicate, timeout=timeout * 1000)
        assert not errors, stage

    probe_journey(app, qapp, [], pump, tmp_path)
    assert (tmp_path / ".venv/probe-map-smoke.json").exists()
    assert (tmp_path / ".venv/probe-grid-smoke.png").exists()
