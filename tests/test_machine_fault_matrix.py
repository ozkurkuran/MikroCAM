"""Only audited gaps in the existing seven-column machine fault matrix."""
import pytest

from mikrocam.machine.controller import MachineController, SETTINGS_TIMEOUT
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.manual_models import JogRequest, ZeroRequest
from mikrocam.machine.job_models import JobPhase
from mikrocam.machine.models import ManualPhase
from mikrocam.machine.console_models import ConsoleRequest, ConsolePhase
from mikrocam.machine.probe_models import StartProbeGridRequest, ProbePhase
from test_job_control import Clock, connected, running_scripted, step, until
from test_job_adversarial import at_boundary
from test_probe_controller import plan


def pending(kind):
    if kind == "connect":
        fake, clock = FakeGRBL(auto_respond=False), Clock()
        controller = MachineController(fake, clock)
        controller.connect()
        fake.inject(b"[VER:1.1h.20190830:]\r\n[OPT:V,15,128]\r\nok\r\n")  # 042 identification first.
        controller.tick()
        return controller, fake, clock, b"$13=0\r\nok\r\n", SETTINGS_TIMEOUT
    if kind in ("job", "hold"):
        controller, fake, clock = (running_scripted() if kind == "job" else at_boundary("paused"))
        return controller, fake, clock, b"ok\r\n", controller._job.deadline
    controller, fake, clock = connected()
    if kind in ("jog", "zero"):
        request = JogRequest("X", 1, 100) if kind == "jog" else ZeroRequest(("X", "Y"))
        controller.request_manual(request)
        until(controller, clock, lambda: controller._manual.transaction == ("jog" if kind == "jog" else "zero"))
        deadline = controller._manual.deadline
    elif kind == "probe":
        controller.request_probe(StartProbeGridRequest(plan(controller)))
        until(controller, clock, lambda: controller._probe.transaction == "probe")
        deadline = controller._probe.deadline
    else:
        controller.request_console(ConsoleRequest("$G"))
        step(controller, clock)
        deadline = controller._console.deadline
    reply = bytes(fake._incoming)
    fake.auto_respond = False
    fake._incoming.clear()
    assert reply.endswith(b"ok\r\n")
    return controller, fake, clock, reply, deadline


def fresh_until(controller, fake, clock, target):
    while clock.value < target:
        clock.value = min(target, clock.value + .25)
        xyz = ",".join(f"{item:.6f}" for item in fake.machine_position)
        wco = ",".join(f"{item:.6f}" for item in fake.offsets["G54"])
        fake.inject(f"<Idle|MPos:{xyz}|WCO:{wco}>\r\n".encode())
        controller.tick()


def failed(controller, kind):
    state = controller.snapshot()
    if kind == "connect":
        return state.report_units is None
    if kind in ("jog", "zero"):
        return state.manual.phase in (ManualPhase.FAILED, ManualPhase.ABORTED)
    if kind in ("job", "hold"):
        return state.job.phase in (JobPhase.FAILED, JobPhase.ABORTED)
    if kind == "probe":
        return state.probe.phase in (ProbePhase.FAILED, ProbePhase.ABORTED)
    return state.console.phase is ConsolePhase.FAILED


@pytest.mark.parametrize("kind", ["connect", "jog", "zero", "job", "probe", "console"])
@pytest.mark.parametrize("edge", [-.01, .01], ids=["before", "after"])
def test_ack_deadline_edges_keep_status_fresh(kind, edge):
    controller, fake, clock, reply, deadline = pending(kind)
    fresh_until(controller, fake, clock, deadline - .1)
    clock.value = deadline + edge
    fake.inject(reply)
    controller.tick()
    assert failed(controller, kind) is (edge > 0), controller.snapshot()
    if edge > 0:
        assert not controller.snapshot().manual.can_jog
        assert not controller.snapshot().job.can_start
        before = len(fake.job_writes)
        fake.inject(b"ok\r\n")
        step(controller, clock)
        assert len(fake.job_writes) == before


@pytest.mark.parametrize("kind", ["connect", "jog", "zero", "probe", "console", "hold"])
def test_fragmented_ack_preserves_owner_until_complete_line(kind):
    controller, fake, clock, reply, _ = pending(kind)
    before = len(fake.job_writes)
    fake.inject(reply[:-4] + b"o")
    step(controller, clock, .01)
    fake.inject(b"k")
    step(controller, clock, .01)
    if kind != "connect":
        assert not failed(controller, kind)
    if kind == "connect":
        assert controller._settings_sent_at is not None
        assert controller.snapshot().report_units is None
    elif kind in ("jog", "zero"):
        assert controller._manual.transaction is not None
    elif kind == "probe":
        assert controller.snapshot().probe.completed == 0 and controller._probe.transaction == "probe"
    elif kind == "console":
        assert controller.snapshot().console.phase is ConsolePhase.PENDING
    else:
        assert controller.snapshot().job.acknowledged == 0 and len(fake.job_writes) == before
    fake.inject(b"\r\n")
    step(controller, clock, .01)
    assert not failed(controller, kind)
    if kind == "hold":
        assert controller.snapshot().job.phase is JobPhase.PAUSED
        assert len(fake.job_writes) == before


