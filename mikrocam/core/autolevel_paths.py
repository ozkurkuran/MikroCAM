"""Bounded exact-endpoint arc chords and within-cell bilinear surface refinement."""
from collections.abc import Callable, Iterator
import math

from .autolevel_surface import AutoLevelSettings, cell_crossings, surface_height
from .gcode_models import MAX_LINES, PreflightCancelled, PreflightSetup, XYZ
from .gcode_motion import motion_bounds, placed_point
from .gcode_parser import Event


def check_cancel(cancelled: Callable[[],bool] | None) -> None:
    if cancelled is not None and cancelled():
        raise PreflightCancelled('Auto-level preparation cancelled')


def work_point(point: XYZ, setup: PreflightSetup, settings: AutoLevelSettings) -> XYZ:
    machine=placed_point(point,setup.placement,setup.z_offset_mm)
    return tuple(a-b for a,b in zip(machine,settings.map.g54_offset_mm))


def lerp(first: XYZ, last: XYZ, t: float) -> XYZ:
    return tuple(a+(b-a)*t for a,b in zip(first,last))


def _line(first: XYZ, last: XYZ, settings: AutoLevelSettings,
          cancelled: Callable[[],bool] | None) -> Iterator[tuple[XYZ,XYZ]]:
    distance=math.dist(first[:2],last[:2])
    count=max(1,math.ceil(2*distance/settings.max_segment_mm))
    if count>MAX_LINES:
        raise ValueError('Auto-level subdivision exceeds work limit')
    fractions=set(cell_crossings(settings.map.grid,first[:2],last[:2]))
    fractions.update(i/count for i in range(1,count))
    ordered=sorted(fractions)
    for a,b in zip(ordered,ordered[1:]):
        stack=[(lerp(first,last,a),lerp(first,last,b),0)]
        while stack:
            check_cancel(cancelled)
            start,end,depth=stack.pop()
            middle=lerp(start,end,.5)
            h0=surface_height(settings.map,*start[:2])
            h1=surface_height(settings.map,*end[:2])
            hm=surface_height(settings.map,*middle[:2])
            if abs(hm-(h0+h1)/2)>settings.surface_error_mm/2:
                if depth>=30 or middle in (start,end):
                    raise ValueError('Auto-level surface subdivision exceeds precision limit')
                stack.append((middle,end,depth+1)); stack.append((start,middle,depth+1))
            else:
                yield start,end


def _arc_chords(event: Event, setup: PreflightSetup, settings: AutoLevelSettings,
                cancelled: Callable[[],bool] | None) -> Iterator[tuple[XYZ,XYZ]]:
    arc=event.arc
    r0=math.dist(event.start[:2],arc.center); r1=math.dist(event.end[:2],arc.center)
    if abs(r0-r1)>1e-8:
        raise ValueError('Auto-level requires equal arc endpoint radii; resolve rounded arc geometry')
    angle=min(math.pi,4*math.asin(math.sqrt(min(1.,settings.chord_error_mm/(4*r0)))))
    count=max(1,math.ceil(abs(arc.sweep)/angle),
              math.ceil(2*r0*abs(arc.sweep)/settings.max_segment_mm))
    if count>MAX_LINES:
        raise ValueError('Auto-level arc subdivision exceeds work limit')
    first=work_point(event.start,setup,settings)
    for index in range(1,count+1):
        check_cancel(cancelled)
        fraction=index/count
        theta=arc.start_angle+arc.sweep*fraction
        point=(arc.center[0]+r0*math.cos(theta),arc.center[1]+r0*math.sin(theta),
               event.start[2]+(event.end[2]-event.start[2])*fraction)
        last=work_point(event.end if index==count else point,setup,settings)
        yield first,last
        first=last


def feed_segments(event: Event, setup: PreflightSetup, settings: AutoLevelSettings,
                  cancelled: Callable[[],bool] | None) -> Iterator[tuple[XYZ,XYZ]]:
    """Check full analytic coverage before generating any chord; errors never extrapolate."""
    bounds=motion_bounds(event.start,event.end,setup.placement,setup.z_offset_mm,event.arc)
    for axis,values in enumerate((settings.map.grid.x_mm,settings.map.grid.y_mm)):
        offset=settings.map.g54_offset_mm[axis]
        if bounds[0][axis]-offset<values[0] or bounds[1][axis]-offset>values[-1]:
            raise ValueError('Complete cutting path lies outside the measured height map')
    if event.arc is None:
        chords=((work_point(event.start,setup,settings),work_point(event.end,setup,settings)),)
    else:
        chords=_arc_chords(event,setup,settings,cancelled)
    for first,last in chords:
        yield from _line(first,last,settings,cancelled)
