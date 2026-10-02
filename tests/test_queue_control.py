"""One owner, verified per-job endpoints and fail-closed automatic queue boundaries."""
from dataclasses import replace
import pytest
from test_job_control import connected, step, until, prepared
from mikrocam.core.gcode_models import SourceSnapshot, PreflightSetup
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.core.cnc_job import PreparedJob
from mikrocam.core.placement import Placement
from mikrocam.machine.queue_models import QueueDraft, QueuePhase
from mikrocam.machine.job_models import JobPhase, StartJobRequest
from mikrocam.machine.manual_models import JogRequest
from mikrocam.machine.console_models import ConsoleRequest
from mikrocam.machine.probe_models import StartProbeGridRequest
from test_probe_controller import plan


def loop_job(name, endpoint=0.):
    text = f"G21 G90 G17 G94\nG1 X1 F60\nG1 X{endpoint}\nM2\n"
    source = SourceSnapshot(name, text)
    setup = PreflightSetup((0., 0., 0.), Placement(), 0., (-10., -10., -10.),
                          (10., 10., 10.), 0., (600., 600., 600.))
    return PreparedJob(source, analyze_gcode(source, setup))


def queued(controller, count=3):
    draft = QueueDraft()
    for i in range(count):
        draft.add(loop_job(f"queue-{i}.nc"))
    request = draft.start_request(True)
    controller.request_queue(request)
    return request


def test_three_jobs_repeat_setup_and_verified_completion_in_order():
    controller, fake, clock = connected()
    request = queued(controller)
    until(controller, clock, lambda: controller.snapshot().queue.phase is QueuePhase.COMPLETE)
    results = controller.snapshot().queue.entries
    assert [r.entry.key for r in results] == [e.key for e in request.entries]
    assert all(r.job.phase is JobPhase.COMPLETE for r in results)
    assert fake.job_writes == [b.wire for e in request.entries for b in e.job.blocks]
    assert fake.writes.count(b"$N\n") == 3
    assert fake.writes.count(b"$G\n") == 6
    assert fake.open_count == 1
    assert controller.snapshot().manual.can_jog


@pytest.mark.parametrize("kind", ["manual", "job", "console", "probe", "queue"])
def test_queue_reservation_rejects_every_other_owner_without_writes(kind):
    controller, fake, clock = connected()
    request = queued(controller)
    before = tuple(fake.writes)
    calls = {"manual": lambda: controller.request_manual(JogRequest("X", 1., 100.)),
             "job": lambda: controller.request_job(StartJobRequest(prepared(), True)),
             "console": lambda: controller.request_console(ConsoleRequest("$I")),
             "probe": lambda: controller.request_probe(StartProbeGridRequest(plan(controller))),
             "queue": lambda: controller.request_queue(request)}
    with pytest.raises(ValueError):
        calls[kind]()
    assert tuple(fake.writes) == before
    state = controller.snapshot()
    assert not any((state.manual.can_jog, state.manual.can_zero, state.job.can_start,
                    state.console.can_query, state.probe.can_start))


@pytest.mark.parametrize("fault", ["error", "alarm", "reset", "read", "write", "stale"])
def test_active_fault_never_releases_next_job_or_replays_on_reconnect(fault):
    controller, fake, clock = connected()
    queued(controller)
    until(controller, clock, lambda: bool(fake.job_writes))
    if fault == "error":
        fake.inject(b"error:2\n")
    elif fault == "alarm":
        fake.inject(b"ALARM:1\n")
    elif fault == "reset":
        fake.inject(b"Grbl 1.1h ['$' for help]\n")
    elif fault == "read":
        fake.read_error = OSError("USB removed")
    elif fault == "write":
        fake.write_error = OSError("USB removed")
    else:
        fake.auto_respond = False
        fake._incoming.clear()
        clock.value += 2.1
    until(controller, clock, lambda: controller.snapshot().queue.phase is QueuePhase.FAILED)
    assert controller.snapshot().queue.entries[1].job.phase is JobPhase.READY
    writes = tuple(fake.job_writes)
    fake.read_error = fake.write_error = None
    fake.auto_respond = True
    controller.disconnect()
    controller.connect()
    for _ in range(20):
        step(controller, clock)
    assert tuple(fake.job_writes) == writes
    assert controller.snapshot().queue.entries[0].job.phase is JobPhase.FAILED


def test_mismatched_reviewed_endpoint_fails_second_before_its_source():
    controller, fake, clock = connected()
    draft = QueueDraft()
    first = draft.add(loop_job("first.nc", endpoint=2.))
    draft.add(loop_job("incompatible.nc"))
    controller.request_queue(draft.start_request(True))
    until(controller, clock, lambda: controller.snapshot().queue.phase is QueuePhase.FAILED)
    result = controller.snapshot().queue.entries
    assert result[0].job.phase is JobPhase.COMPLETE
    assert result[1].job.phase is JobPhase.FAILED
    assert fake.job_writes == [b.wire for b in first.job.blocks]


@pytest.mark.parametrize("action", ["stop", "disconnect", "abort"])
def test_stop_never_advances_and_preserves_terminal_history(action):
    controller, fake, clock = connected()
    queued(controller)
    until(controller, clock, lambda: bool(fake.job_writes))
    {"stop": controller.stop_job, "disconnect": controller.disconnect,
     "abort": controller.abort}[action]()
    writes = tuple(fake.job_writes)
    for _ in range(20):
        step(controller, clock)
    result = controller.snapshot().queue
    assert result.phase is QueuePhase.ABORTED
    assert result.entries[0].job.phase is JobPhase.ABORTED
    assert result.entries[1].job.phase is JobPhase.READY
    assert tuple(fake.job_writes) == writes


@pytest.mark.parametrize("boundary", ["startup", "settings", "off", "modal", "parameters",
                                     "initial", "source", "final_off", "final_modal", "final"])
@pytest.mark.parametrize("fault", ["stop", "error", "alarm", "reset"])
def test_queue_every_transaction_boundary_blocks_remaining_sources(boundary, fault):
    controller, fake, clock = connected()
    queued(controller)
    until(controller, clock, lambda: controller._job.transaction == boundary
          or controller._job.waiting_status == boundary)
    before = tuple(fake.job_writes)
    if fault == "stop":
        controller.stop_job()
    else:
        fake.auto_respond = False
        fake._incoming.clear()
        fake.inject({"error": b"error:2\n", "alarm": b"ALARM:1\n",
                     "reset": b"Grbl 1.1h ['$' for help]\n"}[fault])
    until(controller, clock, lambda: controller.snapshot().queue.phase in
          (QueuePhase.FAILED, QueuePhase.ABORTED))
    for _ in range(10):
        step(controller, clock)
    assert tuple(fake.job_writes) == before
    assert controller.snapshot().queue.entries[1].job.phase is JobPhase.READY


def test_hold_at_reserved_boundary_requires_explicit_resume():
    controller, fake, clock = connected()
    queued(controller)
    controller.pause_job()
    before = tuple(fake.writes)
    for _ in range(3):
        step(controller, clock)
    assert not fake.job_writes
    assert controller.snapshot().queue.phase is QueuePhase.PAUSED
    with pytest.raises(ValueError):
        controller.request_console(ConsoleRequest("$I"))
    controller.resume_job()
    until(controller, clock, lambda: controller.snapshot().queue.phase is QueuePhase.COMPLETE)
    assert controller.snapshot().queue.entries[2].job.phase is JobPhase.COMPLETE
