from dataclasses import replace
import pytest
from mikrocam.core.probe_map import ProbeGrid, ProbePlan
from mikrocam.machine.probe_models import ProbePhase, StartProbeGridRequest
from mikrocam.machine.manual_models import JogRequest
from mikrocam.machine.console_models import ConsoleRequest
from test_machine_manual_controller import connected, drive


def plan(controller):
    state = controller.snapshot()
    return ProbePlan(ProbeGrid((0.,1.,2.), (0.,1.)), 5., -1., 30., 200.,
                     (-100.,-100.,-100.), (100.,100.,100.),
                     state.machine_position_mm, state.work_offset_mm, 30.)


def finish(controller, clock):
    return drive(controller, clock, lambda s: s.probe.phase in (
        ProbePhase.COMPLETE, ProbePhase.FAILED, ProbePhase.ABORTED), steps=400)


@pytest.mark.parametrize('units', ['mm','inch'])
@pytest.mark.parametrize('offset', [(0.,0.,0.), (10.,20.,3.)])
def test_plane_grid_single_owner_verified_retract_and_frames(units, offset):
    controller, fake, clock = connected(report_units=units, offsets={'G54':offset},
                                         machine_position=(offset[0],offset[1],offset[2]+2.))
    request = StartProbeGridRequest(plan(controller))
    controller.request_probe(request)
    assert not controller.snapshot().manual.can_jog
    assert not controller.snapshot().job.can_start
    assert not controller.snapshot().console.can_query
    with pytest.raises(ValueError):
        controller.request_manual(JogRequest('X',1,100))
    result = finish(controller, clock)
    assert result.probe.phase is ProbePhase.COMPLETE, result.probe.diagnostic
    assert result.probe.map.heights_mm == pytest.approx((0.,.01,.02,.02,.03,.04),abs=.005)
    assert result.probe.map.g54_offset_mm == pytest.approx(offset,abs=1e-8)
    assert result.probe.map.origin == 'simulated'
    assert result.machine_position_mm == pytest.approx((offset[0]+2,offset[1]+1,offset[2]+5),abs=.005)
    moves = [data for data in fake.writes if data.startswith(b'G21')]
    assert len(moves) == 19 and moves[0].startswith(b'G21 G90 G94 G1 Z5 ')
    assert sum(b'G38.2' in data for data in moves) == 6
    assert result.manual.can_jog and result.console.can_query


@pytest.mark.parametrize('field,value', [('startup_blocks', ('G0 X1','')), ('work_system','G55'),
                                       ('g92',(1.,0.,0.)), ('tlo',1.)])
def test_bad_live_setup_rejected_without_motion(field,value):
    controller, fake, clock = connected(**{field:value})
    controller.request_probe(StartProbeGridRequest(plan(controller)))
    result = finish(controller, clock)
    assert result.probe.phase is ProbePhase.FAILED
    assert not any(data.startswith(b'G21') for data in fake.writes)


def test_laser_mode_missing_settings_and_changed_binding_fail_before_motion():
    for mode in (1, None):
        controller, fake, clock = connected()
        if mode is None:
            del fake.job_settings[32]
        else:
            fake.job_settings[32] = mode
        controller.request_probe(StartProbeGridRequest(plan(controller)))
        assert finish(controller,clock).probe.phase is ProbePhase.FAILED
        assert not any(data.startswith(b'G21') for data in fake.writes)
    controller, fake, clock = connected()
    wrong = replace(plan(controller), initial_machine_mm=(1.,0.,0.))
    with pytest.raises(ValueError):
        controller.request_probe(StartProbeGridRequest(wrong))


@pytest.mark.parametrize('units', ['mm', 'inch'])
def test_small_decimal_coordinates_and_heights_complete(units):
    controller, fake, clock = connected(report_units=units, machine_position=(0., 0., 2.))
    request_plan = replace(plan(controller), grid=ProbeGrid((0., .001), (0., .001)))
    controller.request_probe(StartProbeGridRequest(request_plan))
    result = finish(controller, clock).probe
    assert result.phase is ProbePhase.COMPLETE, result.diagnostic
    assert result.map.heights_mm == pytest.approx((0., .00001, .00002, .00003), abs=1e-10)


def test_contact_height_is_separate_from_decelerated_idle_position():
    controller, fake, clock = connected(machine_position=(0., 0., 2.))
    respond = fake._probe.respond
    def decelerated(data):
        respond(data)
        if b'G38.2' in data:
            x, y, z = fake.machine_position
            fake.machine_position = (x, y, z - .02)
    fake._probe.respond = decelerated
    controller.request_probe(StartProbeGridRequest(plan(controller)))
    result = finish(controller, clock)
    assert result.probe.phase is ProbePhase.COMPLETE, result.probe.diagnostic
    assert result.probe.map.heights_mm == pytest.approx((0., .01, .02, .02, .03, .04))
    assert result.machine_position_mm == pytest.approx((2., 1., 5.))


@pytest.mark.parametrize('stopped', [(0., 0., .02), (0., 0., -1.02), (.02, 0., -.02)])
def test_stopped_position_outside_contact_segment_fails(stopped):
    controller, fake, clock = connected(machine_position=(0., 0., 2.))
    respond = fake._probe.respond
    def invalid_stop(data):
        respond(data)
        if b'G38.2' in data:
            fake.machine_position = stopped
    fake._probe.respond = invalid_stop
    controller.request_probe(StartProbeGridRequest(plan(controller)))
    result = finish(controller, clock).probe
    assert result.phase is ProbePhase.FAILED and result.completed == 0
    assert result.stop_unverified
    assert sum(b'G38.2' in data for data in fake.writes) == 1
