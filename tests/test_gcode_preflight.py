"""Analytic offline preflight: unknown semantics cannot approve a program."""
from dataclasses import replace
import math
from time import perf_counter

import pytest

from mikrocam.core.gcode_models import SourceSnapshot, PreflightSetup, PreflightCancelled
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.core.placement import Placement

HEADER = 'G21 G90 G17 G94\n'


def setup(**changes):
    original = PreflightSetup((0.,0.,5.),Placement(),0.,(-100.,-100.,-10.),
                              (100.,100.,100.),5.,(600.,300.,120.))
    return replace(original,**changes)


def analyze(text, **changes):
    return analyze_gcode(SourceSnapshot('program.nc',text),setup(**changes))


def codes(report):
    return {finding.code for finding in report.findings}


def test_linear_feed_rapid_dwell_have_analytic_bounds_and_nominal_time():
    report = analyze(HEADER+'G0 X10 Y5\nG1 Z-1 F120\nG1 X13 Y9 F300\nG4 P2\nG0 Z5\nM2')
    assert report.allowed and report.complete
    assert report.bounds_mm == ((0.,0.,-1.),(13.,9.,5.))
    assert (report.rapid_count,report.linear_count,report.arc_count)==(2,2,0)
    assert report.distance_mm == pytest.approx(math.hypot(10,5)+6+5+6)
    assert report.duration_seconds == pytest.approx(1+3+1+2+3)
    assert report.units_seen == ('mm',) and report.distance_modes_seen == ('absolute',)


def test_inch_incremental_and_absolute_programs_are_physically_equivalent():
    mm = analyze(HEADER+'G1 X25.4 F254\nG91\nG1 Y25.4')
    inch = analyze('G20 G90 G17 G94\nG1 X1 F10\nG91\nG1 Y1')
    assert inch.allowed and inch.bounds_mm == mm.bounds_mm
    assert inch.duration_seconds == pytest.approx(mm.duration_seconds)
    assert inch.distance_modes_seen == ('absolute','incremental')


def test_g94_feed_remains_physical_through_unit_change_until_new_f():
    report=analyze(HEADER+'G1 X25.4 F254\nG20\nG1 X2\nF20\nG1 X3')
    assert report.allowed and report.duration_seconds==pytest.approx(6+6+3)
    assert report.units_seen==('mm','inch')


@pytest.mark.parametrize('body,code', [
    ('G1 X1','missing-feed'), ('G1 X1 F0','invalid-feed'), ('F-1\nG1 X1','invalid-feed'),
    ('G0 X101','travel-bounds'), ('G1 Z-11 F100','travel-bounds'),
    ('G0 Z1','unsafe-rapid'), ('G0 X1 Z1','unsafe-rapid'),
    ('G1 Z1 F100\nG0 X1','unsafe-rapid')])
def test_known_hazards_block_with_line_specific_diagnostics(body,code):
    report=analyze(HEADER+body)
    assert report.complete and not report.allowed and code in codes(report)
    assert all(finding.line>=2 for finding in report.findings)


def test_initial_outside_machine_is_not_hidden_by_first_endpoint():
    report=analyze(HEADER+'G1 X0 F100',initial_position_mm=(101.,0.,5.))
    assert not report.allowed and report.bounds_mm[1][0]==101
    assert any(item.line==0 and item.code=='travel-bounds' for item in report.findings)


def test_upward_vertical_retreat_from_below_safe_height_is_allowed():
    report=analyze(HEADER+'G0 Z5',initial_position_mm=(0.,0.,-1.))
    assert report.allowed


@pytest.mark.parametrize('body', ['G93', 'G18', 'G19', 'G90.1', 'G53 G0 X0', 'G55', 'G59',
    'G10 L20 P1 X0', 'G92 X0','G43.1 Z1','G28','G30','G38.2 Z-1','G81 X0','M6','M98 P1',
    'G1 X1 X2 F100', 'G20 G21', 'G90 G91', 'G0 G1 X1','M3 M5','G1 X1 K2 F100',
    'G1 X1 P2 F100','G4','G4 P1 X1','G4 P-1','N1.5 G0 X1','T1.5','S-1',
    'G1 X1e2 F100','M2\nG0 X1','G2 I1 J0 F100','G2 Z1 I1 J0 F100',
    'G2 X1 I1 R1 F100', 'G2 X1 F100'])
