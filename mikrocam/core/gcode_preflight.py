"""Read-only online preflight for a strict, explicitly declared GRBL-oriented setup."""
from collections.abc import Callable

from .gcode_lexer import GcodeError, iter_blocks
from .gcode_models import (Finding, MAX_FINDINGS, PreflightCancelled, PreflightReport,
                           PreflightSetup, SourceSnapshot)
from .gcode_motion import motion_bounds, motion_length, placed_point
from .gcode_parser import Event, ModalInterpreter


class _Analysis:
    def __init__(self, setup: PreflightSetup) -> None:
        self.setup=setup
        self.findings: list[Finding]=[]
        self.finding_count=self.error_count=self.blocks=0
        self.rapid_count=self.linear_count=self.arc_count=0
        self.distance=self.seconds=0.
        self.time_known=True
        point=placed_point(setup.initial_position_mm,setup.placement,setup.z_offset_mm)
        self.bounds=(point,point)
        self._check_bounds(self.bounds,0)

    def add(self, finding: Finding) -> None:
        self.finding_count+=1
        self.error_count+=finding.severity=='error'
        if len(self.findings)<MAX_FINDINGS:
            self.findings.append(finding)

    def _check_bounds(self, bounds: tuple, line: int) -> None:
        axes=[axis for i,axis in enumerate('XYZ') if
              bounds[0][i]<self.setup.machine_min_mm[i]-1e-9 or bounds[1][i]>self.setup.machine_max_mm[i]+1e-9]
        if axes:
            self.add(Finding(line,'travel-bounds','Travel exceeds declared machine bounds on '+','.join(axes)))

    def consume(self, event: Event) -> None:
        for finding in event.findings:
            self.add(finding)
        self.seconds+=event.dwell
        if event.pause:
            self.time_known=False
        if event.motion is None:
            return
        bounds=motion_bounds(event.start,event.end,self.setup.placement,self.setup.z_offset_mm,event.arc)
        self._check_bounds(bounds,event.line)
        self.bounds=(tuple(min(a,b) for a,b in zip(self.bounds[0],bounds[0])),
                     tuple(max(a,b) for a,b in zip(self.bounds[1],bounds[1])))
        length=motion_length(event.start,event.end,event.arc)
        self.distance+=length
        if event.motion==0:
            self.rapid_count+=1
            self._rapid(event,length)
        else:
            self.arc_count+=event.arc is not None
            self.linear_count+=event.arc is None
            if event.feed is None:
                self.time_known=False
                self.add(Finding(event.line,'missing-feed','Feed movement has no verified positive G94 feed'))
            else:
                self.seconds+=60*length/event.feed

    def _rapid(self, event: Event, length: float) -> None:
        first=placed_point(event.start,self.setup.placement,self.setup.z_offset_mm)
        last=placed_point(event.end,self.setup.placement,self.setup.z_offset_mm)
        horizontal=first[:2]!=last[:2]
        below=min(first[2],last[2])<self.setup.safe_z_mm-1e-9
        descending=last[2]<first[2]
        if below and (horizontal or descending):
            self.add(Finding(event.line,'unsafe-rapid','Horizontal or downward rapid travels below declared safe Z'))
        rates=self.setup.rapid_rates_mm_min
        if length>0 and rates is None:
            self.time_known=False
        elif rates is not None:
            self.seconds+=60*max(abs(b-a)/rate for a,b,rate in zip(first,last,rates))

    def report(self, source: SourceSnapshot, parser: ModalInterpreter, complete: bool) -> PreflightReport:
        if complete and self.distance==0:
            self.add(Finding(0,'no-motion','Program contains no nonzero supported movement'))
        return PreflightReport(source.name,source.sha256,self.setup,complete,self.bounds,self.blocks,
                               self.rapid_count,self.linear_count,self.arc_count,self.distance,
                               self.seconds if complete and self.time_known else None,
                               tuple(parser.units_seen),tuple(parser.distance_modes_seen),
                               tuple(self.findings),self.finding_count,self.error_count)


def analyze_gcode(source: SourceSnapshot, setup: PreflightSetup,
                  cancelled: Callable[[], bool] | None = None) -> PreflightReport:
    """Analyze immutable source/setup without reading machine state, writing or sending text."""
    if not isinstance(source,SourceSnapshot) or not isinstance(setup,PreflightSetup):
        raise ValueError('Preflight requires immutable source and explicit setup')
    if cancelled is not None and cancelled():
        raise PreflightCancelled('Preflight cancelled')
    analysis,parser=_Analysis(setup),ModalInterpreter(setup.initial_position_mm)
    complete=True
    try:
        for block in iter_blocks(source.text,cancelled):
            analysis.blocks+=1
            analysis.consume(parser.consume(block))
    except GcodeError as error:
        complete=False
        analysis.add(Finding(error.line,error.code,str(error)[:256]))
    if cancelled is not None and cancelled():
        raise PreflightCancelled('Preflight cancelled')
    return analysis.report(source,parser,complete)
