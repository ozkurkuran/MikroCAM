"""Buffered GRBL source flow, ordinary ACK ownership and physical-proof gates."""
from dataclasses import replace
import pytest
from test_job_control import connected, prepared, step, until
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.job_models import StartJobRequest, JobPhase, StreamingMode


def long_job(count=50):
    return prepared('G21G90G17G94\nF60\n' + ''.join(f'G1X{1+i%2}\n' for i in range(count)) + 'M2\n')


def selected(controller, job=None):
    controller.request_job(StartJobRequest(job or long_job(), True, StreamingMode.CHARACTER_COUNTING))


def scripted():
    controller, fake, clock = connected()
    selected(controller)
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.RUNNING)
    fake.auto_respond = False
    fake._incoming.clear()
    step(controller, clock)
    assert len(fake.job_writes) > 1
    return controller, fake, clock


def test_multiple_blocks_never_exceed_verified_capacity_and_complete_planner_saturation():
    controller, fake, clock = connected()
    job = long_job()
    selected(controller, job)
    maximum = raw_max = 0
    for _ in range(400):
        step(controller, clock)
        raw_max = max(raw_max, fake._job.rx_bytes)
        stream = controller._job.stream
        if stream is not None:
            assert 0 <= stream.used <= stream.capacity <= 128
            maximum = max(maximum, len(stream.pending))
        if controller.snapshot().job.phase is JobPhase.COMPLETE:
            break
    assert maximum > 1 and raw_max > 0
    assert controller.snapshot().job.phase is JobPhase.COMPLETE
    assert fake.job_writes == [b.wire for b in job.blocks]
    assert controller.snapshot().job.acknowledged == len(job.blocks)
    assert fake.machine_position == job.final_machine_mm
    assert fake.writes.count(b'$I\n') == 1


def test_default_source_mode_still_waits_for_each_ack():
    controller, fake, clock = connected()
    controller.request_job(StartJobRequest(long_job(), True))
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.RUNNING)
    fake.auto_respond = False
    fake._incoming.clear()
    for _ in range(3): step(controller, clock)
    assert len(fake.job_writes) == 1 and b'$I\n' not in fake.writes


@pytest.mark.parametrize('evidence', [b'ok\n', b'[VER:0.9j:]\n[OPT:V,15,128]\nok\n',
    b'[VER:1.1h:]\n[OPT:V,15,0]\nok\n', b'[VER:1.1h:]\n[OPT:V,15,4]\nok\n',
    b'[VER:1.1h:]\n[OPT:V,15,128]\n[OPT:V,15,128]\nok\n'])
def test_capability_refusal_sends_no_source(evidence):
    controller, fake, clock = connected()
    original = fake._respond
    fake._respond = lambda data: fake.inject(evidence) if data == b'$I\n' else original(data)
    selected(controller)
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.FAILED)
    assert not fake.job_writes


def test_fragmented_ack_and_push_do_not_release_credit():
    controller, fake, clock = scripted()
    stream = controller._job.stream
    before = (stream.used, len(fake.job_writes))
    fake.inject(b'[MSG:info]\n<Run|MPos:0,0,0|WCO:0,0,0>\nok')
    step(controller, clock)
    assert (stream.used, len(fake.job_writes)) == before
    fake.inject(b'\n')
    step(controller, clock)
    assert controller.snapshot().job.acknowledged == 1
    assert stream.next_index > before[1]


def test_error_maps_to_fifo_head_and_quarantines_already_buffered_motion():
    controller, fake, clock = scripted()
    fake.inject(b'ok\nerror:2\nok\n')
    before = tuple(fake.job_writes)
    step(controller, clock)
    state = controller.snapshot().job
    assert state.phase is JobPhase.FAILED and state.acknowledged == 1
    assert state.source_line == long_job().blocks[1].source_line
    assert 'buffer' in state.diagnostic.lower() and state.stop_unverified
    assert tuple(fake.job_writes) == before and b'\x18' in fake.writes


def test_late_ack_fails_even_with_fresh_status():
    controller, fake, clock = scripted()
    clock.value = controller._job.stream.pending[0].deadline
    fake.inject(b'<Run|MPos:0,0,0|WCO:0,0,0>\nok\n')
    step(controller, clock, 0.)
    assert controller.snapshot().job.phase is JobPhase.FAILED
    assert controller.snapshot().job.acknowledged == 0


def test_priority_between_window_writes_rolls_back_only_unsent_reservation():
    controller, fake, clock = connected()
    selected(controller)
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.RUNNING)
    original = fake.write_job
    pending = [False]
    def write(data):
        count = original(data)
        pending[0] = True
        return count
    fake.write_job = write
    controller._pause_requested = lambda: pending[0]
    step(controller, clock)
    assert len(fake.job_writes) == 1
    assert len(controller._job.stream.pending) == 1


