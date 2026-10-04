"""Short family-specific meanings of ALARM:N and error:N codes (spec 043, research R9).

Code numbers and meanings are interface facts from gnea/grbl bfb67f0c (system.h, report.h) and
grblHAL/core c3a887e3 (alarms.h, errors.h). The wording is MikroCAM's own; no firmware text is
copied. The same number can differ between families (ALARM:10), so lookups always need the family.
"""
import re

from .firmware import FirmwareFamily

_GRBL_ALARMS = {
    1: 'Hard limit triggered; position likely lost, re-home',
    2: 'Soft limit: motion target outside machine travel',
    3: 'Reset during motion; position likely lost, re-home',
    4: 'Probe not in expected initial state',
    5: 'Probe did not make contact within travel',
    6: 'Homing reset during cycle',
    7: 'Safety door opened during homing',
    8: 'Homing pull-off did not clear the switch',
    9: 'Homing switch not found within travel',
    10: 'Homing failed on second dual-axis switch',
}
_GRBLHAL_ALARMS = {
    **{code: _GRBL_ALARMS[code] for code in range(1, 10)},
    10: 'E-stop active',
    11: 'Homing required before motion',
    12: 'Limit switch engaged',
    13: 'Probe protection triggered',
    14: 'Spindle did not reach speed',
    15: 'Homing failed on auto-squared axis switch',
    16: 'Power-on self test failed',
    17: 'Motor fault',
    18: 'Homing failed',
    19: 'Modbus exception',
    20: 'I/O expander exception',
    21: 'Non-volatile storage failed',
    22: 'Buffer overflow',
}
_GRBL_ERRORS = {
    1: 'Expected a command letter', 2: 'Bad number format', 3: 'Invalid $ statement',
    4: 'Negative value not allowed', 5: 'Setting disabled (homing)', 6: 'Step pulse too short',
    7: 'Settings read failed; defaults restored', 8: 'Command requires Idle',
    9: 'G-code locked out in alarm or jog state', 10: 'Soft limits need homing enabled',
    11: 'Line too long', 12: 'Step rate too high', 13: 'Safety door detected as opened',
    14: 'Startup line too long', 15: 'Jog target exceeds machine travel', 16: 'Invalid jog command',
    17: 'Laser mode requires PWM output',
    20: 'Unsupported or invalid G-code command', 21: 'Modal group violation',
    22: 'Feed rate not set', 23: 'Command value must be an integer', 24: 'Axis command conflict',
    25: 'Word repeated in block', 26: 'No axis words for command', 27: 'Invalid line number',
    28: 'Missing value word', 29: 'Work coordinate system not supported',
    30: 'G53 requires G0 or G1', 31: 'Unused axis words in block', 32: 'Arc has no in-plane axis words',
    33: 'Invalid motion target', 34: 'Arc radius error', 35: 'Arc has no in-plane offsets',
    36: 'Unused words in block', 37: 'Dynamic tool offset not on configured axis',
    38: 'Value exceeds supported maximum',
}
_GRBLHAL_ERRORS = {
    **{code: text for code, text in _GRBL_ERRORS.items() if code <= 37},
    18: 'Reset asserted', 19: 'Value must be positive',
    38: 'Illegal tool table entry', 39: 'Value out of range', 40: 'Tool change pending',
    41: 'Spindle not running', 42: 'Illegal plane', 43: 'Maximum feed rate exceeded',
    44: 'Spindle speed out of range', 45: 'Limit switch engaged', 46: 'Homing required',
    47: 'Tool error', 48: 'Value word conflict', 49: 'Self test failed', 50: 'E-stop active',
    51: 'Motor fault', 52: 'Setting value out of range', 53: 'Setting disabled',
    54: 'Invalid retract position', 55: 'Illegal homing configuration',
    56: 'Coordinate system locked', 57: 'Unexpected program demarcation',
    58: 'Auxiliary port unavailable', 60: 'SD card mount failed', 61: 'File read failed',
    62: 'Directory listing failed', 63: 'Directory not found', 64: 'SD card not mounted',
    65: 'File system not mounted', 66: 'File system read only', 70: 'Bluetooth init failed',
    71: 'Unknown expression operation', 72: 'Expression divide by zero',
    73: 'Expression argument out of range', 74: 'Invalid expression argument',
    75: 'Expression syntax error', 76: 'Invalid expression result', 77: 'Authentication required',
    78: 'Access denied', 79: 'Not allowed during a critical event',
    80: 'Flow control outside a macro', 81: 'Flow control syntax error',
    82: 'Flow control stack overflow', 83: 'Flow control out of memory', 84: 'File open failed',
    85: 'File system format failed', 86: 'Auxiliary port unusable', 87: 'Tool already in spindle',
    88: 'No tool in spindle', 89: 'File delete failed', 90: 'Cutter compensation active',
    91: 'Cutter compensation conflict', 92: 'Invalid cutter compensation',
    253: 'User exception',
}
ALARMS = {FirmwareFamily.GRBL: _GRBL_ALARMS, FirmwareFamily.GRBLHAL: _GRBLHAL_ALARMS}
ERRORS = {FirmwareFamily.GRBL: _GRBL_ERRORS, FirmwareFamily.GRBLHAL: _GRBLHAL_ERRORS}
_CODE = re.compile(r'\b(ALARM|Alarm|error):([0-9]{1,3})\b')


def code_meaning(family: FirmwareFamily, text: str) -> str:
    """Meaning of the last ALARM/error code in a diagnostic for the identified family, else ''."""
    matches = _CODE.findall(text) if isinstance(text, str) else []
    if not matches:
        return ''
    kind, number = matches[-1]
    table = (ERRORS if kind == 'error' else ALARMS).get(family, {})
    label = f"{'error' if kind == 'error' else 'ALARM'}:{number}"
    meaning = table.get(int(number))
    return f'{label}: {meaning}' if meaning else f'{label}: code not documented for this firmware'
