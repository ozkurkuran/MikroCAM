"""Pure current-review compensated G-code generation; no file or machine side effects."""
from collections.abc import Callable
from dataclasses import dataclass, replace

from .autolevel_surface import AutoLevelSettings, surface_height
from .autolevel_paths import check_cancel, feed_segments, work_point
from .autolevel_precision import word, float32, represented_point, certify_chord
from .cnc_job import PreparedJob, validate_job_block
from .gcode_lexer import _WORD, iter_blocks
from .gcode_models import MAX_LINES, MAX_SOURCE_BYTES, PreflightReport, SourceSnapshot
from .gcode_parser import ModalInterpreter, _parts
from .gcode_preflight import analyze_gcode
from .gcode_motion import placed_point
from .placement import Placement

MAX_OUTPUT_LINES=MAX_LINES


@dataclass(frozen=True)
class AutoLevelResult:
    original_source: SourceSnapshot
    original_report: PreflightReport
    settings: AutoLevelSettings
    prepared_job: PreparedJob
    lineage: tuple[int | None,...]

    def __post_init__(self) -> None:
        if (type(self.original_source) is not SourceSnapshot or type(self.original_report) is not PreflightReport
                or type(self.settings) is not AutoLevelSettings or type(self.prepared_job) is not PreparedJob):
            raise ValueError('Auto-level result requires exact immutable records')
        if (self.original_source.sha256!=self.original_report.source_sha256
                or self.original_source.name!=self.original_report.source_name):
            raise ValueError('Auto-level original review identity disagrees')
        if (type(self.lineage) is not tuple or len(self.lineage)!=len(self.prepared_job.source.text.splitlines())
                or any(n is not None and (type(n) is not int or not 1<=n<=MAX_LINES) for n in self.lineage)):
            raise ValueError('Auto-level lineage must identify every generated physical line')


class _Generator:
    def __init__(self, source: SourceSnapshot, report: PreflightReport, settings: AutoLevelSettings,
                 cancelled: Callable[[],bool] | None) -> None:
        self.source,self.setup,self.settings,self.cancelled=source,report.setup,settings,cancelled
        self.lines,self.lineage,self.size=[],[],0
        initial=work_point(self.setup.initial_position_mm,self.setup,settings)
        offset=settings.map.g54_offset_mm
        self.actual=tuple(float32(value+shift)-shift for value,shift in zip(initial,offset))
        self.append('; AUTOLEVEL original SHA256 '+source.sha256,None)
        self.append('; Map SHA256 '+settings.map_sha256,None)
        self.append('; Map origin '+settings.map.origin+'; reference work Z mm '+str(settings.reference_z_mm),None)
        self.append('; Surface tolerance applies to emitted chords; physical setup must be verified.',None)
        self.append('G21G90G17G94G54',None)

    def append(self, text: str, line: int | None, *, executable: bool=False) -> None:
        check_cancel(self.cancelled)
        if executable:
            validate_job_block((text+'\n').encode('ascii'))
        self.size+=len(text.encode('ascii'))+1
        if self.size>MAX_SOURCE_BYTES or len(self.lines)>=MAX_OUTPUT_LINES:
            raise ValueError('Auto-level generated source exceeds output limit')
        self.lines.append(text); self.lineage.append(line)

    def move(self, mode: int, nominal_first: tuple, nominal_last: tuple, feed: float | None,
             line: int, *, vertical_entry: bool=False) -> None:
        end=list(nominal_last)
        if mode==1:
            end[2]+=surface_height(self.settings.map,*end[:2])-self.settings.reference_z_mm
        texts=tuple(word(value) for value in end)
        serialized=tuple(float(text) for text in texts)
        actual=represented_point(serialized,self.settings.map.g54_offset_mm)
        if mode==1:
            certify_chord(self.actual,actual,nominal_first,nominal_last,self.settings,vertical_entry=vertical_entry)
        text='G'+str(mode)+''.join(axis+value for axis,value in zip('XYZ',texts))
        if mode==1:
            if feed is None:
                raise ValueError('Auto-level cutting requires verified positive feed')
            text+='F'+word(feed)
        self.append(text,line,executable=True)
        self.actual=actual

    def consume(self, block, event) -> None:
        words,g,m=_parts(block)
        if m.get('program') in (0,1) or m.get('coolant')==7:
            raise ValueError('Auto-level job cannot stream programmed pauses or optional mist')
        before=''.join(match[0].upper() for match in _WORD.finditer(block.canonical)
                       if match[1] in 'ST' or (match[1]=='M' and float(match[2]) not in (2,30)))
        if before:
            self.append(before,block.line,executable=True)
        if event.motion==0:
            self.move(0,work_point(event.start,self.setup,self.settings),
                      work_point(event.end,self.setup,self.settings),None,block.line)
        elif event.motion is not None:
            self._feed(event)
        if 'dwell' in g:
            self.append('G4'+next(match[0].upper() for match in _WORD.finditer(block.canonical)
                                  if match[1]=='P'),block.line,executable=True)
        if m.get('program') in (2,30):
            self.append('M'+str(int(m['program'])),block.line,executable=True)

    def _feed(self, event) -> None:
        if event.arc is None and event.start==event.end:
            return
        first=work_point(event.start,self.setup,self.settings)
        target_z=first[2]+surface_height(self.settings.map,*first[:2])-self.settings.reference_z_mm
        horizontal=event.arc is not None or event.start[:2]!=event.end[:2]
        mismatch=abs(self.actual[2]-target_z)>self.settings.surface_error_mm/4
        if horizontal and mismatch:
            raise ValueError('Use a vertical feed plunge before horizontal compensated cutting')
        for start,end in feed_segments(event,self.setup,self.settings,self.cancelled):
            self.move(1,start,end,event.feed,event.line,vertical_entry=not horizontal and mismatch)


