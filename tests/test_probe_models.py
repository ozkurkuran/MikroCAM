import pytest
from mikrocam.machine.probe_models import ProbeObservation, ProbePhase, StartProbeGridRequest


def test_default_observation_has_no_motion_authority():
    value = ProbeObservation()
    assert value.phase is ProbePhase.READY
    assert value.map is None and not value.can_start and not value.can_stop


@pytest.mark.parametrize('kwargs', [{'phase': 'ready'}, {'completed': True}, {'total': 1025},
    {'completed': 1}, {'diagnostic': 'x'*257}, {'can_start': 1}, {'map': {}}, {'stop_unverified': 0}])
def test_observation_rejects_bad_shape(kwargs):
    with pytest.raises(ValueError):
        ProbeObservation(**kwargs)


def test_typed_start_requires_validated_plan():
    with pytest.raises(ValueError):
        StartProbeGridRequest({})
