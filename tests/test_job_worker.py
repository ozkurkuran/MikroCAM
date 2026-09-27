"""Typed UI preparation and serial-owner priorities without physical devices."""
from threading import Event, Thread, get_ident

import pytest

from mikrocam.core.cnc_job import PreparedJob
from mikrocam.core.gcode_models import SourceSnapshot
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.machine.job_models import JobObservation, StartJobRequest
from mikrocam.machine.models import ConnectionState, MachineSnapshot
from mikrocam.ui.job_prepare_worker import JobPrepareWorker
from mikrocam.ui.machine_worker import MachineWorker
from test_gcode_preflight import HEADER, setup


def prepared():
    source = SourceSnapshot('reviewed.nc', HEADER + 'G1 X1 F60\nM30')
    return PreparedJob(source, analyze_gcode(source, setup()))


def test_preparation_is_off_gui_and_owns_only_reviewed_values(qtbot, monkeypatch):
    import mikrocam.ui.job_prepare_worker as module
    source = SourceSnapshot('reviewed.nc', HEADER + 'G1 X1 F60\nM30')
    report = analyze_gcode(source, setup())
    original = module.PreparedJob
    owners = []
    def prepare(*args, **kwargs):
        owners.append(get_ident())
        return original(*args, **kwargs)
    monkeypatch.setattr(module, 'PreparedJob', prepare)
    worker = JobPrepareWorker(source, report)
    with qtbot.waitSignal(worker.completed, timeout=3000) as signal:
        worker.start()
    assert worker.wait(2000) and worker.final_job is signal.args[0]
    assert worker.final_job.source is source and worker.final_job.report is report
    assert owners == [owners[0]] and owners[0] != get_ident()


def test_cancelled_preparation_never_delivers_a_job(qtbot, monkeypatch):
    import mikrocam.ui.job_prepare_worker as module
    entered, release = Event(), Event()
    original = module.PreparedJob
    def prepare(*args, **kwargs):
        entered.set()
        assert release.wait(2)
        return original(*args, **kwargs)
    monkeypatch.setattr(module, 'PreparedJob', prepare)
    job = prepared()
    worker = JobPrepareWorker(job.source, job.report)
    completed = []
    worker.completed.connect(completed.append)
    worker.start()
    try:
        qtbot.waitUntil(entered.is_set)
        worker.cancel()
        with qtbot.waitSignal(worker.cancelled, timeout=2000):
            release.set()
        assert worker.wait(2000) and not completed and worker.final_job is None
    finally:
        release.set()
        assert worker.wait(2000)


class Owner:
    def __init__(self):
        self.events = []
        self.before_tick = Event()
        self.release = Event()
        self.snapshot_value = MachineSnapshot(connection=ConnectionState.CONNECTED,
                                               job=JobObservation(can_start=True))

    def record(self, name):
        self.events.append((name, get_ident()))

    def set_interrupt_check(self, callback):
        self.interrupted = callback

    def set_pause_check(self, callback):
        self.pausing = callback

    def connect(self):
        self.record('connect')

    def disconnect(self):
        self.record('disconnect')

    def tick(self):
        self.record('tick')

    def snapshot(self):
        return self.snapshot_value

    def request_job(self, request):
        assert isinstance(request, StartJobRequest)
        self.record('start')

    def pause_job(self):
        self.record('pause')

    def resume_job(self):
        self.record('resume')

    def stop_job(self):
        self.record('stop-job')

    def abort(self):
        self.record('abort')


@pytest.mark.parametrize('priority', ['pause_job', 'stop_job', 'stop'])
def test_priority_before_owner_iteration_discards_pending_start(qtbot, priority):
    owner = Owner()
    worker = MachineWorker(lambda: owner)
    # Exercise the real slot/priority arbitration without bypassing it through GUI wire calls.
    worker._publish(owner.snapshot())
    assert worker.submit(StartJobRequest(prepared(), True))
    getattr(worker, priority)()
    worker._process_intent(owner)
    assert not any(name == 'start' for name, _ in owner.events)
    if priority != 'stop':
        assert owner.events[-1][0] == ('pause' if priority == 'pause_job' else 'stop-job')


def test_pause_callback_defers_feeding_without_interrupt_taint():
    worker = MachineWorker(lambda: Owner())
    worker.pause_job()
    assert worker._pause.is_set() and not worker._interrupted()
    worker.stop_job()
    assert worker._interrupted()


def test_stale_pause_intent_rejection_does_not_escape_owner_iteration():
    owner = Owner()
    def rejected():
        owner.record('pause-rejected')
        raise ValueError('Job already completed before Pause was processed')
    owner.pause_job = rejected
    worker = MachineWorker(lambda: owner)
    worker.pause_job()
    worker._process_intent(owner)
    assert [name for name, _ in owner.events] == ['pause-rejected']
    assert not worker._interrupted()


def test_owner_admission_seals_immutable_job_before_later_gui_invalidation():
    worker = MachineWorker(lambda: Owner())
    owner = Owner()
    worker._publish(owner.snapshot())
    job = prepared()
    assert worker.submit(StartJobRequest(job, True))
    admitted, release, invalidated = Event(), Event(), Event()
    accepted, removed = [], []
    def admit(request):
        accepted.append(request)
        admitted.set()
        assert release.wait(2)
    owner.request_job = admit
    processing = Thread(target=lambda: worker._process_intent(owner))
    def invalidate():
        removed.append(worker.invalidate_pending_job(job))
        invalidated.set()
    invalidating = Thread(target=invalidate)
    processing.start()
    try:
        assert admitted.wait(1)
        invalidating.start()
        assert not invalidated.wait(.02)
        release.set()
    finally:
        release.set()
        processing.join(2)
        if invalidating.ident is not None:
            invalidating.join(2)
    assert not processing.is_alive() and not invalidating.is_alive()
    assert len(accepted) == 1 and removed == [False]


def test_resume_is_one_typed_intent_even_when_ack_remains_pending():
    owner = Owner()
    owner.snapshot_value = MachineSnapshot(connection=ConnectionState.CONNECTED,
                                           job=JobObservation(can_resume=True))
    worker = MachineWorker(lambda: owner)
    worker._publish(owner.snapshot())
    assert worker.resume_job()
    assert not worker.resume_job()
    worker._process_intent(owner)
    assert [name for name, _ in owner.events] == ['resume']


def test_real_worker_calls_controller_and_priority_methods_only_on_owned_thread(qtbot):
    owner = Owner()
    worker = MachineWorker(lambda: owner)
    worker.start()
    try:
        qtbot.waitUntil(lambda: any(name == 'connect' for name, _ in owner.events))
        worker.pause_job()
        qtbot.waitUntil(lambda: any(name == 'pause' for name, _ in owner.events))
        worker.stop_job()
        qtbot.waitUntil(lambda: any(name == 'stop-job' for name, _ in owner.events))
        assert all(thread != get_ident() for _, thread in owner.events)
    finally:
        worker.stop()
        assert worker.wait(4000)
