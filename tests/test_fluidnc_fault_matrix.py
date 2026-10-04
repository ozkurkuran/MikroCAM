"""C1 machine fault suites re-run against the FakeGRBL FluidNC v4.1.1 profile (spec 044, US3).

Every test of the C1 fault matrix (docs/MACHINE_FAULT_MATRIX.md) and its adversarial suites is
collected again here, renamed ``<test>__<module>``, while FakeGRBL's default firmware profile is
``fluidnc``. Their helpers build sessions with ``FakeGRBL()``, so the same owners, deadlines and
assertions run through FluidNC identification, macro/$RI startup evidence, $$ proxies and the
FluidNC $# format. Suites asserting GRBL-only bytes (``$N``, ``$31``, ``startup_blocks``) are not
re-collected; their FluidNC counterparts live in test_fluidnc_controller.py.
"""
import pytest

from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.firmware import FirmwareFamily
import test_console_adversarial
import test_job_adversarial
import test_machine_controller
import test_machine_fault_matrix
import test_machine_manual_stop
import test_probe_failures

SUITES = (test_machine_fault_matrix, test_job_adversarial, test_machine_manual_stop,
          test_probe_failures, test_console_adversarial, test_machine_controller)
for _suite in SUITES:
    for _name, _test in vars(_suite).items():
        if _name.startswith('test_') and callable(_test):
            globals()[f'{_name}__{_suite.__name__}'] = _test


@pytest.fixture(autouse=True)
def fluidnc_profile(monkeypatch):
    defaults = dict(FakeGRBL.__init__.__kwdefaults__)
    defaults['firmware'] = 'fluidnc'
    monkeypatch.setattr(FakeGRBL.__init__, '__kwdefaults__', defaults)


def test_matrix_sessions_really_use_fluidnc():
    controller, fake, clock = test_machine_fault_matrix.connected()
    assert fake.fluidnc is not None
    assert controller.snapshot().firmware.capabilities.family is FirmwareFamily.FLUIDNC
    assert controller.snapshot().firmware.motion_allowed
    controller.request_job(test_job_adversarial.StartJobRequest(test_job_adversarial.prepared(), True))
    for _ in range(40):
        test_machine_fault_matrix.step(controller, clock)
    assert b'$RI\n' in fake.writes and b'$N\n' not in fake.writes