# Existing moving-jog/job/console/probe fault tests are reused in the matrix.
# These combinations were missing: persistent-zero and held-job faults, probe error/stale/write.
@pytest.mark.parametrize("kind,fault", [
    *((kind, fault) for kind in ("zero", "hold") for fault in ("error", "alarm", "reset", "stale", "read", "write")),
    ("probe", "error"), ("probe", "stale"), ("probe", "write"), ("jog", "error"),
])
def test_missing_active_faults_stop_without_replaying_motion(kind, fault):
    controller, fake, clock, _, _ = pending(kind)
    count = len(fake.job_writes)
    zeros = sum(data.startswith(b"G10 ") for data in fake.writes)
    probes = sum(b"G38.2" in data for data in fake.writes)
    if fault == "read":
        fake.read_error = OSError("matrix USB read loss")
    elif fault == "write":
        fake.write_error = OSError("matrix USB write loss")
        clock.value += 2.1
    elif fault == "stale":
        clock.value += 2.1
    else:
        fake.inject({"error": b"error:20\r\n", "alarm": b"ALARM:2\r\n", "reset": b"Grbl 1.1h\r\n"}[fault])
    controller.tick()
    assert failed(controller, kind), controller.snapshot()
    assert not controller.snapshot().manual.can_jog
    assert not controller.snapshot().job.can_start
    fake.read_error = fake.write_error = None
    fake.inject(b"ok\r\n")
    for _ in range(4):
        step(controller, clock)
    assert len(fake.job_writes) == count
    assert sum(data.startswith(b"G10 ") for data in fake.writes) == zeros
    assert sum(b"G38.2" in data for data in fake.writes) == probes


@pytest.mark.parametrize("kind", ["connect", "jog", "zero", "job", "hold", "probe", "console"])
@pytest.mark.parametrize("operation", ["read", "write"])
def test_serial_exception_is_fail_closed_for_each_owner(kind, operation):
    from serial import SerialException
    from mikrocam.machine.models import ConnectionState
    controller, fake, clock, _, _ = pending(kind)
    if operation == "read":
        fake.read_error = SerialException("matrix USB read detached")
    else:
        fake.write_error = SerialException("matrix USB write detached")
        clock.value += 2.1
    controller.tick()
    state = controller.snapshot()
    assert state.connection is ConnectionState.ERROR
    assert state.machine_position_mm is None and not fake.is_open
    assert not state.manual.can_jog and not state.job.can_start
    if kind != "connect":
        assert failed(controller, kind)


@pytest.mark.parametrize("kind", ["zero", "job", "probe"])
@pytest.mark.parametrize("status", ["Door:0", "Check", "Sleep"])
def test_nonidle_modes_reject_missing_operation_admission(kind, status):
    from test_job_control import prepared
    from mikrocam.machine.job_models import StartJobRequest
    controller, fake, clock = connected()
    fake.auto_respond = False
    fake.inject(f"<{status}|MPos:0,0,0|WCO:0,0,0>\r\n".encode())
    step(controller, clock)
    before = tuple(fake.writes)
    request = {"zero": lambda: controller.request_manual(ZeroRequest(("X", "Y"))),
               "job": lambda: controller.request_job(StartJobRequest(prepared(), True)),
               "probe": lambda: controller.request_probe(StartProbeGridRequest(plan(controller)))}[kind]
    with pytest.raises(ValueError):
        request()
    assert tuple(fake.writes) == before


@pytest.mark.parametrize("status", ["Check", "Sleep"])
def test_hold_cannot_resume_from_check_or_sleep(status):
    controller, fake, clock, _, _ = pending("hold")
    fake.inject(f"<{status}|MPos:0,0,0|WCO:0,0,0>\r\n".encode())
    step(controller, clock)
    with pytest.raises(ValueError):
        controller.resume_job()
    assert b"~" not in fake.writes


@pytest.mark.parametrize("status", ["Door:0", "Check", "Sleep"])
def test_console_nonidle_modes_reject_queries_without_movement(status):
    controller, fake, clock = connected()
    fake.state = status
    step(controller, clock, .3)
    step(controller, clock, .1)
    before = len(fake.writes)
    with pytest.raises(ValueError):
        controller.request_console(ConsoleRequest("$I"))
    assert len(fake.writes) == before
    assert not controller.snapshot().manual.can_jog


@pytest.mark.parametrize("kind", ["jog", "zero", "job", "hold", "probe", "console"])
def test_repeated_reconnect_discards_prior_owner_without_replay(kind):
    controller, fake, clock, _, _ = pending(kind)
    controller.disconnect()
    motion = lambda: tuple(data for data in fake.writes if data.startswith((b"$J=", b"G10 ", b"G38.2", b"G1", b"G0")))
    before = motion()
    fake.auto_respond = True
    for _ in range(10):
        controller.connect()
        for _ in range(4):
            step(controller, clock)
        assert motion() == before
        assert controller.snapshot().job.source_sha256 == ""
        assert controller.snapshot().probe.map is None
        controller.disconnect()
        assert not fake.is_open
    assert fake.open_count == 11


@pytest.mark.parametrize("kind", ["jog", "zero", "job", "probe", "console"])
@pytest.mark.parametrize("status", ["Door:0", "Check", "Sleep"])
def test_nonidle_transition_during_transaction_cannot_release_next_motion(kind, status):
    controller, fake, clock, _, _ = pending(kind)
    count = len(fake.job_writes)
    zeros = sum(data.startswith(b"G10 ") for data in fake.writes)
    probes = sum(b"G38.2" in data for data in fake.writes)
    fake.inject(f"<{status}|MPos:0,0,0|WCO:0,0,0>\r\n".encode() + b"ok\r\n")
    step(controller, clock)
    assert failed(controller, kind), controller.snapshot()
    assert len(fake.job_writes) == count
    assert sum(data.startswith(b"G10 ") for data in fake.writes) == zeros
    assert sum(b"G38.2" in data for data in fake.writes) == probes
    assert not controller.snapshot().manual.can_jog
    assert not controller.snapshot().job.can_start
