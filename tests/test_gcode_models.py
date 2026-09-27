"""Immutable bounded preflight inputs and honest complete/partial report values."""
from dataclasses import FrozenInstanceError, replace
import hashlib

import pytest

from mikrocam.core.gcode_models import (Finding, MAX_FINDINGS, MAX_LINES, MAX_LINE_LENGTH,
                                      MAX_MAGNITUDE, MAX_NUMBER_LENGTH, MAX_SOURCE_BYTES,
                                      PreflightCancelled, PreflightReport, PreflightSetup, SourceSnapshot)
from mikrocam.core.placement import Placement


def setup(**kwargs):
    values = dict(initial_position_mm=(0.,0.,2.), placement=Placement(), z_offset_mm=0.,
                  machine_min_mm=(-10.,-10.,-5.), machine_max_mm=(10.,10.,10.), safe_z_mm=2.)
    return PreflightSetup(**(values | kwargs))


def report(**kwargs):
    values = dict(source_name='board.nc', source_sha256='a'*64, setup=setup(), complete=True,
                  bounds_mm=((0.,0.,2.), (1.,0.,2.)), executable_blocks=2,
                  rapid_count=0, linear_count=1, arc_count=0, distance_mm=1., duration_seconds=.6,
                  units_seen=('mm',), distance_modes_seen=('absolute',), findings=(),
                  finding_count=0, error_count=0)
    return PreflightReport(**(values | kwargs))


def test_constants_and_cancel_exception_are_public_and_fixed():
    assert (MAX_SOURCE_BYTES, MAX_LINES, MAX_LINE_LENGTH, MAX_NUMBER_LENGTH,
            MAX_MAGNITUDE, MAX_FINDINGS) == (16*1024*1024, 250000, 4096, 64, 1e9, 200)
    assert issubclass(PreflightCancelled, Exception)


def test_source_preserves_exact_text_and_hashes_utf8_not_normalized_lines():
    text='G21\r\nG90\nG1 X1 F100\r; μ retained for lexer rejection'
    source=SourceSnapshot('board.nc', text)
    assert source.text == text and source.name == 'board.nc'
    assert source.sha256 == hashlib.sha256(text.encode('utf-8')).hexdigest()
    assert SourceSnapshot('blank.nc', ' \n\t').text == ' \n\t'
    with pytest.raises(FrozenInstanceError):
        source.text='other'


@pytest.mark.parametrize('name,text', [('', 'G21'), ('x'*257, 'G21'), (None, 'G21'),
                                     ('board', ''), ('board', b'G21'), ('board', []),
                                     ('board', '\ud800')])
def test_invalid_source_snapshot_is_a_value_error(name,text):
    with pytest.raises(ValueError):
        SourceSnapshot(name,text)


def test_source_cap_counts_utf8_bytes_and_accepts_exact_boundary(monkeypatch):
    import mikrocam.core.gcode_models as models
    monkeypatch.setattr(models, 'MAX_SOURCE_BYTES', 8)
    assert SourceSnapshot('x','é'*4).text == 'é'*4
    for text in ('é'*5, 'x'*9):
        with pytest.raises(ValueError):
            SourceSnapshot('x',text)


def test_lexer_limits_and_control_rejection_are_not_silently_applied_by_snapshot():
    source=SourceSnapshot('lexer.nc', 'X' * (MAX_LINE_LENGTH+1) + '\n;\x18')
    assert source.text.endswith(';\x18')
    assert SourceSnapshot('x','G21\n').sha256 != SourceSnapshot('x','G21\r\n').sha256


def test_setup_retains_explicit_placement_and_allows_initial_outside_limits():
    placement=Placement(origin=(1.,2.),translation=(5.,6.),rotation_deg=30.,mirror_x=True)
    value=setup(placement=placement,initial_position_mm=(20.,0.,2.),rapid_rates_mm_min=(100.,200.,300.))
    assert value.placement is placement
    assert value.initial_position_mm == (20.,0.,2.)
    assert value.rapid_rates_mm_min == (100.,200.,300.)
    assert setup().rapid_rates_mm_min is None
    with pytest.raises(FrozenInstanceError):
        value.safe_z_mm=3.


@pytest.mark.parametrize('field,value', [
    ('initial_position_mm',[0.,0.,2.]), ('initial_position_mm',(0.,2.)),
    ('initial_position_mm',(True,0.,2.)), ('initial_position_mm',(float('nan'),0.,2.)),
    ('initial_position_mm',(MAX_MAGNITUDE+1,0.,2.)), ('placement',{}),
    ('z_offset_mm',True), ('z_offset_mm',float('inf')), ('z_offset_mm',MAX_MAGNITUDE+1),
    ('machine_min_mm',(10.,-10.,-5.)), ('machine_max_mm',(-11.,10.,10.)),
    ('safe_z_mm',11.), ('safe_z_mm',-6.), ('safe_z_mm',False),
    ('rapid_rates_mm_min',(100.,0.,300.)), ('rapid_rates_mm_min',(100.,-1.,300.)),
    ('rapid_rates_mm_min',[100.,200.,300.]), ('rapid_rates_mm_min',(100.,True,300.)),
    ('rapid_rates_mm_min',(100.,float('nan'),300.)),
])
def test_setup_rejects_invalid_mutable_nonfinite_or_unordered_inputs(field,value):
    with pytest.raises(ValueError):
        setup(**{field:value})


