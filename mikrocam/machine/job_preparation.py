"""Strict provisional evidence for the one mechanical CNC stream."""
from math import isfinite
import re

from mikrocam.core.cnc_job import PreparedJob
from .manual_models import PARAMETER_NAMES
from .manual_protocol import parse_modal, parse_parameter, parse_startup


def near(actual: tuple | None, expected: tuple) -> bool:
    """Controller-reported coordinates have a declared .005mm comparison tolerance."""
    return actual is not None and len(actual) == len(expected) and all(
        abs(a - b) <= .005 for a, b in zip(actual, expected))


def query_record(purpose: str, line: str, units: str) -> tuple | None:
    """Return a typed provisional record; acknowledgement still belongs to caller."""
    if purpose == 'startup':
        item = parse_startup(line)
        if item is not None:
            return item.index, item.block
    elif purpose == 'settings' and line.startswith('$'):
        match = re.fullmatch(r'\$(\d+)=([+-]?(?:\d+(?:\.\d*)?|\.\d+))', line)
        if match is None or not isfinite(float(match[2])):
            raise ValueError('Malformed job settings evidence')
        return int(match[1]), float(match[2])
    elif purpose in ('modal', 'final_modal'):
        item = parse_modal(line)
        if item is not None:
            return 'modal', item
    elif purpose == 'parameters':
        item = parse_parameter(line, units)
        if item is not None:
            return item.name, item.value
    return None


def verify_settings(records: dict, job: PreparedJob, units: str) -> None:
    """Settings are policy evidence, not proof of the physically connected spindle."""
    if not {13, 30, 31, 32}.issubset(records):
        raise ValueError('Missing mechanical spindle/report-unit settings')
    if records[13] != (1 if units == 'inch' else 0) or records[32] != 0:
        raise ValueError('Mechanical mode and unchanged report units are required')
    minimum, maximum = records[31], records[30]
    if not 0 <= minimum < maximum:
        raise ValueError('Invalid spindle speed configuration')
    if any(not minimum <= speed <= maximum for speed in job.spindle_speeds):
        raise ValueError('Reviewed spindle speed is outside controller configuration')


def verify_parameters(records: dict, job: PreparedJob) -> None:
    """Require the complete inventory, fixed G54 and zero temporary/tool offsets."""
    if set(records) != set(PARAMETER_NAMES):
        raise ValueError('Missing or duplicate coordinate parameter inventory')
    if records['G92'] != (0., 0., 0.) or records['TLO'] != 0:
        raise ValueError('Streaming requires zero G92 and tool-length offset')
    if not near(records['G54'], job.g54_offset_mm):
        raise ValueError('Actual G54 does not match the reviewed setup')


def verify_modal(records: dict) -> None:
    """Parser-reported output-off and G54 are required, not physical power claims."""
    modal = records.get('modal')
    if modal is None or modal.work_system != 'G54' or modal.spindle != 'M5' or modal.coolant != ('M9',):
        raise ValueError('G54 and controller-reported output-off could not be verified')
