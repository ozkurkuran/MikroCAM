"""Exact reviewed-source binding and bounded mechanical-only streaming preparation."""
from dataclasses import FrozenInstanceError, fields, replace

import pytest

from mikrocam.core.cnc_job import JobBlock, PreparedJob, validate_job_block
from mikrocam.core.gcode_lexer import iter_blocks
from mikrocam.core.gcode_models import PreflightCancelled, PreflightSetup, SourceSnapshot
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.core.placement import Placement


HEADER='G21 G90 G17 G94 G54 G40 G49\n'


def inputs(text=HEADER+'G1 X1 F60\nM2', **changes):
    setup=replace(PreflightSetup((0.,0.,5.),Placement(),0.,(-100.,-100.,-10.),
                                 (100.,100.,100.),5.,(600.,300.,120.)),**changes)
    source=SourceSnapshot('reviewed.nc',text)
    return source,analyze_gcode(source,setup)


def test_canonical_lexer_preserves_exact_numeric_spelling_and_source_lines():
    blocks=tuple(iter_blocks(';heading\r\ng21 g90\n n0002g1 x+.1000y-0. z5. F060.00(comment)'))
    assert tuple(block.line for block in blocks)==(2,3)
    assert tuple(block.canonical for block in blocks)==('G21G90','N0002G1X+.1000Y-0.Z5.F060.00')


def test_prepared_job_owns_derived_frozen_values_and_original_transcript():
    source,report=inputs(';heading\n'+HEADER+'g1 x+.1000 F060.00\nM2',
                         placement=Placement(origin=(1.,2.),translation=(4.,6.)),z_offset_mm=3.)
    job=PreparedJob(source,report)
    assert job.source is source and job.report is report
    assert job.initial_machine_mm==(3.,4.,8.) and job.final_machine_mm==(3.1,4.,8.)
    assert job.g54_offset_mm==(3.,4.,3.)
    assert job.blocks[-2]==JobBlock(3,b'G1X+.1000F060.00\n')
    assert isinstance(job.blocks,tuple) and job.spindle_speeds==()
    assert job.ack_timeout_seconds==pytest.approx(31.)
    assert {field.name for field in fields(job) if field.init}=={'source','report'}
    with pytest.raises(FrozenInstanceError):
        job.blocks=()
    with pytest.raises(TypeError):
        PreparedJob(source,report,blocks=())
    with pytest.raises(TypeError):
        replace(job,blocks=())


def test_source_and_every_report_field_must_equal_fresh_analysis():
    source,report=inputs()
    for forged in (replace(report,distance_mm=2.), replace(report,source_name='other'),
                   replace(report,bounds_mm=((0.,0.,5.),(2.,0.,5.))),
                   replace(report,duration_seconds=2.), replace(report,source_sha256='b'*64)):
        with pytest.raises(ValueError):
            PreparedJob(source,forged)
    with pytest.raises(ValueError):
        PreparedJob(SourceSnapshot(source.name,source.text+'\n;changed'),report)


@pytest.mark.parametrize('placement', [Placement(rotation_deg=90.), Placement(rotation_deg=1e-10),
                                      Placement(mirror_x=True)])
def test_nontranslation_placement_cannot_stream_even_with_allowed_preflight(placement):
    source,report=inputs(placement=placement)
    assert report.allowed
    with pytest.raises(ValueError):
        PreparedJob(source,report)


def test_equivalent_identity_rotation_and_eof_without_terminal_output_off_are_supported():
    source,report=inputs(HEADER+'G1 X1 F60',placement=Placement(rotation_deg=360.))
    assert PreparedJob(source,report).blocks[-1].wire==b'G1X1F60\n'


@pytest.mark.parametrize('changes', [{'rapid_rates_mm_min':None}])
def test_explicit_rapid_rates_required_even_when_source_has_only_feed(changes):
    source,report=inputs(**changes)
    assert report.allowed and report.duration_seconds is not None
    with pytest.raises(ValueError):
        PreparedJob(source,report)


@pytest.mark.parametrize('body', ['M0\nG1 X1 F60', 'M1\nG1 X1 F60', 'M7\nG1 X1 F60',
                                  'M3\nG1 X1 F60', 'S0 M4\nG1 X1 F60',
                                  'S100 M3\nG1 X1 F60\nS0'])
