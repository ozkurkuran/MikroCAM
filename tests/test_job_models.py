"""Immutable observable progress and explicit per-start mechanical confirmation."""
from dataclasses import FrozenInstanceError

import pytest

from mikrocam.core.cnc_job import JobBlock, PreparedJob
from mikrocam.core.gcode_models import PreflightSetup, SourceSnapshot
from mikrocam.core.gcode_preflight import analyze_gcode
from mikrocam.core.placement import Placement
from mikrocam.machine.job_models import JobObservation, JobPhase, StartJobRequest


def job():
    source=SourceSnapshot('job.nc','G21G90G94\nG1X1F60')
    setup=PreflightSetup((0.,0.,5.),Placement(),0.,(-10.,-10.,-10.),(10.,10.,10.),5.,(100.,100.,100.))
    return PreparedJob(source,analyze_gcode(source,setup))


def test_observation_defaults_truthful_and_frozen():
    value=JobObservation()
    assert value.phase is JobPhase.READY
    assert value.source_name==value.source_sha256==value.diagnostic==''
    assert value.acknowledged==value.total==0 and value.source_line is None
    assert not any((value.can_start,value.can_pause,value.can_resume,value.can_stop,value.stop_unverified))
    with pytest.raises(FrozenInstanceError):
        value.total=2
    assert tuple(phase.value for phase in JobPhase)==('ready','preparing','running','pausing','paused',
                                                   'completing','complete','aborted','failed')


def test_progress_is_accepted_source_blocks_not_physical_completion():
    value=JobObservation(phase=JobPhase.RUNNING,source_name='job.nc',source_sha256='a'*64,
                         acknowledged=2,total=4,source_line=9,can_pause=True,can_stop=True)
    assert value.acknowledged==2 and value.source_line==9
    assert JobObservation(phase=JobPhase.FAILED,diagnostic='Stop unverified',stop_unverified=True).stop_unverified


@pytest.mark.parametrize('kwargs', [{'phase':'running'},{'source_name':'x'*257},{'source_sha256':'bad'},
                                    {'source_sha256':'g'*64},{'acknowledged':True},{'total':-1},
                                    {'total':250001},{'acknowledged':2,'total':1},{'source_line':0},
                                    {'source_line':True},{'source_line':250001},{'diagnostic':'x'*257},
                                    {'diagnostic':[]},{'can_start':1},{'can_stop':0},{'stop_unverified':1}])
def test_invalid_mutable_or_unbounded_observation_rejected(kwargs):
    with pytest.raises(ValueError):
        JobObservation(**kwargs)


def test_start_requires_exact_prepared_type_and_true_boolean_confirmation():
    prepared=job()
    request=StartJobRequest(prepared,True)
    assert request.job is prepared and request.mechanical_confirmed is True
    with pytest.raises(FrozenInstanceError):
        request.mechanical_confirmed=False
    for confirmed in (False,1,'yes',None):
        with pytest.raises(ValueError):
            StartJobRequest(prepared,confirmed)
    with pytest.raises(ValueError):
        StartJobRequest({},True)
    class OtherJob(PreparedJob):
        pass
    with pytest.raises(ValueError):
        StartJobRequest(OtherJob(prepared.source,prepared.report),True)


@pytest.mark.parametrize('line,wire', [(0,b'G1X1\n'),(True,b'G1X1\n'),(250001,b'G1X1\n'),
                                     (1,b'M7\n'),(1,b'G1 X1\n')])
def test_job_block_rejects_invalid_source_identity_and_unsupported_wire(line,wire):
    with pytest.raises(ValueError):
        JobBlock(line,wire)
