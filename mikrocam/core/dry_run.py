"""Pure reviewed-source XY projection at an explicitly declared machine Z plane."""
from collections.abc import Callable
from dataclasses import dataclass, replace
from decimal import Decimal
import math

from .cnc_job import PreparedJob
from .gcode_lexer import _WORD, iter_blocks
from .gcode_models import (MAX_LINES, MAX_SOURCE_BYTES, PreflightCancelled,
                           PreflightReport, SourceSnapshot)
from .gcode_motion import placed_point
from .gcode_parser import ModalInterpreter
from .gcode_preflight import analyze_gcode


@dataclass(frozen=True)
class DryRunResult:
    original_source: SourceSnapshot
    original_report: PreflightReport
    dry_z_mm: float
    prepared_job: PreparedJob
    lineage: tuple[int | None, ...]

    def __post_init__(self) -> None:
        if (type(self.original_source) is not SourceSnapshot
                or type(self.original_report) is not PreflightReport
                or type(self.prepared_job) is not PreparedJob):
            raise ValueError('Dry run requires immutable source, report and prepared job')
        if (self.original_source.sha256 != self.original_report.source_sha256
                or self.original_source.name != self.original_report.source_name):
            raise ValueError('Original source and review identity disagree')
        object.__setattr__(self, 'dry_z_mm', _height(self.dry_z_mm))
        original_lines = min(MAX_LINES,len(self.original_source.text.splitlines()))
        if (type(self.lineage) is not tuple
                or len(self.lineage) != len(self.prepared_job.source.text.splitlines())
                or any(line is not None and (type(line) is not int or not 1 <= line
                                             <= original_lines)
                       for line in self.lineage)):
            raise ValueError('Lineage must map every derived physical line to an original line or None')


def _height(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Dry Z must be an explicit finite number')
    try:
        height = float(value)
    except OverflowError as error:
        raise ValueError('Dry Z must be finite') from error
    if not math.isfinite(height):
        raise ValueError('Dry Z must be finite')
    return height


def _decimal_z(height: float, offset: float) -> str:
    # Exact decimal subtraction avoids inserting binary subtraction artifacts or rounding down.
    value = Decimal(str(height)) - Decimal(str(offset))
    text = format(value, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    if sum(character.isdigit() for character in text) > 8:
        raise ValueError('Dry Z cannot be represented without rounding within GRBL eight-digit precision')
    return text


def _project(canonical: str) -> str:
    retained = []
    for match in _WORD.finditer(canonical):
        letter, numeric = match.groups()
        if letter in 'ZST' or (letter == 'M' and Decimal(numeric) in (3,4,7,8)):
            continue
        retained.append(letter+numeric)
    return ''.join(retained)


def _derived_source(source: SourceSnapshot, report: PreflightReport, height: float,
                    cancelled: Callable[[], bool] | None) -> tuple[SourceSnapshot, tuple[int | None, ...]]:
    lines, lineage, size = [], [], 0

    def append(text: str, original: int | None) -> None:
        nonlocal size
        if cancelled is not None and cancelled():
            raise PreflightCancelled('Dry-run preparation cancelled')
        size += len(text.encode('ascii')) + 1
        if size > MAX_SOURCE_BYTES or len(lines) >= MAX_LINES:
            raise ValueError('Generated dry-run source exceeds resource limits')
        lines.append(text)
        lineage.append(original)

    append('; DRY RUN original SHA256 '+source.sha256, None)
    append('; Machine dry Z mm '+str(height), None)
    append('G21G90G17G94', None)
    append('M5M9', None)
    setup = report.setup
    initial = placed_point(setup.initial_position_mm, setup.placement, setup.z_offset_mm)
    if height > initial[2]:
        append('G0Z'+_decimal_z(height, setup.z_offset_mm), None)
    interpreter, has_xy = ModalInterpreter(setup.initial_position_mm), False
    for block in iter_blocks(source.text, cancelled):
        if any(letter == 'M' and value in (0,1) for letter, value in block.words):
            raise ValueError('Programmed pauses cannot be projected into a dry run')
        event = interpreter.consume(block)
        has_xy |= event.arc is not None or event.start[:2] != event.end[:2]
        projected = _project(block.canonical)
        if projected:
            append(projected, block.line)
    if not has_xy:
        raise ValueError('Dry run requires positive XY travel')
    return SourceSnapshot(('DRY RUN - '+source.name)[:256], '\n'.join(lines)+'\n'), tuple(lineage)


def prepare_dry_run(source: SourceSnapshot, report: PreflightReport, dry_z_mm: float, *,
                    cancelled: Callable[[], bool] | None = None) -> DryRunResult:
    """Derive and independently validate a separate job; never rewrite the original or transmit."""
    if type(source) is not SourceSnapshot or type(report) is not PreflightReport:
        raise ValueError('Dry run requires exact source and report types')
    if cancelled is not None and not callable(cancelled):
        raise ValueError('Cancellation must be callable')
    fresh = analyze_gcode(source, report.setup, cancelled)
    if fresh != report or not fresh.allowed:
        raise ValueError('Original review must equal fresh allowed analysis')
    height, setup = _height(dry_z_mm), report.setup
    if setup.placement.matrix[:4] != (1.,0.,0.,1.):
        raise ValueError('Dry run supports pure translation only')
    initial = placed_point(setup.initial_position_mm, setup.placement, setup.z_offset_mm)
    if not max(initial[2],setup.safe_z_mm,setup.machine_min_mm[2]) <= height <= setup.machine_max_mm[2]:
        raise ValueError('Dry Z must be at or above initial/safe Z and within the machine envelope')
    derived, lineage = _derived_source(source, report, height, cancelled)
    derived_report = analyze_gcode(derived, replace(setup,safe_z_mm=height), cancelled)
    job = PreparedJob(derived, derived_report, cancelled=cancelled)
    if cancelled is not None and cancelled():
        raise PreflightCancelled('Dry-run preparation cancelled')
    return DryRunResult(source, report, height, job, lineage)
