"""Concrete bounded modal interpreter; validate each entire block before state advances."""
from dataclasses import dataclass, replace

from .gcode_lexer import Block, GcodeError
from .gcode_models import Finding, MAX_MAGNITUDE, XYZ
from .gcode_motion import Arc, make_arc

_G_GROUPS = {0:'motion',1:'motion',2:'motion',3:'motion',20:'units',21:'units',
             90:'distance',91:'distance',17:'plane',91.1:'centers',94:'feedmode',
             54:'wcs',40:'cutter',49:'tool',4:'dwell'}
_M_GROUPS = {0:'program',1:'program',2:'program',30:'program',3:'spindle',4:'spindle',
             5:'spindle',7:'coolant',8:'coolant',9:'coolant'}


@dataclass(frozen=True)
class Event:
    line: int
    start: XYZ
    end: XYZ
    motion: int | None = None
    feed: float | None = None
    arc: Arc | None = None
    dwell: float = 0.
    pause: bool = False
    findings: tuple[Finding, ...] = ()


@dataclass
class _State:
    position: XYZ
    factor: float | None = None
    absolute: bool | None = None
    plane: bool = False
    feedmode: bool = False
    motion: int | None = None
    feed: float | None = None
    ended: bool = False


def _groups(values: list[float], allowed: dict, line: int, letter: str) -> dict:
    result = {}
    for value in values:
        if value not in allowed:
            raise GcodeError(line,'unsupported-mode',f'Unsupported {letter}{value:g}')
        group=allowed[value]
        if group in result:
            raise GcodeError(line,'modal-conflict',f'Conflicting {letter} words in {group} group')
        result[group]=value
    return result


def _parts(block: Block) -> tuple[dict, dict, dict]:
    singles,g,m={},[],[]
    for letter,value in block.words:
        if letter in 'GM':
            (g if letter=='G' else m).append(value)
        elif letter not in 'XYZFIJRPNST':
            raise GcodeError(block.line,'unsupported-word',f'Unsupported word {letter}')
        elif letter in singles:
            raise GcodeError(block.line,'duplicate-word',f'Duplicate {letter} word')
        else:
            singles[letter]=value
    return singles,_groups(g,_G_GROUPS,block.line,'G'),_groups(m,_M_GROUPS,block.line,'M')


def _metadata(words: dict, modes: dict, line: int) -> tuple[Finding, ...]:
    for key in ('N','S','T'):
        if key in words and (words[key]<0 or (key!='S' and not words[key].is_integer())):
            raise GcodeError(line,'invalid-metadata',f'{key} must be nonnegative'+(' integer' if key!='S' else ''))
    if words.get('N',0)>9999999:
        raise GcodeError(line,'invalid-metadata','N exceeds supported line number range')
    if modes.get('spindle') in (3,4) or modes.get('coolant') in (7,8):
        return (Finding(line,'output-command','Program requests spindle/laser or coolant output; analysis never transmits it','warning'),)
    return ()


class ModalInterpreter:
    def __init__(self, initial: XYZ) -> None:
        self.state=_State(initial)
        self.units_seen: list[str]=[]
        self.distance_modes_seen: list[str]=[]

    def consume(self, block: Block) -> Event:
        if self.state.ended:
            raise GcodeError(block.line,'after-end','Executable words follow program end')
        words,g,m=_parts(block)
        state=replace(self.state)
        self._modes(state,g)
        findings=list(_metadata(words,m,block.line))
        self._feed(state,words,block.line,findings)
        event=self._event(state,words,g,block.line)
        state.position=event.end
        state.ended=m.get('program') in (2,30)
        self.state=state
        for key,collection,label in (('units',self.units_seen,'mm' if state.factor==1 else 'inch'),
                                     ('distance',self.distance_modes_seen,'absolute' if state.absolute else 'incremental')):
            if key in g and label not in collection:
                collection.append(label)
        return replace(event,findings=tuple(findings),pause=m.get('program') in (0,1))

    @staticmethod
    def _modes(state: _State, groups: dict) -> None:
        if 'units' in groups:
            state.factor=1. if groups['units']==21 else 25.4
        if 'distance' in groups:
            state.absolute=groups['distance']==90
        if 'plane' in groups:
            state.plane=True
        if 'feedmode' in groups:
            state.feedmode=True
        if 'motion' in groups:
            state.motion=int(groups['motion'])

    @staticmethod
    def _feed(state: _State, words: dict, line: int, findings: list[Finding]) -> None:
        if 'F' not in words:
            return
        if state.factor is None or not state.feedmode:
            raise GcodeError(line,'missing-mode','Explicit units and G94 are required before F')
        value=words['F']*state.factor
        if abs(value)>MAX_MAGNITUDE:
            raise GcodeError(line,'numeric-range','Normalized feed exceeds supported range')
        state.feed=value if value>0 else None
        if value<=0:
            findings.append(Finding(line,'invalid-feed','Feed must be positive'))

    def _event(self, state: _State, words: dict, groups: dict, line: int) -> Event:
        axes=set(words)&set('XYZ')
        centers=set(words)&set('IJR')
        if 'dwell' in groups:
            if 'P' not in words or words['P']<0 or axes or centers or 'motion' in groups:
                raise GcodeError(line,'invalid-dwell','G4 requires nonnegative P and no movement words')
            return Event(line,state.position,state.position,dwell=words['P'])
        if 'P' in words:
            raise GcodeError(line,'unused-word','P is supported only with G4 dwell')
        if not axes and not centers and groups.get('motion') not in (2,3):
            return Event(line,state.position,state.position)
        if state.factor is None or state.absolute is None or state.motion is None:
            raise GcodeError(line,'missing-mode','Explicit units, distance and motion modes are required')
        if state.motion!=0 and not state.feedmode:
            raise GcodeError(line,'missing-mode','Explicit G94 is required before feed motion')
        end=tuple(state.position[i] if axis not in words else words[axis]*state.factor
                  +(0 if state.absolute else state.position[i]) for i,axis in enumerate('XYZ'))
        if any(abs(value)>MAX_MAGNITUDE for value in end):
            raise GcodeError(line,'numeric-range','Normalized endpoint exceeds supported range')
        arc=None
        if state.motion in (2,3):
            arc=self._arc(state,end,words,axes,line)
        elif centers:
            raise GcodeError(line,'unused-word','I/J/R are supported only for XY arcs')
        return Event(line,state.position,end,state.motion,state.feed,arc)

    @staticmethod
    def _arc(state: _State, end: XYZ, words: dict, axes: set, line: int) -> Arc:
        if not state.plane or not axes.intersection('XY'):
            raise GcodeError(line,'arc-plane','G17 and an explicit X or Y endpoint are required for arcs')
        ij=(words.get('I',0.)*state.factor,words.get('J',0.)*state.factor) if set(words)&set('IJ') else None
        radius=words['R']*state.factor if 'R' in words else None
        return make_arc(state.position,end,state.motion==2,ij=ij,radius=radius,line=line)
