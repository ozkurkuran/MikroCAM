"""FluidNC serial protocol differences used by the single controller (spec 044).

Formats come from bdring/FluidNC v3.9.9 and v4.1.1 as cited in specs/044-fluidnc-serial/research.md.
No firmware source code is copied. Everything here is pure: no I/O, Qt or legacy imports.
"""
from math import isfinite
import re

from mikrocam.core.cnc_job import PreparedJob


MACROS = ('startup_line0', 'startup_line1', 'after_reset')
REPORT_INTERVAL = 'report_interval'
STARTUP_QUERIES = tuple(f'$/macros/{name}\n'.encode('ascii') for name in MACROS) + (b'$RI\n',)
CONFIG_DUMP = '$CD'
RESTART_QUIET_SECONDS = 2.0
SUPPORTED_MAJOR_VERSIONS = ('3', '4')
# ESP32 ROM boot log (classic ESP32 and S2/S3/C3) and FluidNC's first boot log line. None of them
# is user-editable, unlike the $Start/Message greeting.
_BOOT_PREFIXES = ('ets ', 'rst:0x', 'ESP-ROM:', '[MSG:INFO: FluidNC v')
_PROTOCOL_PREFIXES = ('<', '[', '$', '>', 'error:', 'ALARM:')
_MACRO = re.compile(r'\$/macros/(startup_line0|startup_line1|after_reset)=(.*)\Z')
_INTERVAL_OFF = re.compile(r'\[MSG:INFO: [A-Za-z0-9_]{1,32} auto reporting is off\]\Z')
_INTERVAL_ON = re.compile(r'\[MSG:INFO: [A-Za-z0-9_]{1,32} auto report interval is ([0-9]{1,9}) ms\]\Z')
_SETTING = re.compile(r'\$(\d+)=([+-]?(?:\d+(?:\.\d*)?|\.\d+))\Z')


def is_boot_marker(line: str) -> bool:
    """A line that only an ESP32/FluidNC restart prints; independent of the custom greeting."""
    return isinstance(line, str) and line.startswith(_BOOT_PREFIXES)


def is_free_text(line: str) -> bool:
    """Not shaped like any protocol record: a FluidNC greeting, boot chatter or unknown output."""
    return isinstance(line, str) and bool(line) and line != 'ok' and not line.startswith(_PROTOCOL_PREFIXES)


def motion_version_supported(protocol: str) -> bool:
    """Only the 3.x/4.x protocol lines whose formats were checked against the cited sources."""
    return isinstance(protocol, str) and protocol.split('.', 1)[0] in SUPPORTED_MAJOR_VERSIONS


def parse_startup_record(line: str) -> tuple[str, str | int] | None:
    """Macro read-back or $RI auto-report state; unrelated lines return None."""
    if not isinstance(line, str) or len(line) > 512 or any(not 32 <= ord(char) <= 126 for char in line):
        raise ValueError('FluidNC startup evidence must be printable ASCII of at most 512 bytes')
    if line.startswith('$/macros/'):
        match = _MACRO.fullmatch(line)
        if match is None:
            raise ValueError('Malformed or unexpected FluidNC macro record')
        return match[1], match[2]
    if _INTERVAL_OFF.fullmatch(line):
        return REPORT_INTERVAL, 0
    match = _INTERVAL_ON.fullmatch(line)
    if match:
        return REPORT_INTERVAL, int(match[1])
    if line.startswith('$'):
        raise ValueError('Unexpected settings record during FluidNC startup verification')
    return None


def startup_problem(records: dict) -> str | None:
    """None when no stored G-code runs on reset/boot and auto-reporting is off."""
    missing = [name for name in MACROS + (REPORT_INTERVAL,) if name not in records]
    if missing:
        if missing == [REPORT_INTERVAL]:
            return ('FluidNC $RI auto-report state was not reported; set $Message/Level=Info '
                    'or higher and retry')
        return 'FluidNC startup macro read-back is incomplete: ' + ', '.join(missing)
    filled = [name for name in MACROS if records[name].strip()]
    if filled:
        return ('FluidNC macros/' + ', macros/'.join(filled) + ' must be empty before motion; '
                'MikroCAM does not edit them')
    if records[REPORT_INTERVAL] != 0:
        return 'FluidNC auto-reporting is on ($RI); turn it off with $RI=0 before motion'
    return None


def parse_setting(line: str) -> tuple[int, float] | None:
    match = _SETTING.fullmatch(line) if isinstance(line, str) else None
    if match is None:
        return None
    value = float(match[2])
    if not isfinite(value):
        raise ValueError('Malformed FluidNC settings evidence')
    return int(match[1]), value


def verify_settings(records: dict, job: PreparedJob, units: str) -> None:
    """FluidNC $$ proxies: $13 units, $32 laser mode and $30 max speed; it never reports $31."""
    if not {13, 30, 32}.issubset(records):
        raise ValueError('Missing FluidNC $13/$30/$32 report-unit and spindle proxies')
    if records[13] != (1 if units == 'inch' else 0) or records[32] != 0:
        raise ValueError('Mechanical (non-laser) spindle and unchanged report units are required')
    minimum = records.get(31, 0.)
    maximum = records[30]
    if not 0 <= minimum < maximum:
        raise ValueError('Invalid FluidNC spindle speed configuration')
    if any(not minimum <= speed <= maximum for speed in job.spindle_speeds):
        raise ValueError('Reviewed spindle speed is outside the FluidNC spindle configuration')
