"""The D1 GRBL 1.1 journeys replayed on the FluidNC profile reach the same outcome (spec 044, SC-001).

Only the documented FluidNC substitution is allowed on the wire: each GRBL ``$N`` startup query
becomes the four FluidNC read-only startup queries. Console ``$N``, character counting and the
GRBL-greeting reset journeys are FluidNC-specific and are covered in test_fluidnc_controller.py.
"""
import functools

import pytest

import firmware_wire_scenarios as scenarios
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.fluidnc import STARTUP_QUERIES
from test_firmware_wire_preservation import IDENTIFIED_SETTINGS, expected_writes

SHARED = sorted(set(scenarios.SCENARIOS) - {
    'console_queries', 'job_character_counting', 'reset_mid_session', 'reset_on_open'})


def fluidnc_writes(golden: list[bytes]) -> list[bytes]:
    result = []
    for write in golden:
        result.extend(STARTUP_QUERIES if write == b'$N\n' else (write,))
    return result


@pytest.mark.parametrize('firmware', ['fluidnc', 'fluidnc3'])
@pytest.mark.parametrize('name', SHARED)
def test_grbl_journey_has_the_same_outcome_on_fluidnc(monkeypatch, name, firmware):
    monkeypatch.setattr(scenarios, 'FakeGRBL', functools.partial(FakeGRBL, firmware=firmware))
    golden = scenarios.load_golden()[name]
    writes, summary = scenarios.run(name)
    old = expected_writes([bytes.fromhex(item) for item in golden['writes']], IDENTIFIED_SETTINGS[name])
    # Three extra readonly round trips shift the time-based '?' polls; every other byte is exact.
    # job_abort aborts after a fixed tick count, i.e. earlier in the longer FluidNC preparation.
    actual, expected = ([w for w in data if w != b'?'] for data in (writes, fluidnc_writes(old)))
    summary = scenarios.json.loads(scenarios.json.dumps(summary))
    if name == 'job_abort':
        tail = [b'\x18', b'$$\n']  # Abort reset, then the consistent greeting re-reads settings.
        assert actual[-2:] == expected[-2:] == tail and actual[:-2] == expected[:len(actual) - 2]
        assert summary['job'][0] == 'aborted' and summary['job'][1] <= golden['summary']['job'][1]
        summary['job'] = golden['summary']['job']
    else:
        assert actual == expected
    assert summary == golden['summary']
    assert not any(byte in write for write in writes for byte in (b'\x87', b'\x88', b'\x89', b'\x8a'))
