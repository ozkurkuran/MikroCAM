import pytest
from mikrocam.machine.probe_models import ProbePhase, StartProbeGridRequest
from test_probe_controller import plan, finish
from test_machine_manual_controller import connected, drive


@pytest.mark.parametrize('fault', ['missing','failed','malformed','duplicate','alarm','delay'])
def test_probe_fault_never_commits_sample_or_sends_next_motion(fault):
    controller, fake, clock = connected()
    fake._probe.fault = fault
    controller.request_probe(StartProbeGridRequest(plan(controller)))
    result = finish(controller,clock)
    assert result.probe.phase is ProbePhase.FAILED, result.probe
    assert result.probe.completed == 0 and result.probe.map.heights_mm == (None,)*6
    assert result.probe.stop_unverified
    assert sum(b'G38.2' in data for data in fake.writes) == 1
    assert not result.manual.can_jog and not result.job.can_start


@pytest.mark.parametrize('action', ['stop_probe','abort','disconnect'])
def test_priority_preserves_completed_samples(action):
    controller,fake,clock = connected()
    controller.request_probe(StartProbeGridRequest(plan(controller)))
    drive(controller,clock,lambda s:s.probe.completed==1)
    count = sum(b'G38.2' in data for data in fake.writes)
    getattr(controller, action)()
    state = controller.snapshot()
    assert state.probe.phase is ProbePhase.ABORTED
    assert state.probe.map.completed == 1 and not state.probe.map.complete
    for _ in range(10):
        clock.now += .25; controller.tick()
    assert sum(b'G38.2' in data for data in fake.writes)==count


def test_cached_parameter_probe_never_supplies_new_missing_result():
    controller,fake,clock = connected()
    respond = fake._respond
    def cached(data):
        respond(data)
        if data == b'$#\n':
            fake._incoming[:] = fake._incoming.replace(b'ok\r\n',b'[PRB:0,0,0:1]\r\nok\r\n')
    fake._respond = cached
    fake._probe.fault = 'missing'
    controller.request_probe(StartProbeGridRequest(plan(controller)))
    value = finish(controller,clock).probe
    assert value.phase is ProbePhase.FAILED and value.completed == 0
    assert 'without successful' in value.diagnostic


@pytest.mark.parametrize('fault', ['duplicate_ack','offset','bad_position','disconnect','short_write','reset'])
def test_loss_of_live_evidence_stops_without_new_contact(fault):
    controller,fake,clock = connected()
    fake._probe.fault = 'delay'
    controller.request_probe(StartProbeGridRequest(plan(controller)))
    drive(controller,clock,lambda s: controller._probe.transaction=='probe')
    if fault == 'duplicate_ack':
        fake.inject(b'[PRB:0,0,0:1]\r\nok\r\nok\r\n')
    elif fault == 'offset':
        fake.offsets['G54'] = (1.,0.,0.)
    elif fault == 'bad_position':
        fake.inject(b'[PRB:0,0,0:1]\r\nok\r\n')
        fake.machine_position = (5.,0.,0.)
    elif fault == 'disconnect':
        fake.read_error = OSError('Cable removed')
    elif fault == 'short_write':
        fake.short_write = True
    else:
        fake.inject(b'Grbl 1.1h\r\n')
    value = finish(controller,clock).probe
    assert value.phase is ProbePhase.FAILED and value.completed==0
    assert value.stop_unverified
    assert sum(b'G38.2' in data for data in fake.writes)==1


def test_ack_and_contact_alone_wait_for_fresh_idle_before_committing():
    controller,fake,clock = connected()
    fake._probe.fault = 'delay'
    controller.request_probe(StartProbeGridRequest(plan(controller)))
    drive(controller,clock,lambda s: controller._probe.transaction=='probe')
    fake.auto_respond = False
    fake.inject(b'[PRB:0,0,0:1]\r\nok\r\n')
    controller.tick()
    assert controller.snapshot().probe.completed==0
    assert controller._probe.waiting=='probe'
    clock.now+=.25; controller.tick()
    fake.inject(b'<Idle|MPos:0,0,0|WCO:0,0,0>\r\n')
    controller.tick()
    assert controller.snapshot().probe.completed==1
    controller.stop_probe()


def test_late_ack_cannot_clear_expired_transaction_deadline():
    controller,fake,clock = connected()
    fake._probe.fault = 'delay'
    controller.request_probe(StartProbeGridRequest(plan(controller)))
    drive(controller,clock,lambda s: controller._probe.transaction=='probe')
    deadline = controller._probe.deadline
    while clock.now + .25 < deadline:
        clock.now += .25
        controller.tick()
    assert controller._probe.transaction == 'probe'
    fake.inject(b'[PRB:0,0,0:1]\r\nok\r\n')
    clock.now = deadline + .01
    controller.tick()
    assert controller.snapshot().probe.phase is ProbePhase.FAILED
    assert controller.snapshot().probe.completed == 0


def test_unsolicited_idle_probe_result_quarantines_new_operations():
    controller,fake,clock = connected()
    fake.inject(b'[PRB:0,0,0:1]\r\n')
    controller.tick()
    assert controller.snapshot().probe.phase is ProbePhase.FAILED
    assert not controller.snapshot().probe.can_start
    assert not controller.snapshot().manual.can_jog
    with pytest.raises(ValueError):
        controller.request_probe(StartProbeGridRequest(plan(controller)))


@pytest.mark.parametrize('operation', ['manual','console'])
def test_legitimate_cached_parameters_do_not_quarantine_other_owner(operation):
    from mikrocam.machine.manual_models import ZeroRequest
    from mikrocam.machine.models import ManualPhase
    from mikrocam.machine.console_models import ConsoleRequest, ConsolePhase
    controller,fake,clock = connected()
    respond = fake._respond
    def cached(data):
        respond(data)
        if data == b'$#\n':
            fake._incoming[:] = fake._incoming.replace(b'ok\r\n',b'[PRB:0,0,0:0]\r\nok\r\n')
    fake._respond = cached
    if operation == 'manual':
        controller.request_manual(ZeroRequest(('X','Y','Z')))
        state = drive(controller,clock,lambda s:s.manual.phase is ManualPhase.COMPLETE)
    else:
        controller.request_console(ConsoleRequest('$#'))
        state = drive(controller,clock,lambda s:s.console.phase is ConsolePhase.COMPLETE)
    assert not controller._probe.tainted
    assert state.probe.phase is ProbePhase.READY
