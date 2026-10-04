"""Re-run the C1 fault matrix and adversarial suites with FakeGRBL's grblHAL profile (spec 043 FR-010).

Every imported test builds FakeGRBL() without an explicit firmware; the autouse fixture makes that
default the grblHAL profile (grblHAL banner, $I, status fields and $G/$#/$$ shapes). The tests and
their assertions are unchanged. Tests that assert GRBL-only bytes are listed in EXCLUDED with the
reason; they keep running with the GRBL profile in their own modules.
"""
import importlib

import pytest

from mikrocam.machine import fake_firmware

# C1 fault matrix and adversarial suites first, then the owner suites they exercise.
SUITE_NAMES = ('test_machine_fault_matrix', 'test_job_adversarial', 'test_machine_manual_stop',
               'test_probe_failures', 'test_console_adversarial', 'test_machine_manual_adversarial',
               'test_machine_controller', 'test_machine_manual_controller', 'test_machine_work_zero',
               'test_job_control', 'test_job_transport', 'test_job_precision', 'test_grbl_program_flow',
               'test_char_counting', 'test_dry_run_execution', 'test_queue_control',
               'test_probe_controller', 'test_console_control')
SUITES = tuple(importlib.import_module(name) for name in SUITE_NAMES)
EXCLUDED = {
    'test_cached_parameter_probe_never_supplies_new_missing_result':
        'Scripts an extra [PRB:] into the GRBL-shaped $# reply; the grblHAL fake already reports PRB '
        'in $# (grblHAL report.c:699), so the duplicate fails closed with a different diagnostic.',
}


@pytest.fixture(autouse=True)
def grblhal_default_profile(monkeypatch):
    monkeypatch.setattr(fake_firmware, 'DEFAULT_PROFILE', 'grblhal')


for _suite in SUITES:
    for _name in dir(_suite):
        if _name.startswith('test_') and _name not in EXCLUDED:
            globals()[f'{_name}__{_suite.__name__[5:]}'] = getattr(_suite, _name)
del _suite, _name


def test_suite_rerun_really_uses_grblhal_profile():
    from mikrocam.machine.fake import FakeGRBL
    fake = FakeGRBL()
    assert fake.firmware == 'grblhal' and fake.banner.startswith(b'GrblHAL ')
