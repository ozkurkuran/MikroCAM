"""GRBL 1.1 bytes stay identical to main 70800e5b except the read-only $I (spec 042, UA-1)."""
import pytest

import firmware_wire_scenarios as scenarios

IDENTIFY = b'$I\n'
SETTINGS = b'$$\n'
# Which session-settings requests ($$ occurrences, 0-based) are now preceded by identification.
# Job preparation and console $$ requests are owned by those flows and never gain $I.
IDENTIFIED_SETTINGS = {name: (0,) for name in scenarios.SCENARIOS}
IDENTIFIED_SETTINGS.update(reset_on_open=(0, 1), disconnect_reconnect=(0, 1))


def expected_writes(golden: list[bytes], occurrences: tuple[int, ...]) -> list[bytes]:
    result, seen = [], 0
    for write in golden:
        if write == SETTINGS:
            if seen in occurrences:
                result.append(IDENTIFY)
            seen += 1
        result.append(write)
    return result


@pytest.mark.parametrize('name', sorted(scenarios.SCENARIOS))
def test_grbl11_wire_trace_matches_main_plus_identification_only(name):
    golden = scenarios.load_golden()[name]
    writes, summary = scenarios.run(name)
    old = [bytes.fromhex(item) for item in golden['writes']]
    assert writes == expected_writes(old, IDENTIFIED_SETTINGS[name])
    assert scenarios.json.loads(scenarios.json.dumps(summary)) == golden['summary']


def test_golden_covers_every_motion_owner_and_stop_path():
    golden = scenarios.load_golden()
    flat = {bytes.fromhex(item) for data in golden.values() for item in data['writes']}
    for marker in (b'$J=G21 G91 X1 F100\n', b'\x85', b'G10 L20 P1 X0 Y0\n', b'G54\n', b'\x18',
                   b'G1X1F60\n', b'$N\n', b'$G\n', b'$#\n', b'M5 M9\n', IDENTIFY):
        assert marker in flat
    assert any(item.startswith(b'G21 G90 G94 G38.2') or b'G38.2' in item for item in flat)