def test_setup_safe_z_inclusive_boundaries_and_magnitude_cap():
    assert setup(safe_z_mm=-5.).safe_z_mm == -5.
    assert setup(safe_z_mm=10.).safe_z_mm == 10.
    assert setup(initial_position_mm=(MAX_MAGNITUDE,0.,2.)).initial_position_mm[0] == MAX_MAGNITUDE


def test_placement_coordinates_and_overflowing_numeric_setup_are_bounded():
    for placement in (Placement(origin=(MAX_MAGNITUDE+1,0.)),
                      Placement(translation=(0.,MAX_MAGNITUDE+1))):
        with pytest.raises(ValueError):
            setup(placement=placement)
    with pytest.raises(ValueError):
        setup(initial_position_mm=(10**400,0.,2.))


def test_finding_source_line_and_program_level_warning_are_frozen():
    finding=Finding(12,'missing_feed','Specify a positive feed')
    assert finding.severity == 'error'
    assert Finding(0,'assumption','Declared setup only','warning').line == 0
    with pytest.raises(FrozenInstanceError):
        finding.line=0


@pytest.mark.parametrize('args', [(-1,'code','message'), (True,'code','message'),
                                  (1,'','message'), (1,[], 'message'),
                                  (1,'code','x'*257), (1,'code',[]),
                                  (1,'code','message','info')])
def test_invalid_findings_rejected(args):
    with pytest.raises(ValueError):
        Finding(*args)


def test_report_allowed_means_complete_without_errors_not_hardware_permission():
    value=report()
    assert value.allowed and value.setup.placement == Placement()
    assert report(complete=False,duration_seconds=None).allowed is False
    finding=Finding(1,'feed','Missing feed')
    assert not report(findings=(finding,),finding_count=1,error_count=1).allowed
    assert report(findings=(Finding(0,'scope','Declared setup only','warning'),),finding_count=1).allowed
    with pytest.raises(FrozenInstanceError):
        value.complete=False


def test_report_retains_total_counters_beyond_bounded_first_findings():
    findings=tuple(Finding(i+1,'unsupported','Unknown word') for i in range(MAX_FINDINGS))
    value=report(complete=False,duration_seconds=None,findings=findings,finding_count=201,error_count=201)
    assert len(value.findings) == 200 and value.finding_count == value.error_count == 201


@pytest.mark.parametrize('field,value', [
    ('source_name',''), ('source_sha256','bad'), ('source_sha256','g'*64), ('setup',{}),
    ('complete',1), ('bounds_mm',[[0.,0.,0.],[1.,1.,1.]]),
    ('bounds_mm',((1.,0.,0.),(0.,1.,1.))), ('bounds_mm',((0.,0.,0.),(float('inf'),1.,1.))),
    ('executable_blocks',True), ('rapid_count',-1), ('arc_count',3),
    ('distance_mm',-1.), ('distance_mm',float('nan')), ('duration_seconds',-1.),
    ('duration_seconds',float('inf')), ('units_seen',['mm']), ('units_seen',('MM',)),
    ('units_seen',('mm','mm')), ('distance_modes_seen',('G90',)),
    ('findings',[]), ('finding_count',-1), ('error_count',1),
])
def test_invalid_report_values_rejected(field,value):
    with pytest.raises(ValueError):
        report(**{field:value})


def test_incomplete_duration_and_inconsistent_diagnostic_totals_rejected():
    with pytest.raises(ValueError):
        report(complete=False)
    errors=(Finding(1,'bad','bad'),)
    for kwargs in ({'findings':errors,'finding_count':0,'error_count':0},
                   {'findings':errors,'finding_count':1,'error_count':0},
                   {'findings':errors*201,'finding_count':201,'error_count':201}):
        with pytest.raises(ValueError):
            report(**kwargs)


def test_partial_report_may_preserve_known_bounds_distance_and_unknown_duration():
    value=report(complete=False,bounds_mm=None,duration_seconds=None,
                 units_seen=('mm','inch'),distance_modes_seen=('absolute','incremental'))
    assert value.distance_mm == 1. and value.duration_seconds is None
    assert not value.allowed
    assert replace(value,bounds_mm=((0.,0.,0.),(2e9,0.,0.))).bounds_mm[1][0] == 2e9
