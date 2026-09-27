"""Analytic XY projection and exact review binding; no machine or GUI dependencies."""
from dataclasses import FrozenInstanceError, replace
import math

import pytest

from mikrocam.core.dry_run import DryRunResult, prepare_dry_run
from mikrocam.core.gcode_lexer import iter_blocks
from mikrocam.core.gcode_models import PreflightCancelled, PreflightSetup, SourceSnapshot
from mikrocam.core.gcode_parser import ModalInterpreter
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.core.placement import Placement


def reviewed(text, **changes):
    setup = replace(PreflightSetup((0., 0., 2.), Placement(), 0., (-20., -20., -20.),
                                  (20., 20., 20.), 2., (600., 600., 600.)), **changes)
    source = SourceSnapshot('original.nc', text)
    report = analyze_gcode(source, setup)
    assert report.allowed, report.findings
    return source, report


def events(source, setup):
    interpreter = ModalInterpreter(setup.initial_position_mm)
    return tuple(interpreter.consume(block) for block in iter_blocks(source.text))


def test_vertical_up_then_exact_xy_spelling_output_removal_and_lineage():
    source, report = reviewed(';first\ng21 g90 g17 g94\nM3 S100 T1\n'
                              'g1x+.1000y-0.z-1.F060.00\nM7 M5\nM8\nM30')
    before = source, report, source.text, report.setup
    result = prepare_dry_run(source, report, 5.)
    assert (source, report, source.text, report.setup) == before
    assert result.original_source is source and result.original_report is report
    assert result.dry_z_mm == 5.
    job = result.prepared_job
    assert 'DRY RUN' in job.source.name and source.name in job.source.name
    assert source.sha256 in job.source.text and '5' in job.source.text
    lines = job.source.text.splitlines()
    mapping = dict(zip(lines, result.lineage))
    assert mapping['G0Z5'] is None
    assert mapping['G1X+.1000Y-0.F060.00'] == 4
    assert mapping['M5'] == 5 and mapping['M30'] == 7
    assert all(original is None for original in result.lineage[:3])
    assert len(result.lineage) == len(lines)
    assert job.report.setup == replace(report.setup, safe_z_mm=5.)
    assert job.initial_machine_mm == (0., 0., 2.) and job.final_machine_mm == (.1, 0., 5.)
    assert job.spindle_speeds == ()
    executable = tuple(iter_blocks(job.source.text))
    assert not any(letter in 'ST' or (letter == 'M' and value in (3,4,7,8))
                   for block in executable for letter, value in block.words)
    z_blocks = [block for block in executable if any(letter == 'Z' for letter, _ in block.words)]
    assert len(z_blocks) == 1 and z_blocks[0].canonical == 'G0Z5'
    with pytest.raises(FrozenInstanceError):
        result.lineage = ()


@pytest.mark.parametrize('text', [
    'G21G90G17G94\nG1X1Z-2F60\nG1X2Z-3',
    'G20G90G17G94\nG1X.0393701Z-.1F2.3622\nG1X.0787402',
    'G21G91G17G94\nG1X1Z-2F60\nG1X1Z-3',
    'G20G91G17G94\nG1X.0393701Z-.1F2.3622\nG1X.0393701'])
def test_mm_inch_absolute_incremental_preserve_xy_endpoints(text):
    source, report = reviewed(text)
    result = prepare_dry_run(source, report, 5.)
    original = [event.end[:2] for event in events(source, report.setup) if event.motion is not None]
    derived = [event.end[:2] for event in events(result.prepared_job.source, result.prepared_job.report.setup)
               if event.motion is not None and event.start[:2] != event.end[:2]]
    assert derived == original
    assert result.prepared_job.final_machine_mm[2] == 5.


@pytest.mark.parametrize('arc', ['G3X1Y1I0J1Z-2', 'G3X1Y1R1Z-2', 'G2X1Y-1R-1Z-2'])
def test_helical_arcs_keep_validated_xy_arc_and_drop_only_height(arc):
    source, report = reviewed('G21G90G17G94\nF60\n'+arc)
    result = prepare_dry_run(source, report, 5.)
    original = next(event for event in events(source, report.setup) if event.arc)
    derived = next(event for event in events(result.prepared_job.source, result.prepared_job.report.setup) if event.arc)
    assert original.arc == derived.arc and original.end[:2] == derived.end[:2]
    assert derived.start[2] == derived.end[2] == 5.
    assert result.prepared_job.report.distance_mm == pytest.approx(3.+abs(derived.arc.sweep)*derived.arc.radius)


def test_removed_z_only_motion_retains_modal_word_and_feed_for_later_xy():
    source, report = reviewed('G21G90G17G94\nG1Z-1F060.00\nX1\nG0Z3\nX2')
    result = prepare_dry_run(source, report, 5.)
    assert 'G1F060.00' in result.prepared_job.source.text
    assert '\nG0\nX2' in result.prepared_job.source.text
    moving = [event.motion for event in events(result.prepared_job.source, result.prepared_job.report.setup)
              if event.start[:2] != event.end[:2]]
    assert moving == [1,0]


def test_machine_height_accounts_for_z_offset_and_equal_plane_omits_retract():
    source, report = reviewed('G21G90G17G94\nG1X1F60', z_offset_mm=3., safe_z_mm=5.)
    result = prepare_dry_run(source, report, 6.)
    assert 'G0Z3\n' in result.prepared_job.source.text
    assert result.prepared_job.final_machine_mm == (1.,0.,6.)
    equal = prepare_dry_run(source, report, 5.)
    assert not any(letter == 'Z' for block in iter_blocks(equal.prepared_job.source.text)
                   for letter, _ in block.words)


