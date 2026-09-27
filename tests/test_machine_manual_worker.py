"""Worker intent admission and priority signals use one communication owner."""
from threading import Event, get_ident
from time import monotonic

import pytest

from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.manual_models import JogRequest
from mikrocam.machine.models import ManualPhase
from mikrocam.ui.machine_worker import MachineWorker


class PausedRead(FakeGRBL):
    def __init__(self):
        super().__init__()
        self.pause = Event()
        self.entered = Event()
        self.release = Event()
        self.owners = set()

    def read(self, size):
        self.owners.add(get_ident())
        if self.pause.is_set():
            self.entered.set()
            assert self.release.wait(2)
        return super().read(size)

    def write(self, data):
        self.owners.add(get_ident())
        return super().write(data)


@pytest.fixture
def worker(qtbot):
    fake = PausedRead()
    value = MachineWorker(lambda: MachineController(fake))
    observations = []
    value.snapshot_ready.connect(observations.append)
    value.start()
    qtbot.waitUntil(lambda: bool(observations) and observations[-1].manual.can_jog)
    yield value, fake, observations
    fake.release.set()
    value.stop()
    assert value.wait(4000)


def test_intent_slot_is_bounded_and_gui_never_performs_io(worker, qtbot):
    value, fake, observations = worker
    fake.pause.set()
    qtbot.waitUntil(fake.entered.is_set)
    assert value.submit(JogRequest('X', .1, 100))
    assert not value.submit(JogRequest('Y', .1, 100))
    assert not value.submit(b'M3\n')
    fake.release.set()
    qtbot.waitUntil(lambda: observations[-1].manual.phase is ManualPhase.COMPLETE, timeout=6000)
    assert observations[-1].machine_position_mm == pytest.approx((.1, 0, 0))
    assert len(fake.owners) == 1 and get_ident() not in fake.owners


@pytest.mark.parametrize('priority', ['cancel_jog', 'abort', 'stop'])
def test_priority_discards_pending_action(worker, qtbot, priority):
    value, fake, observations = worker
    fake.pause.set()
    qtbot.waitUntil(fake.entered.is_set)
    assert value.submit(JogRequest('X', .1, 100))
    getattr(value, priority)()
    assert not value.submit(JogRequest('Y', .1, 100))
    fake.release.set()
    if priority == 'stop':
        assert value.wait(4000)
    elif priority == 'abort':
        qtbot.waitUntil(lambda: b'\x84' in fake.writes)
    else:
        qtbot.wait(100)
    assert not any(data.startswith(b'$J=') for data in fake.writes)


def test_stop_before_start_does_not_construct_or_open(qtbot):
    calls = []
    value = MachineWorker(lambda: calls.append('created'))
    value.stop()
    value.start()
    assert value.wait(4000)
    assert not calls


def test_close_active_jog_is_bounded_and_cancels_before_close(worker, qtbot):
    value, fake, observations = worker
    assert value.submit(JogRequest('X', 10, 100))
    qtbot.waitUntil(lambda: observations[-1].manual.phase is ManualPhase.MOVING, timeout=6000)
    start = monotonic()
    value.stop()
    assert value.wait(4000) and monotonic() - start < 4
    assert b'\x85' in fake.writes and not fake.is_open
    assert not value.final_snapshot.manual.stop_unverified
