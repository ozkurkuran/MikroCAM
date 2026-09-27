"""Independent analytic XY arc geometry and machine-space travel extents."""
from dataclasses import dataclass
import math

from .gcode_lexer import GcodeError
from .gcode_models import XYZ
from .placement import Placement

_TAU = 2 * math.pi


@dataclass(frozen=True)
class Arc:
    center: tuple[float, float]
    radius: float
    start_angle: float
    sweep: float


def _sweep(start: float, end: float, clockwise: bool, full: bool = False) -> float:
    if full:
        return -_TAU if clockwise else _TAU
    return -((start-end) % _TAU) if clockwise else (end-start) % _TAU


def _center_arc(start: XYZ, end: XYZ, center: tuple[float, float], clockwise: bool,
                line: int) -> Arc:
    first = (start[0]-center[0], start[1]-center[1])
    last = (end[0]-center[0], end[1]-center[1])
    r1, r2 = math.hypot(*first), math.hypot(*last)
    if r1 <= 0 or abs(r1-r2) > .005:
        raise GcodeError(line, 'arc-geometry', 'Arc radii are zero or inconsistent by more than0.005mm')
    angle = math.atan2(first[1],first[0])
    sweep = _sweep(angle, math.atan2(last[1],last[0]), clockwise, start[:2] == end[:2])
    if abs(sweep) < 1e-6:
        raise GcodeError(line, 'arc-geometry', 'Near-zero arc angle is ambiguous with controller full-circle handling')
    # Conservative radius includes permitted endpoint rounding rather than clipping that endpoint.
    return Arc(center, max(r1,r2), angle, sweep)


def make_arc(start: XYZ, end: XYZ, clockwise: bool, *, ij: tuple[float, float] | None = None,
             radius: float | None = None, line: int = 0) -> Arc:
    """Construct a relative-center or signed-radius arc; ambiguous forms fail closed."""
    if (ij is None) == (radius is None):
        raise GcodeError(line, 'arc-geometry', 'Arc requires either relative I/J or signed R')
    if ij is not None:
        return _center_arc(start,end,(start[0]+ij[0],start[1]+ij[1]),clockwise,line)
    dx,dy=end[0]-start[0],end[1]-start[1]
    chord=math.hypot(dx,dy)
    if not radius or not chord or chord > 2*abs(radius):
        raise GcodeError(line,'arc-geometry','Radius arc is impossible, zero-radius or a full circle')
    height=math.sqrt(max(0.,radius*radius-chord*chord/4))
    middle=((start[0]+end[0])/2,(start[1]+end[1])/2)
    for sign in (1,-1):
        center=(middle[0]-sign*dy*height/chord,middle[1]+sign*dx*height/chord)
        arc=_center_arc(start,end,center,clockwise,line)
        if (radius>0 and abs(arc.sweep)<=math.pi+1e-12) or (radius<0 and abs(arc.sweep)>=math.pi-1e-12):
            return arc
    raise GcodeError(line,'arc-geometry','Could not determine unambiguous radius arc')


def placed_point(point: XYZ, placement: Placement, z_offset: float) -> XYZ:
    return (*placement.apply_point(point[:2]), point[2]+z_offset)


def motion_bounds(start: XYZ, end: XYZ, placement: Placement, z_offset: float,
                  arc: Arc | None = None) -> tuple[XYZ, XYZ]:
    """Include endpoints and every transformed circle extremum lying on the actual sweep."""
    first,last=placed_point(start,placement,z_offset),placed_point(end,placement,z_offset)
    points=[first,last]
    if arc is not None:
        center=placement.apply_point(arc.center)
        angle=math.atan2(first[1]-center[1],first[0]-center[0])
        sweep=-arc.sweep if placement.mirror_x else arc.sweep
        for cardinal in (0., math.pi/2, math.pi, 3*math.pi/2):
            distance=((angle-cardinal) if sweep<0 else (cardinal-angle)) % _TAU
            if distance<=abs(sweep)+1e-12:
                points.append((center[0]+arc.radius*math.cos(cardinal),
                               center[1]+arc.radius*math.sin(cardinal),first[2]))
    return (tuple(min(p[i] for p in points) for i in range(3)),
            tuple(max(p[i] for p in points) for i in range(3)))


def motion_length(start: XYZ, end: XYZ, arc: Arc | None = None) -> float:
    if arc is not None:
        return math.hypot(arc.radius*abs(arc.sweep),end[2]-start[2])
    return math.dist(start,end)