@pytest.mark.parametrize('height', [True, None, '5', float('nan'), float('inf'), 1., 21.])
def test_invalid_below_initial_or_outside_plane_rejects(height):
    source, report = reviewed('G21G90G17G94\nG1X1F60')
    with pytest.raises(ValueError):
        prepare_dry_run(source, report, height)


def test_plane_below_declared_safe_z_is_rejected_even_above_initial():
    source, report = reviewed('G21G90G17G94\nG1X1F60', safe_z_mm=4.)
    with pytest.raises(ValueError):
        prepare_dry_run(source, report, 3.)


@pytest.mark.parametrize('body', ['G1Z-1F60', 'G4P1\nG1Z-1F60', 'M0\nG1X1F60', 'M1\nG1X1F60'])
def test_no_xy_travel_and_programmed_pauses_are_not_dry_jobs(body):
    source, report = reviewed('G21G90G17G94\n'+body)
    with pytest.raises(ValueError):
        prepare_dry_run(source, report, 5.)


def test_forged_or_changed_review_blocked_unknown_and_nontranslation_reject():
    source, report = reviewed('G21G90G17G94\nG1X1F60')
    for supplied_source, supplied_report in [(source, replace(report,distance_mm=2.)),
                                            (SourceSnapshot(source.name,source.text+'\n;edit'),report)]:
        with pytest.raises(ValueError):
            prepare_dry_run(supplied_source,supplied_report,5.)
    blocked = SourceSnapshot('unknown.nc','G21G90G17G94\nM6\nG1X1F60')
    with pytest.raises(ValueError):
        prepare_dry_run(blocked,analyze_gcode(blocked,report.setup),5.)
    rotated, review = reviewed(source.text,placement=Placement(rotation_deg=90))
    with pytest.raises(ValueError):
        prepare_dry_run(rotated,review,5.)


def test_unrepresentable_height_or_retained_numeric_precision_rejects():
    source, report = reviewed('G21G90G17G94\nG1X1F60')
    with pytest.raises(ValueError):
        prepare_dry_run(source,report,5.12345678)
    source, report = reviewed('G21G90G17G94\nG1X0.00000009F60')
    with pytest.raises(ValueError):
        prepare_dry_run(source,report,5.)


def test_generated_height_exact_decimal_subtraction_without_downward_rounding():
    source, report = reviewed('G21G90G17G94\nG1X1F60',initial_position_mm=(0.,0.,0.),
                              z_offset_mm=.1,safe_z_mm=.1)
    result = prepare_dry_run(source,report,.3)
    assert 'G0Z0.2\n' in result.prepared_job.source.text
    assert result.prepared_job.final_machine_mm[2] >= .3


def test_cancellation_and_generated_resource_caps(monkeypatch):
    import mikrocam.core.dry_run as module
    source, report = reviewed('G21G90G17G94\nG1X1F60')
    with pytest.raises(PreflightCancelled):
        prepare_dry_run(source,report,5.,cancelled=lambda:True)
    for name, limit in [('MAX_LINES',3),('MAX_SOURCE_BYTES',100)]:
        with monkeypatch.context() as patch:
            patch.setattr(module,name,limit)
            with pytest.raises(ValueError):
                prepare_dry_run(source,report,5.)


def test_long_original_name_stays_bounded_and_result_validates_lineage():
    source, report = reviewed('G21G90G17G94\nG1X1F60')
    source = SourceSnapshot('n'*256,source.text)
    report = analyze_gcode(source,report.setup)
    result = prepare_dry_run(source,report,5.)
    assert len(result.prepared_job.source.name) <= 256
    for lineage in ([],(True,),(0,),(-1,),('1',)):
        with pytest.raises(ValueError):
            DryRunResult(source,report,5.,result.prepared_job,lineage)


def test_untrusted_filename_stays_metadata_not_executable_comments():
    source, report = reviewed('G21G90G17G94\nG1X1F60')
    source = SourceSnapshot('kart!ö).nc',source.text)
    report = analyze_gcode(source,report.setup)
    result = prepare_dry_run(source,report,5.)
    assert source.name in result.prepared_job.source.name
    assert source.name not in result.prepared_job.source.text


def test_z_only_unit_distance_and_feed_change_is_retained_with_dwell():
    source, report = reviewed('G21G90G17G94\nG20G91G1Z-.1F10\nX.5Y0\nG4P1S100')
    result = prepare_dry_run(source,report,5.)
    assert 'G20G91G1F10\nX.5Y0\nG4P1' in result.prepared_job.source.text
    assert result.prepared_job.final_machine_mm == (12.7,0.,5.)
    assert result.prepared_job.report.duration_seconds == pytest.approx(4.3)


def test_same_xy_full_circle_helix_is_positive_planar_travel():
    source, report = reviewed('G21G90G17G94\nG3X0Y0I1J0Z-1F60')
    result = prepare_dry_run(source,report,5.)
    arc = next(event.arc for event in events(result.prepared_job.source,result.prepared_job.report.setup) if event.arc)
    assert abs(arc.sweep) == pytest.approx(2*math.pi)
    assert result.prepared_job.final_machine_mm == (0.,0.,5.)


def test_cancel_during_projection_and_output_caps_leave_no_result(monkeypatch):
    import mikrocam.core.dry_run as module
    source,report=reviewed('G21G90G17G94\nG1X1F60')
    projecting=[False]
    original=module.iter_blocks
    def observe(text,cancelled=None):
        projecting[0]=True
        yield from original(text,cancelled)
    monkeypatch.setattr(module,'iter_blocks',observe)
    with pytest.raises(PreflightCancelled):
        prepare_dry_run(source,report,5.,cancelled=lambda:projecting[0])