def prepare_autolevel(source: SourceSnapshot, report: PreflightReport, settings: AutoLevelSettings,
                      *, cancelled: Callable[[],bool] | None=None) -> AutoLevelResult:
    """Derive an independently validated job from exactly the current immutable review."""
    if (type(source) is not SourceSnapshot or type(report) is not PreflightReport
            or type(settings) is not AutoLevelSettings):
        raise ValueError('Auto-level requires exact source, report and explicit settings')
    if cancelled is not None and not callable(cancelled):
        raise ValueError('Cancellation must be callable')
    check_cancel(cancelled)
    fresh=analyze_gcode(source,report.setup,cancelled)
    if fresh!=report or not fresh.allowed:
        raise ValueError('Auto-level requires the exact fresh allowed original preflight')
    generator=_Generator(source,report,settings,cancelled)
    parser=ModalInterpreter(report.setup.initial_position_mm)
    for block in iter_blocks(source.text,cancelled):
        try:
            generator.consume(block,parser.consume(block))
        except ValueError as error:
            raise ValueError(f'Auto-level original line {block.line}: {error}') from error
    generated=SourceSnapshot(('AUTOLEVEL - '+source.name)[:256],'\n'.join(generator.lines)+'\n')
    offset=settings.map.g54_offset_mm
    initial=work_point(report.setup.initial_position_mm,report.setup,settings)
    setup=replace(report.setup,initial_position_mm=initial,placement=Placement(translation=offset[:2]),
                  z_offset_mm=offset[2])
    derived_report=analyze_gcode(generated,setup,cancelled)
    if not derived_report.allowed:
        raise ValueError('Auto-level derived preflight blocked: '+str(derived_report.findings[:3]))
    job=PreparedJob(generated,derived_report,cancelled=cancelled)
    check_cancel(cancelled)
    return AutoLevelResult(source,report,settings,job,tuple(generator.lineage))
