"""Review-bound mechanical job preparation; no transport or output side effects."""
from collections.abc import Callable
from dataclasses import InitVar, dataclass, field
import math
import struct

from .gcode_lexer import _WORD, iter_blocks
from .gcode_models import MAX_LINES, XYZ, PreflightCancelled, PreflightReport, SourceSnapshot
from .gcode_motion import placed_point
from .gcode_parser import ModalInterpreter, _metadata, _parts
from .gcode_preflight import analyze_gcode


def validate_job_block(data: bytes) -> None:
    """Reject noncanonical/unsupported blocks and GRBL's eight-digit truncation risk."""
    if type(data) is not bytes or not 1 < len(data) <= 79 or not data.endswith(b'\n'):
        raise ValueError('Job block requires canonical bytes with LF, at most79 bytes')
    try:
        text = data[:-1].decode('ascii')
    except UnicodeDecodeError as error:
        raise ValueError('Job block must be ASCII') from error
    blocks = tuple(iter_blocks(text))
    if len(blocks) != 1 or blocks[0].canonical != text:
        raise ValueError('Job block must contain one canonical executable block')
    for match in _WORD.finditer(text):
        numeric = match.group(2)
        if sum(character.isdigit() for character in numeric) > 8:
            raise ValueError('GRBL numeric precision requires at most8 digits including leading zeros')
        value = float(numeric)
        try:
            rounded = struct.unpack('f', struct.pack('f', value))[0]
        except OverflowError as error:
            raise ValueError('GRBL numeric precision exceeds float32') from error
        if not math.isfinite(rounded) or (value != 0 and rounded == 0):
            raise ValueError('GRBL numeric precision loses a nonzero value')
    words, g, m = _parts(blocks[0])
    _metadata(words, m, blocks[0].line)
    if m.get('program') in (0, 1) or m.get('coolant') == 7:
        raise ValueError('Program pauses and optional mist are unsupported for streaming')
    axes, centers = set(words)&set('XYZ'), set(words)&set('IJR')
    if 'tool' in g and (axes or centers or 'motion' in g):
        raise ValueError('G49 cannot carry movement')
    if 'dwell' in g:
        if 'P' not in words or words['P'] < 0 or axes or centers or 'motion' in g:
            raise ValueError('Invalid dwell block')
    elif 'P' in words:
        raise ValueError('P requires G4')
    if centers and (g.get('motion') in (0, 1) or not axes.intersection('XY')
                    or ('R' in words and centers.intersection('IJ'))):
        raise ValueError('Invalid arc words')


@dataclass(frozen=True)
class JobBlock:
    source_line: int
    wire: bytes

    def __post_init__(self) -> None:
        if type(self.source_line) is not int or not 1 <= self.source_line <= MAX_LINES:
            raise ValueError('Source line must be a bounded positive integer')
        validate_job_block(self.wire)


@dataclass(frozen=True)
class PreparedJob:
    source: SourceSnapshot
    report: PreflightReport
    cancelled: InitVar[Callable[[], bool] | None] = field(default=None, kw_only=True)
    blocks: tuple[JobBlock, ...] = field(init=False)
    initial_machine_mm: XYZ = field(init=False)
    final_machine_mm: XYZ = field(init=False)
    g54_offset_mm: XYZ = field(init=False)
    spindle_speeds: tuple[float, ...] = field(init=False)
    ack_timeout_seconds: float = field(init=False)

    def __post_init__(self, cancelled: Callable[[], bool] | None) -> None:
        if type(self.source) is not SourceSnapshot or type(self.report) is not PreflightReport:
            raise ValueError('Prepared job requires exact source and report types')
        if cancelled is not None and not callable(cancelled):
            raise ValueError('Cancellation must be callable')
        fresh = analyze_gcode(self.source, self.report.setup, cancelled)
        if fresh != self.report or not fresh.allowed:
            raise ValueError('Reviewed report must equal fresh allowed analysis')
        setup = fresh.setup
        if setup.placement.matrix[:4] != (1., 0., 0., 1.):
            raise ValueError('Streaming permits translation only')
        seconds = fresh.duration_seconds
        if setup.rapid_rates_mm_min is None or seconds is None or not 0 < seconds <= 8640:
            raise ValueError('Explicit rapid rates and positive bounded nominal duration are required')
        interpreter = ModalInterpreter(setup.initial_position_mm)
        blocks, speeds, seen, speed, active = [], [], set(), None, False
        for block in iter_blocks(self.source.text, cancelled):
            blocks.append(JobBlock(block.line, (block.canonical+'\n').encode('ascii')))
            words, _, modes = _parts(block)
            if 'S' in words:
                speed = words['S']
            if 'spindle' in modes:
                active = modes['spindle'] in (3, 4)
            if active:
                if speed is None or speed <= 0:
                    raise ValueError('Active spindle requires explicit positive S')
                if speed not in seen:
                    seen.add(speed)
                    speeds.append(speed)
            interpreter.consume(block)
        if cancelled is not None and cancelled():
            raise PreflightCancelled('Preparation cancelled')
        values = dict(blocks=tuple(blocks), spindle_speeds=tuple(speeds),
                      initial_machine_mm=placed_point(setup.initial_position_mm, setup.placement, setup.z_offset_mm),
                      final_machine_mm=placed_point(interpreter.state.position, setup.placement, setup.z_offset_mm),
                      g54_offset_mm=(*setup.placement.matrix[4:], setup.z_offset_mm),
                      ack_timeout_seconds=min(86400., max(30., 10*seconds+30)))
        for name, value in values.items():
            object.__setattr__(self, name, value)