def test_unsupported_or_ambiguous_program_is_incomplete_and_never_allowed(body):
    report=analyze(HEADER+body)
    assert not report.allowed and not report.complete
    assert report.duration_seconds is None and report.error_count>=1
    assert report.findings[-1].line>=2


@pytest.mark.parametrize('text', ['G1 X1 F100','G21\nG1 X1 F100','G90 G94\nG1 X1 F100',
                                  'G21 G90\nG1 X1 F100','G21 G90 G94\nG2 X1 I1 F100'])
def test_inherited_unknown_modes_cannot_be_guessed(text):
    report=analyze(text)
    assert not report.complete and not report.allowed


def test_invalid_block_does_not_partially_advance_geometry():
    report=analyze(HEADER+'G1 X2 F100\nG1 X90 Q1')
    assert not report.complete and report.bounds_mm==((0.,0.,5.),(2.,0.,5.))
    assert report.linear_count==1 and report.duration_seconds is None


def test_rotated_arc_interior_crosses_bound_even_when_endpoints_fit():
    report=analyze(HEADER+'G3 X0 Y1 I-1 J0 F60',initial_position_mm=(1.,0.,5.),
                   placement=Placement(rotation_deg=45),machine_max_mm=(100.,.9,100.))
    assert report.complete and not report.allowed and 'travel-bounds' in codes(report)
    assert report.bounds_mm[1][1]==pytest.approx(1.)


def test_full_circle_helix_and_major_radius_are_counted():
    report=analyze(HEADER+'G2 X1 Z7 I-1 F60',initial_position_mm=(1.,0.,5.))
    assert report.allowed and report.arc_count==1
    assert report.bounds_mm[0]==pytest.approx((-1.,-1.,5.))
    assert report.bounds_mm[1]==pytest.approx((1.,1.,7.))
    assert report.duration_seconds==pytest.approx(math.hypot(2*math.pi,2))
    major=analyze(HEADER+'G3 X2 R-2 F60')
    assert major.allowed and major.distance_mm==pytest.approx(2*5*math.pi/3)


@pytest.mark.parametrize('body,kwargs', [('G0 X1',{'rapid_rates_mm_min':None}),
                                        ('M0\nG1 X1 F60',{}),('M1\nG1 X1 F60',{})])
def test_unknown_time_is_not_zero_or_falsely_complete(body,kwargs):
    report=analyze(HEADER+body,**kwargs)
    assert report.allowed and report.duration_seconds is None


def test_source_outputs_are_metadata_not_machine_execution():
    report=analyze(HEADER+'S1000 M3\nM8\nT1\nG1 X1 F60\nM5 M9\nM30')
    assert report.allowed and 'output-command' in codes(report)
    assert all(finding.severity=='warning' for finding in report.findings)


def test_no_motion_and_comments_only_cannot_approve_a_job():
    for text in (';just comments',HEADER+'M5'):
        report=analyze(text)
        assert not report.allowed and 'no-motion' in codes(report)


def test_diagnostics_are_bounded_but_total_count_retained():
    report=analyze(HEADER+'G91\n'+('G0 X1 Z-0.01\n'*500),machine_max_mm=(1000.,1000.,1000.))
    assert report.complete and not report.allowed
    assert len(report.findings)==200 and report.finding_count==500


def test_cancelled_analysis_never_returns_report():
    with pytest.raises(PreflightCancelled):
        analyze_gcode(SourceSnapshot('x',HEADER+'G1 X1 F60'),setup(),lambda:True)


def test_large_program_completes_with_bounded_storage_and_prompt_cancellation():
    source=SourceSnapshot('large.nc',HEADER+'G91\n'+('G1 X0.0001 F60\n'*100000))
    started=perf_counter()
    report=analyze_gcode(source,setup())
    assert report.allowed and report.linear_count==100000 and len(report.findings)==0
    assert perf_counter()-started<10
    calls=0
    def cancelled():
        nonlocal calls
        calls+=1
        return calls>=100
    started=perf_counter()
    with pytest.raises(PreflightCancelled):
        analyze_gcode(source,setup(),cancelled)
    assert perf_counter()-started<1
