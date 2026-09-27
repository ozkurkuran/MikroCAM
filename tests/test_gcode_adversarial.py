"""Independent physical equivalences and fail-closed edge cases beyond basic fixtures."""
from dataclasses import replace
import math

import pytest

from mikrocam.core.gcode_models import PreflightCancelled, PreflightSetup, SourceSnapshot
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.core.placement import Placement


HEADER = 'G21 G90 G17 G94\n'


def setup(**changes):
    return replace(PreflightSetup((0.,0.,5.),Placement(),0.,(-200.,-200.,-20.),
                                  (200.,200.,100.),5.,(600.,60.,120.)), **changes)


def analyze(text, **changes):
    return analyze_gcode(SourceSnapshot('adversarial.nc',text),setup(**changes))


@pytest.mark.parametrize('clockwise', [True, False])
@pytest.mark.parametrize('mirror', [True, False])
def test_inch_full_circle_helix_matches_mm_under_nontrivial_placement(clockwise,mirror):
    placement=Placement(origin=(5.,3.),translation=(7.,-11.),rotation_deg=37.,mirror_x=mirror)
    motion='G2' if clockwise else 'G3'
    mm=analyze(HEADER+f'{motion} X25.4 Z25.4 I-25.4 F254',
               initial_position_mm=(25.4,0.,5.),placement=placement,z_offset_mm=12.)
    inch=analyze(f'G20 G90 G17 G94\n{motion} X1 Z1 I-1 F10',
                 initial_position_mm=(25.4,0.,5.),placement=placement,z_offset_mm=12.)
    assert mm.allowed and inch.allowed
    radians=math.radians(37.)
    local_x=5. if mirror else -5.
    cx=7.+local_x*math.cos(radians)+3.*math.sin(radians)
    cy=-11.+local_x*math.sin(radians)-3.*math.cos(radians)
    assert mm.bounds_mm[0] == pytest.approx((cx-25.4,cy-25.4,17.))
    assert mm.bounds_mm[1] == pytest.approx((cx+25.4,cy+25.4,37.4))
    for first,last in zip(mm.bounds_mm,inch.bounds_mm):
        assert first == pytest.approx(last,abs=1e-9)
    expected=math.hypot(2*math.pi*25.4,20.4)
    assert inch.distance_mm == pytest.approx(expected)
    assert inch.duration_seconds == pytest.approx(60*expected/254)


@pytest.mark.parametrize('clockwise', [False,True])
@pytest.mark.parametrize('radius_sign', [1,-1])
def test_inch_incremental_signed_radius_helix_matches_absolute_mm(clockwise,radius_sign):
    motion='G2' if clockwise else 'G3'
    mm=analyze(HEADER+f'{motion} X50.8 Z7 R{radius_sign*50.8} F254')
    inch=analyze(f'G20 G91 G17 G94\n{motion} X2 Z.07874015748031496 R{radius_sign*2} F10')
    assert mm.allowed and inch.allowed
    sweep=math.pi/3 if radius_sign>0 else 5*math.pi/3
    expected=math.hypot(50.8*sweep,2.)
    assert mm.distance_mm == pytest.approx(expected)
    assert inch.duration_seconds == pytest.approx(60*expected/254)
    for first,last in zip(mm.bounds_mm,inch.bounds_mm):
        assert first == pytest.approx(last,abs=1e-9)


def test_arc_feed_persists_in_physical_units_across_mm_to_inch_change():
    report=analyze(HEADER+'G3 X0 Y25.4 I-25.4 F254\nG20\nG3 X-1 Y0 J-1',
                   initial_position_mm=(25.4,0.,5.))
    assert report.allowed and report.arc_count == 2
    assert report.bounds_mm[0] == pytest.approx((-25.4,0.,5.))
    assert report.bounds_mm[1] == pytest.approx((25.4,25.4,5.))
    assert report.duration_seconds == pytest.approx(6*math.pi)


@pytest.mark.parametrize('body', ['G20 G1 X9 Q1 F60', 'M3 G1 X99 F60 K1',
                                  'G91 G1 X99 F60 T.5', 'G1 X99 F60 M6',
                                  'G1 X99 F60 G55', 'G1 X99 F60 (broken'])
def test_invalid_entire_block_cannot_contribute_motion_modes_or_warning(body):
    report=analyze(HEADER+'G1 X2 F60\n'+body+'\nG1 X100 F60')
    assert not report.complete and not report.allowed and report.duration_seconds is None
    assert report.bounds_mm == ((0.,0.,5.),(2.,0.,5.))
    assert report.distance_mm == 2. and report.linear_count == 1
    assert report.units_seen == ('mm',) and report.distance_modes_seen == ('absolute',)
    assert report.findings[0].line == 3
    assert not any(finding.code=='output-command' for finding in report.findings)