def test_hold_drains_ack_without_refill_and_extends_all_remaining_deadlines():
    controller, fake, clock = scripted()
    before = tuple(fake.job_writes)
    deadlines = tuple(e.deadline for e in controller._job.stream.pending)
    controller.pause_job()
    fake.inject(b'ok\n<Hold:0|MPos:0,0,0|WCO:0,0,0>\n')
    step(controller, clock, .3)
    assert controller.snapshot().job.phase is JobPhase.PAUSED
    for _ in range(71):
        fake.inject(b'<Hold:0|MPos:0,0,0|WCO:0,0,0>\n')
        step(controller, clock, 1.)
    assert tuple(fake.job_writes) == before
    controller.resume_job()
    assert all(e.deadline > old + 70 for e, old in zip(controller._job.stream.pending, deadlines[1:]))


@pytest.mark.parametrize('fault', ['alarm', 'reset', 'read', 'write', 'short', 'stale', 'stop', 'disconnect'])
def test_buffered_faults_never_write_later_sources_or_replay(fault):
    controller, fake, clock = scripted()
    before = tuple(fake.job_writes)
    if fault == 'alarm': fake.inject(b'ALARM:1\n')
    elif fault == 'reset': fake.inject(b"Grbl 1.1h ['$' for help]\n")
    elif fault == 'read': fake.read_error = OSError('USB')
    elif fault in ('write', 'short'):
        fake.write_error = OSError('USB') if fault == 'write' else None
        fake.short_write = fault == 'short'
    elif fault == 'stale': clock.value += 2.1
    elif fault == 'stop': controller.stop_job()
    else: controller.disconnect()
    for _ in range(10): step(controller, clock)
    assert controller.snapshot().job.phase in (JobPhase.FAILED, JobPhase.ABORTED)
    assert tuple(fake.job_writes) == before
    fake.read_error = fake.write_error = None
    fake.short_write = False
    fake.auto_respond = True
    controller.disconnect()
    controller.connect()
    for _ in range(10): step(controller, clock)
    assert tuple(fake.job_writes) == before


def test_queue_rediscovers_capacity_and_completes_each_job_before_advancing():
    from mikrocam.machine.queue_models import QueueDraft, QueuePhase, StartQueueRequest
    from test_queue_control import loop_job
    controller, fake, clock = connected()
    draft = QueueDraft()
    for i in range(3): draft.add(loop_job(f'char-queue-{i}.nc'))
    request = StartQueueRequest(draft.entries, True, StreamingMode.CHARACTER_COUNTING)
    controller.request_queue(request)
    until(controller, clock, lambda: controller.snapshot().queue.phase is QueuePhase.COMPLETE)
    assert fake.writes.count(b'$I\n') == 3
    assert fake.writes.count(b'$G\n') == 6
    assert fake.job_writes == [b.wire for e in request.entries for b in e.job.blocks]


def test_empty_fifo_duplicate_ack_fails_instead_of_granting_credit():
    controller, fake, clock = scripted()
    count = len(controller._job.stream.pending)
    before = tuple(fake.job_writes)
    fake.inject(b'ok\n' * (count + 1))
    step(controller, clock)
    assert controller.snapshot().job.phase is JobPhase.FAILED
    assert tuple(fake.job_writes) == before


def test_all_source_acks_still_require_serialized_final_modal_and_idle():
    controller, fake, clock = connected()
    job = prepared()
    selected(controller, job)
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.RUNNING)
    fake.auto_respond = False
    fake._incoming.clear()
    step(controller, clock)
    fake.inject(b'ok\n' * len(job.blocks))
    step(controller, clock)
    assert controller.snapshot().job.phase is JobPhase.COMPLETING
    assert fake.writes[-1] != b'$G\n'
    fake.inject(b'ok\n')
    step(controller, clock)
    assert controller._job.transaction == 'final_modal'
    fake.inject(b'[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]\nok\n')
    step(controller, clock)
    assert controller.snapshot().job.phase is JobPhase.COMPLETING
    fake.inject(b'<Run|MPos:2,0,0|WCO:0,0,0>\n')
    step(controller, clock)
    assert controller.snapshot().job.phase is JobPhase.COMPLETING


def test_priority_at_transport_handoff_cancels_latest_unsent_credit():
    controller, fake, clock = connected()
    selected(controller)
    until(controller, clock, lambda: controller.snapshot().job.phase is JobPhase.RUNNING)
    original = fake.write_job
    checks = [None]
    def write(data):
        value = original(data)
        checks[0] = 0
        return value
    def pause_pending():
        if checks[0] is None: return False
        checks[0] += 1
        return checks[0] >= 2
    fake.write_job = write
    controller.set_pause_check(pause_pending)
    step(controller, clock)
    stream = controller._job.stream
    assert len(fake.job_writes) == stream.next_index == len(stream.pending) == 1
    assert stream.used == len(fake.job_writes[0])
