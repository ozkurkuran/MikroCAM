"""Aligned jobs realise the reviewed fiducial Placement through the existing streaming path."""
from dataclasses import replace
import math

import pytest

from mikrocam.core.aligned_job import AlignedJobResult, prepare_aligned_job
from mikrocam.core.autolevel import prepare_autolevel
from mikrocam.core.autolevel_surface import AutoLevelSettings
from mikrocam.core.dry_run import prepare_dry_run
from mikrocam.core.gcode_lexer import iter_blocks
from mikrocam.core.gcode_models import PreflightCancelled, PreflightSetup, SourceSnapshot
from mikrocam.core.gcode_motion import placed_point
from mikrocam.core.gcode_parser import ModalInterpreter
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.core.placement import Placement
from mikrocam.core.probe_map import ProbeGrid, ProbeMap
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.job_models import JobPhase
from test_job_control import connected, start, step, until


AFFINE = Placement(affine=(0.9995, -0.0262, 0.0259, 1.0003, -60., -40.))
G54 = (-50., -30., 0.)
TEXT = ('G21G90G17G94\nM3S500\nG0Z2\nG1Z-.1F60\nG1X10Y0\nG2X10Y10I0J5\n'
        'G1X0Y10\nG3X0Y0I0J-5\nG0Z5\nM5\nM30\n')


def reviewed(text=TEXT, placement=AFFINE, initial=(0., 0., 5.)):
    setup = PreflightSetup(initial, placement, 0., (-200., -200., -10.), (200., 200., 30.),
                           2., (600., 600., 600.))
    source = SourceSnapshot('board.nc', text)
    report = analyze_gcode(source, setup)
    assert report.allowed, report.findings
    return source, report


def derived_motions(result):
    job = result.prepared_job
    parser = ModalInterpreter(job.report.setup.initial_position_mm)
    return [event for block in iter_blocks(job.source.text)
            if (event := parser.consume(block)).motion is not None]


def test_linear_endpoints_are_placed_by_the_same_placement():
    source, report = reviewed()
    result = prepare_aligned_job(source, report, G54[:2], chord_error_mm=.005)
    assert isinstance(result, AlignedJobResult)
    assert result.original_source is source and result.original_report is report
    assert result.g54_offset_mm == G54
    job = result.prepared_job
    assert job.report.setup.placement == Placement(translation=G54[:2])
    assert job.g54_offset_mm == G54 and job.report.allowed and job.report.arc_count == 0
    machine = [placed_point(e.end, job.report.setup.placement, 0.) for e in derived_motions(result)]
    for corner in ((10., 0.), (10., 10.), (0., 10.), (0., 0.)):
        assert min(math.dist(m[:2], AFFINE.apply_point(corner)) for m in machine) < 1e-5
    assert job.initial_machine_mm == pytest.approx(placed_point((0., 0., 5.), AFFINE, 0.), abs=1e-5)
    assert source.sha256 in job.source.text
    assert len(result.lineage) == len(job.source.text.splitlines())
    assert set(result.lineage) - {None} <= set(range(1, 12))


@pytest.mark.parametrize('tolerance', [.05, .005, .0005])
def test_arc_chords_stay_on_the_placed_arc_within_tolerance(tolerance):
    source, report = reviewed('G21G90G17G94\nG0Z2\nG1Z-.1F60\nG1X10Y0\nG2X10Y10I0J5\nG0Z5\nM2\n')
    result = prepare_aligned_job(source, report, G54[:2], chord_error_mm=tolerance)
    events = [e for e in derived_motions(result) if e.motion == 1 and e.start[:2] != e.end[:2]]
    arc_chords = [e for e in events if result.lineage[e.line - 1] == 5]
    assert len(arc_chords) > 2
    inverse = AFFINE.inverse()
    for event in arc_chords:
        for point in (event.start, event.end):
            machine = (point[0] + G54[0], point[1] + G54[1])
            design = inverse.apply_point(machine)
            assert math.dist(design, (10., 5.)) == pytest.approx(5., abs=1e-4)
        middle = ((event.start[0] + event.end[0]) / 2 + G54[0], (event.start[1] + event.end[1]) / 2 + G54[1])
        assert 5. - math.dist(inverse.apply_point(middle), (10., 5.)) <= tolerance * 1.01
    low, high = result.prepared_job.report.bounds_mm
    original_low, original_high = report.bounds_mm
    assert all(a >= b - 1e-3 for a, b in zip(low, original_low))
    assert all(a <= b + 1e-3 for a, b in zip(high, original_high))


def test_inch_incremental_source_is_rewritten_in_absolute_mm():
    text = 'G20G91G17G94\nG0Z-.1\nG1X1F10\nG1Y1\nM2\n'
    source, report = reviewed(text, initial=(0., 0., 5.))
    result = prepare_aligned_job(source, report, G54[:2], chord_error_mm=.005)
    assert 'G21' in result.prepared_job.source.text and 'G90' in result.prepared_job.source.text
    assert result.prepared_job.final_machine_mm == pytest.approx(
        placed_point((25.4, 25.4, 5. - 2.54), AFFINE, 0.), abs=1e-4)