@pytest.mark.parametrize('tail', ['; harmless?','(metadata\x18)',';labelé',';tail\x00'])
def test_unsafe_comment_after_program_end_still_blocks_full_source(tail):
    report=analyze(HEADER+'G1 X1 F60\nM2\n'+tail)
    assert not report.complete and not report.allowed
    assert report.findings[-1].line == 4 and report.findings[-1].code=='unsafe-byte'
    assert report.bounds_mm == ((0.,0.,5.),(1.,0.,5.))


def test_mixed_line_endings_keep_physical_finding_line_and_prefix():
    text='(header)\rG21 G90 G94\r\n\r\nG1X2F60\n\tG1X90Q1'
    report=analyze(text)
    assert not report.complete and report.findings[-1].line == 5
    assert report.linear_count == 1 and report.distance_mm == 2.


def test_commented_fake_commands_after_end_are_not_executable():
    report=analyze(HEADER+'g1x1f60(comment; M6 X999)\nM30\n;(M3 G1 X999)\n(blank)')
    assert report.allowed and report.linear_count == 1 and report.distance_mm == 1.
    assert not report.findings


def test_explicit_modes_required_only_where_used_not_invented_for_unused_groups():
    rapid=analyze('G21 G90\nG0 X1')
    straight=analyze('G21 G90 G94\nG1 X1 F60')
    assert rapid.allowed and rapid.duration_seconds == pytest.approx(.1)
    assert straight.allowed and straight.duration_seconds == pytest.approx(1.)
    assert rapid.arc_count == straight.arc_count == 0
    with pytest.raises(ValueError):
        analyze_gcode(SourceSnapshot('x',HEADER+'G1 X1 F60'),None)


@pytest.mark.parametrize('body', ['G1 X1 F60 G54.000000000000001',
                                  'G1.00000000000000001 X1 F60',
                                  'N1.00000000000000001 G1 X1 F60',
                                  'T1.00000000000000001 G1 X1 F60'])
def test_fractional_opcode_or_integer_metadata_cannot_round_into_supported_word(body):
    report=analyze(HEADER+body)
    assert not report.complete and not report.allowed
    assert report.linear_count == 0 and report.distance_mm == 0.


def test_inch_arc_radius_obeys_normalized_numeric_magnitude_limit():
    report=analyze('G20 G90 G17 G94\nG3 X1 R1000000000 F10')
    assert not report.complete and not report.allowed
    assert any(finding.code=='numeric-range' for finding in report.findings)


def test_machine_axis_rapid_time_uses_placed_delta_and_slowest_axis():
    report=analyze(HEADER+'G0 X6 Y2',placement=Placement(rotation_deg=90,mirror_x=True),z_offset_mm=7.)
    assert report.allowed and report.duration_seconds == pytest.approx(6.)
    assert report.distance_mm == pytest.approx(math.sqrt(40))
    assert report.bounds_mm == ((-2.,-6.,12.),(0.,0.,12.))


def test_translated_machine_z_not_work_z_controls_rapid_safety():
    safe=analyze(HEADER+'G0 X1',initial_position_mm=(0.,0.,-5.),z_offset_mm=10.)
    unsafe=analyze(HEADER+'G0 X1',initial_position_mm=(0.,0.,10.),z_offset_mm=-6.)
    assert safe.allowed
    assert unsafe.complete and not unsafe.allowed
    assert any(finding.code=='unsafe-rapid' for finding in unsafe.findings)


@pytest.mark.parametrize('delta,allowed', [(.5e-9,True),(2e-9,False)])
def test_inclusive_machine_boundary_uses_only_documented_numeric_tolerance(delta,allowed):
    report=analyze(HEADER+f'G1 X{1.+delta:.12f} F60',machine_max_mm=(1.,200.,100.))
    assert report.allowed is allowed


def test_error_after_retained_warning_cap_still_blocks_report():
    report=analyze(HEADER+'M3\n'*250+'G1 X1')
    assert report.complete and not report.allowed and report.duration_seconds is None
    assert report.finding_count == 251 and report.error_count == 1
    assert len(report.findings)==200 and all(finding.severity=='warning' for finding in report.findings)


def test_cancellation_at_final_return_cannot_publish_completed_report():
    calls=0
    def cancelled():
        nonlocal calls
        calls+=1
        return calls==4
    with pytest.raises(PreflightCancelled):
        analyze_gcode(SourceSnapshot('x',HEADER+'G1 X1 F60'),setup(),cancelled)


def test_line_limit_after_valid_prefix_is_partial_not_success(monkeypatch):
    import mikrocam.core.gcode_lexer as lexer
    monkeypatch.setattr(lexer,'MAX_LINES',3)
    report=analyze(HEADER+'G1 X1 F60\n;blank\n;too many')
    assert not report.complete and not report.allowed
    assert report.duration_seconds is None and report.distance_mm==1.
    assert report.findings[-1].line==4 and report.findings[-1].code=='resource-limit'
