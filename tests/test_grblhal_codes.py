"""Family-specific alarm and error meanings (spec 043, research R9)."""
import pytest

from mikrocam.machine.firmware import FirmwareFamily
from mikrocam.machine.firmware_codes import ALARMS, ERRORS, code_meaning

GRBL, HAL = FirmwareFamily.GRBL, FirmwareFamily.GRBLHAL


def test_tables_cover_documented_ranges():
    assert set(ALARMS[GRBL]) == set(range(1, 11))
    assert set(ALARMS[HAL]) == set(range(1, 23))
    assert set(ERRORS[GRBL]) == set(range(1, 18)) | set(range(20, 39))
    assert set(range(1, 18)) | set(range(20, 59)) <= set(ERRORS[HAL])
    assert 253 in ERRORS[HAL] and max(ERRORS[HAL]) == 253
    for table in (*ALARMS.values(), *ERRORS.values()):
        assert all(0 < len(text) <= 80 and text.isascii() for text in table.values())


def test_alarm_ten_differs_between_families():
    assert 'dual' in code_meaning(GRBL, 'ALARM:10').lower()
    assert 'e-stop' in code_meaning(HAL, 'ALARM:10').lower()


@pytest.mark.parametrize('family,text,fragment', [
    (GRBL, 'Controller ALARM:1', 'hard limit'), (HAL, 'ALARM:11', 'homing required'),
    (HAL, 'Controller error:79', 'critical'), (GRBL, 'job rejected: error:22', 'feed rate'),
    (HAL, 'Alarm:12', 'limit'), (HAL, 'error:46', 'homing'),
])
def test_meaning_found_inside_diagnostics(family, text, fragment):
    assert fragment in code_meaning(family, text).lower()


@pytest.mark.parametrize('family,text', [
    (GRBL, 'ALARM:11'), (GRBL, 'error:79'), (HAL, 'error:200'),
    (FirmwareFamily.UNKNOWN, 'error:1'), (GRBL, 'no code here'), (GRBL, ''), (GRBL, 'error:'),
])
def test_unknown_codes_or_families_are_explicit(family, text):
    meaning = code_meaning(family, text)
    if any(char.isdigit() for char in text):
        assert 'not documented' in meaning
    else:
        assert meaning == ''