@pytest.mark.parametrize('call', [
    lambda s, r: prepare_aligned_job(s, r, (math.nan, 0.), chord_error_mm=.005),
    lambda s, r: prepare_aligned_job(s, r, (0., 0., 0.), chord_error_mm=.005),
    lambda s, r: prepare_aligned_job(s, r, G54[:2], chord_error_mm=0.),
    lambda s, r: prepare_aligned_job(s, r, G54[:2], chord_error_mm=.2),
    lambda s, r: prepare_aligned_job(s, replace(r, complete=False), G54[:2], chord_error_mm=.005),
    lambda s, r: prepare_aligned_job(SourceSnapshot('other.nc', s.text + '\n'), r, G54[:2], chord_error_mm=.005),
    lambda s, r: prepare_aligned_job(s.text, r, G54[:2], chord_error_mm=.005)])
def test_invalid_inputs_are_rejected(call):
    source, report = reviewed()
    with pytest.raises(ValueError):
        call(source, report)


def test_translation_only_review_does_not_need_alignment():
    source, report = reviewed(placement=Placement(translation=(1., 2.)))
    with pytest.raises(ValueError, match='translation'):
        prepare_aligned_job(source, report, G54[:2], chord_error_mm=.005)


def test_unrepresentable_work_coordinates_are_rejected():
    source, report = reviewed()
    with pytest.raises(ValueError):
        prepare_aligned_job(source, report, (1e7, 0.), chord_error_mm=.005)


def test_cancellation_is_cooperative():
    source, report = reviewed()
    with pytest.raises(PreflightCancelled):
        prepare_aligned_job(source, report, G54[:2], chord_error_mm=.005, cancelled=lambda: True)


def execute(result, fake=None):
    job = result.prepared_job
    controller, fake, clock = connected(fake or FakeGRBL(machine_position=job.initial_machine_mm,
                                                         offsets={'G54': job.g54_offset_mm}))
    start(controller, job)
    until(controller, clock, lambda: controller.snapshot().job.phase in (JobPhase.COMPLETE, JobPhase.FAILED),
          count=2000)
    return controller, fake


def test_aligned_job_streams_only_derived_blocks_to_placed_endpoint():
    source, report = reviewed()
    result = prepare_aligned_job(source, report, G54[:2], chord_error_mm=.01)
    controller, fake = execute(result)
    assert controller.snapshot().job.phase is JobPhase.COMPLETE
    assert fake.job_writes == [block.wire for block in result.prepared_job.blocks]
    assert fake.machine_position == pytest.approx(placed_point((0., 0., 5.), AFFINE, 0.), abs=1e-3)
    controller.disconnect()


@pytest.mark.parametrize('kwargs', [dict(offsets={'G54': (-49., -30., 0.)}), dict(g92=(1., 0., 0.))])
def test_live_g54_mismatch_sends_no_job_block(kwargs):
    source, report = reviewed()
    result = prepare_aligned_job(source, report, G54[:2], chord_error_mm=.01)
    options = dict(machine_position=result.prepared_job.initial_machine_mm, offsets={'G54': G54})
    options.update(kwargs)
    controller, fake = execute(result, FakeGRBL(**options))
    assert controller.snapshot().job.phase is JobPhase.FAILED and not fake.job_writes
    controller.disconnect()


def test_stop_uses_existing_owner_path():
    source, report = reviewed()
    result = prepare_aligned_job(source, report, G54[:2], chord_error_mm=.01)
    job = result.prepared_job
    controller, fake, clock = connected(FakeGRBL(machine_position=job.initial_machine_mm,
                                                 offsets={'G54': G54}))
    start(controller, job)
    until(controller, clock, lambda: len(fake.job_writes) > 3)
    controller.stop_job()
    sent = list(fake.job_writes)
    for _ in range(10):
        step(controller, clock)
    assert fake.job_writes == sent
    value = controller.snapshot().job
    assert value.phase is JobPhase.ABORTED and value.stop_unverified
    assert value.source_sha256 == job.source.sha256 != source.sha256
    controller.disconnect()


def test_dry_run_rejects_direct_affine_but_accepts_the_aligned_job():
    source, report = reviewed()
    with pytest.raises(ValueError, match='translation'):
        prepare_dry_run(source, report, 10.)
    aligned = prepare_aligned_job(source, report, G54[:2], chord_error_mm=.01).prepared_job
    dry = prepare_dry_run(aligned.source, aligned.report, 10.)
    assert dry.prepared_job.final_machine_mm[:2] == pytest.approx(aligned.final_machine_mm[:2])
    assert dry.prepared_job.g54_offset_mm == G54


def test_autolevel_applies_the_same_placement_as_the_aligned_job():
    text = 'G21G90G17G94\nG0Z2\nG1Z-.1F60\nG1X10Y0\nG1X10Y10\nG0Z5\nM2\n'
    source, report = reviewed(text)
    aligned = prepare_aligned_job(source, report, G54[:2], chord_error_mm=.005)
    xs, ys = (-20., 0., 20.), (-20., 0., 20.)
    flat = ProbeMap(ProbeGrid(xs, ys), (0.,) * 9, G54, 'complete', 'simulated')
    level = prepare_autolevel(source, report, AutoLevelSettings(flat, 0., .5, .001, .001))
    aligned_points = [e.end[:2] for e in derived_motions(aligned)]
    level_points = [e.end[:2] for e in derived_motions(level)]
    for point in aligned_points:
        assert min(math.dist(point, other) for other in level_points) < 1e-4
    assert level.prepared_job.final_machine_mm == pytest.approx(aligned.prepared_job.final_machine_mm, abs=1e-4)
