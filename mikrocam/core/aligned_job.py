"""Realise a reviewed non-translation Placement as a separate translation-only G54 job.

GRBL streams reviewed G-code unchanged under G54, so rotation/affine fiducial corrections
are written into XY coordinates here using the same Placement as preflight. Arcs become
chords because an affine image of a circle is an ellipse. No file or machine side effects.
"""
from collections.abc import Callable
from dataclasses import dataclass, replace
import math

from .cnc_job import PreparedJob, validate_job_block
from .gcode_lexer import _WORD, iter_blocks
from .gcode_models import (MAX_LINES, MAX_SOURCE_BYTES, XYZ, PreflightCancelled, PreflightReport,
                           SourceSnapshot, _number)
from .gcode_motion import placed_point
from .gcode_parser import ModalInterpreter, _parts
from .gcode_preflight import analyze_gcode
from .placement import Placement


MAX_DIGITS = 8
BOUNDS_SLACK_MM = .001


@dataclass(frozen=True)
class AlignedJobResult:
    original_source: SourceSnapshot
    original_report: PreflightReport
    g54_offset_mm: XYZ
    chord_error_mm: float
    prepared_job: PreparedJob
    lineage: tuple[int | None, ...]

    def __post_init__(self) -> None:
        if (type(self.original_source) is not SourceSnapshot or type(self.original_report) is not PreflightReport
                or type(self.prepared_job) is not PreparedJob):
            raise ValueError('Aligned job requires exact immutable records')
        if (type(self.lineage) is not tuple
                or len(self.lineage) != len(self.prepared_job.source.text.splitlines())):
            raise ValueError('Aligned lineage must identify every generated physical line')


def _check(cancelled: Callable[[], bool] | None) -> None:
    if cancelled is not None and cancelled():
        raise PreflightCancelled('Aligned job preparation cancelled')


def _word(value: float, tolerance: float) -> str:
    """Shortest GRBL eight-digit decimal within tolerance; otherwise refuse."""
    for decimals in range(5, -1, -1):
        text = format(value, f'.{decimals}f')
        if '.' in text:
            text = text.rstrip('0').rstrip('.')
        text = '0' if text in ('-0', '') else text
        if sum(ch.isdigit() for ch in text) <= MAX_DIGITS:
            if abs(float(text) - value) > tolerance:
                break
            return text
    raise ValueError('Aligned work coordinate cannot be represented within GRBL eight-digit precision')


class _Writer:
    def __init__(self, setup, g54: XYZ, chord: float, cancelled) -> None:
        self.setup, self.g54, self.chord, self.cancelled = setup, g54, chord, cancelled
        a, b, d, e = setup.placement.matrix[:4]
        # Frobenius norm bounds the largest stretch, so source sagitta maps within tolerance.
        self.stretch = max(math.sqrt(a*a + b*b + d*d + e*e), 1.)
        self.lines: list[str] = []
        self.lineage: list[int | None] = []
        self.size = 0

    def append(self, text: str, line: int | None, *, executable: bool = False) -> None:
        _check(self.cancelled)
        if executable:
            validate_job_block((text + '\n').encode('ascii'))
        self.size += len(text) + 1
        if self.size > MAX_SOURCE_BYTES or len(self.lines) >= MAX_LINES:
            raise ValueError('Aligned job exceeds the source output limit')
        self.lines.append(text)
        self.lineage.append(line)

    def work(self, point: XYZ) -> XYZ:
        machine = placed_point(point, self.setup.placement, self.setup.z_offset_mm)
        return tuple(value - shift for value, shift in zip(machine, self.g54))

    def move(self, mode: int, point: XYZ, feed: float | None, line: int) -> None:
        tolerance = min(self.chord / 4, .0005)
        text = f'G{mode}' + ''.join(axis + _word(value, tolerance) for axis, value in zip('XYZ', self.work(point)))
        if mode == 1:
            if feed is None or feed <= 0:
                raise ValueError('Aligned cutting requires a verified positive feed')
            text += 'F' + _word(feed, .0005)
        self.append(text, line, executable=True)

    def arc(self, event) -> None:
        arc, start, end = event.arc, event.start, event.end
        r0 = math.dist(start[:2], arc.center)
        r1 = math.dist(end[:2], arc.center)
        ratio = min(1., self.chord / (max(r0, r1) * self.stretch))
        step = max(2 * math.acos(1 - ratio), 1e-6)
        count = max(1, math.ceil(abs(arc.sweep) / step))
        if count > MAX_LINES:
            raise ValueError('Aligned arc subdivision exceeds work limit')
        for index in range(1, count + 1):
            fraction = index / count
            if index == count:
                point = end
            else:
                theta = arc.start_angle + arc.sweep * fraction
                radius = r0 + (r1 - r0) * fraction
                point = (arc.center[0] + radius * math.cos(theta), arc.center[1] + radius * math.sin(theta),
                         start[2] + (end[2] - start[2]) * fraction)
            self.move(1, point, event.feed, event.line)

    def consume(self, block, event) -> None:
        words, g, m = _parts(block)
        if m.get('program') in (0, 1) or m.get('coolant') == 7:
            raise ValueError('Aligned job cannot stream programmed pauses or optional mist')
        before = ''.join(match[0].upper() for match in _WORD.finditer(block.canonical)
                         if match[1] in 'ST' or (match[1] == 'M' and float(match[2]) not in (2, 30)))
        if before:
            self.append(before, block.line, executable=True)
        if event.motion == 0:
            self.move(0, event.end, None, block.line)
        elif event.motion is not None and event.arc is not None:
            self.arc(event)
        elif event.motion is not None and event.start != event.end:
            self.move(1, event.end, event.feed, block.line)
        if 'dwell' in g:
            self.append('G4' + next(match[0].upper() for match in _WORD.finditer(block.canonical)
                                    if match[1] == 'P'), block.line, executable=True)
        if m.get('program') in (2, 30):
            self.append('M' + str(int(m['program'])), block.line, executable=True)