def test_pause_optional_mist_and_unverified_or_zero_active_speed_are_rejected(body):
    source,report=inputs(HEADER+body)
    assert report.allowed
    with pytest.raises(ValueError):
        PreparedJob(source,report)


def test_active_spindle_speed_inventory_includes_later_changes_not_off_only_values():
    source,report=inputs(HEADER+'S999\nS100 M3\nG1 X1 F60\nS200\nM5 S0\nS777\nM4 S300\nM8\nM2')
    job=PreparedJob(source,report)
    assert job.spindle_speeds==(100.,200.,300.)
    assert b'M8\n' in tuple(block.wire for block in job.blocks)


@pytest.mark.parametrize('seconds,expected', [(1.,40.), (100.,1030.), (8640.,86400.)])
def test_watchdog_uses_recomputed_nominal_time_with_hard_cap(seconds,expected):
    source,report=inputs(HEADER+f'G4 P{seconds-1:g}\nG1 X1 F60')
    assert report.duration_seconds==seconds
    assert PreparedJob(source,report).ack_timeout_seconds==expected


def test_long_duration_or_blocked_review_never_prepares():
    for text in (HEADER+'G4 P8640\nG1 X1 F60', HEADER+'G1 X101 F60',HEADER+'M5'):
        source,report=inputs(text)
        with pytest.raises(ValueError):
            PreparedJob(source,report)


@pytest.mark.parametrize('wire', [b'G21G90\n',b'N001G1X+.1000F060.00\n',b'G4P1\n',
                                 b'M3S100\n',b'M8\n',b'M2\n',b'G1X1\n'])
def test_canonical_supported_source_blocks_accepted(wire):
    validate_job_block(wire)


@pytest.mark.parametrize('wire', [b'',b'?',b'$G\n',b'!\n',b'~',b'G1 X1\n',b'g1X1\n',
                                 b'G1X1(comment)\n',b'G1X1;comment\n',b'G1X1\r\n',
                                 b'G1X1\nM3\n',b'M0\n',b'M1\n',b'M7\n',b'G55\n',
                                 b'M6\n',b'G1X1Q1\n',b'G1X1X2\n',b'G4P1X1\n',
                                 b'G49X1\n',b'G1X1G0\n',b'G1Xnan\n',bytearray(b'G1X1\n'),
                                 b'G1X1'*20+b'\n'])
def test_noncanonical_or_unsupported_source_blocks_rejected(wire):
    with pytest.raises(ValueError):
        validate_job_block(wire)


def test_wire_length_counts_lf_and_oversized_source_block_cannot_prepare():
    body=''.join('G'+str(n).zfill(8) for n in (21,90,17,94,54,40,1))+'X1F0600N1T1S100'
    assert len(body.encode()+b'\n')==79
    validate_job_block(body.encode()+b'\n')
    with pytest.raises(ValueError):
        validate_job_block((body+'0').encode()+b'\n')
    source,report=inputs(HEADER+body+'0')
    assert report.allowed
    with pytest.raises(ValueError):
        PreparedJob(source,report)


def test_preparation_checks_cancellation_during_reanalysis_and_final_delivery():
    source,report=inputs()
    with pytest.raises(PreflightCancelled):
        PreparedJob(source,report,cancelled=lambda:True)
    calls=0
    def cancelled():
        nonlocal calls
        calls+=1
        return calls>=8
    with pytest.raises(PreflightCancelled):
        PreparedJob(source,report,cancelled=cancelled)


@pytest.mark.parametrize('numeric', ['0.00000009','000000001','1.00000000','100000000'])
@pytest.mark.parametrize('letter', ['X','F','S','G','M'])
def test_controller_digit_truncation_is_rejected_without_rewriting(numeric,letter):
    with pytest.raises(ValueError,match='precision|digits'):
        validate_job_block(('G1'+letter+numeric+'\n').encode())


def test_preparation_rejects_subresolution_coordinate_despite_allowed_review():
    source,report=inputs(HEADER+'G1 X0.00000009 F60')
    assert report.allowed
    with pytest.raises(ValueError,match='precision|digits'):
        PreparedJob(source,report)
