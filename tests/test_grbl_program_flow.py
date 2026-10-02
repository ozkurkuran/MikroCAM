"""Real GRBL modal program-flow tokens must not reject verified output-off evidence."""
import pytest
from mikrocam.machine.manual_protocol import parse_modal
from mikrocam.machine.job_models import JobPhase
from test_job_control import connected, start, until


@pytest.mark.parametrize('program', ['M0', 'M1', 'M2', 'M30'])
def test_known_program_flow_is_optional_modal_evidence(program):
    modal = parse_modal(f'[GC:G1 G54 G17 G21 G90 G94 {program} M5 M9 T0 F60 S0]')
    assert modal.work_system == 'G54' and modal.spindle == 'M5' and modal.coolant == ('M9',)


@pytest.mark.parametrize('program', ['M0 M2', 'M2 M30', 'M99'])
def test_conflicting_or_unknown_program_flow_stays_rejected(program):
    with pytest.raises(ValueError):
        parse_modal(f'[GC:G1 G54 G17 G21 G90 G94 {program} M5 M9 T0 F60 S0]')


@pytest.mark.parametrize('program', ['M2', 'M30'])
def test_real_final_modal_program_end_allows_job_completion(program):
    controller, fake, clock = connected()
    original = fake._respond
    def report(data):
        if data == b'$G\n' and fake.job_writes:
            fake.inject(f'[GC:G1 G54 G17 G21 G90 G94 {program} M5 M9 T0 F60 S0]\nok\n'.encode())
        else: original(data)
    fake._respond = report
    start(controller)
    until(controller, clock, lambda: controller.snapshot().job.phase in (JobPhase.COMPLETE, JobPhase.FAILED))
    assert controller.snapshot().job.phase is JobPhase.COMPLETE