def _inputs(source, report, g54_xy, chord_error_mm, cancelled) -> tuple[XYZ, float]:
    if type(source) is not SourceSnapshot or type(report) is not PreflightReport:
        raise ValueError('Aligned job requires exact source and report types')
    if cancelled is not None and not callable(cancelled):
        raise ValueError('Cancellation must be callable')
    if type(g54_xy) is not tuple or len(g54_xy) != 2:
        raise ValueError('G54 XY must be an explicit two-value tuple')
    chord = _number(chord_error_mm, 'chord_error_mm')
    if not .0001 <= chord <= .1:
        raise ValueError('Chord error requires .0001..0.1mm')
    if report.setup.placement.matrix[:4] == (1., 0., 0., 1.):
        raise ValueError('Reviewed placement is translation only; transfer the reviewed job directly')
    g54 = (_number(g54_xy[0], 'G54 X'), _number(g54_xy[1], 'G54 Y'), report.setup.z_offset_mm)
    return g54, chord


def _within(inner, outer) -> bool:
    return (all(a >= b - BOUNDS_SLACK_MM for a, b in zip(inner[0], outer[0]))
            and all(a <= b + BOUNDS_SLACK_MM for a, b in zip(inner[1], outer[1])))


def prepare_aligned_job(source: SourceSnapshot, report: PreflightReport, g54_xy_mm: tuple[float, float], *,
                        chord_error_mm: float,
                        cancelled: Callable[[], bool] | None = None) -> AlignedJobResult:
    """Derive and independently validate the aligned job from exactly the current review."""
    g54, chord = _inputs(source, report, g54_xy_mm, chord_error_mm, cancelled)
    _check(cancelled)
    fresh = analyze_gcode(source, report.setup, cancelled)
    if fresh != report or not fresh.allowed:
        raise ValueError('Aligned job requires the exact fresh allowed original preflight')
    writer = _Writer(report.setup, g54, chord, cancelled)
    writer.append('; ALIGNED original SHA256 ' + source.sha256, None)
    writer.append('; Placement matrix ' + ' '.join(f'{v:.9g}' for v in report.setup.placement.matrix), None)
    writer.append('; G54 offset mm ' + ' '.join(f'{v:.9g}' for v in g54), None)
    writer.append('G21G90G17G94G54', None)
    parser = ModalInterpreter(report.setup.initial_position_mm)
    for block in iter_blocks(source.text, cancelled):
        try:
            writer.consume(block, parser.consume(block))
        except ValueError as error:
            raise ValueError(f'Aligned job original line {block.line}: {error}') from error
    generated = SourceSnapshot(('ALIGNED - ' + source.name)[:256], '\n'.join(writer.lines) + '\n')
    setup = replace(report.setup, initial_position_mm=writer.work(report.setup.initial_position_mm),
                    placement=Placement(translation=g54[:2]))
    derived = analyze_gcode(generated, setup, cancelled)
    if not derived.allowed:
        raise ValueError('Aligned derived preflight blocked: ' + str(derived.findings[:3]))
    if not _within(derived.bounds_mm, report.bounds_mm):
        raise ValueError('Aligned derived bounds exceed the reviewed original bounds')
    job = PreparedJob(generated, derived, cancelled=cancelled)
    _check(cancelled)
    return AlignedJobResult(source, report, g54, chord, job, tuple(writer.lineage))
