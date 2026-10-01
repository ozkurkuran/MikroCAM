"""Complete measured bilinear fields in the immutable map's G54 work-mm frame."""
from bisect import bisect_right
from dataclasses import dataclass, field
import hashlib

from .probe_map import ProbeGrid, ProbeMap, _number
from .probe_codec import dumps_map


@dataclass(frozen=True)
class AutoLevelSettings:
    map: ProbeMap
    reference_z_mm: float
    max_segment_mm: float
    chord_error_mm: float
    surface_error_mm: float
    map_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        _complete(self.map)
        for name in ('reference_z_mm', 'max_segment_mm', 'chord_error_mm', 'surface_error_mm'):
            object.__setattr__(self, name, _number(getattr(self,name), name))
        if not .01 <= self.max_segment_mm <= 10:
            raise ValueError('Maximum XY segment requires .01..10mm')
        if any(not .0001 <= value <= .1 for value in (self.chord_error_mm,self.surface_error_mm)):
            raise ValueError('Chord/surface error requires .0001..0.1mm')
        digest=hashlib.sha256(dumps_map(self.map).encode('utf-8')).hexdigest()
        object.__setattr__(self,'map_sha256',digest)


def _complete(value: ProbeMap) -> None:
    if type(value) is not ProbeMap or not value.complete:
        raise ValueError('Auto-level requires a complete validated height map')


def surface_height(value: ProbeMap, x_mm: float, y_mm: float) -> float:
    """Bilinear height on the closed measured rectangle, without extrapolation."""
    _complete(value)
    x,y=_number(x_mm,'Surface X'),_number(y_mm,'Surface Y')
    axes=value.grid.x_mm,value.grid.y_mm
    if not axes[0][0] <= x <= axes[0][-1] or not axes[1][0] <= y <= axes[1][-1]:
        raise ValueError('Cutting path lies outside the measured height map')
    ix=min(bisect_right(axes[0],x)-1,len(axes[0])-2)
    iy=min(bisect_right(axes[1],y)-1,len(axes[1])-2)
    u=(x-axes[0][ix])/(axes[0][ix+1]-axes[0][ix])
    v=(y-axes[1][iy])/(axes[1][iy+1]-axes[1][iy])
    width=len(axes[0]); index=iy*width+ix
    h00,h10=value.heights_mm[index:index+2]
    h01,h11=value.heights_mm[index+width:index+width+2]
    return (1-v)*((1-u)*h00+u*h10)+v*((1-u)*h01+u*h11)


def cell_crossings(grid: ProbeGrid, first: tuple[float,float], last: tuple[float,float]) -> tuple[float,...]:
    """Ordered chord fractions at every interior grid crossing, including both endpoints."""
    if type(grid) is not ProbeGrid or len(first)!=2 or len(last)!=2:
        raise ValueError('Cell crossing requires grid and XY endpoints')
    fractions={0.,1.}
    for axis,values in enumerate((grid.x_mm,grid.y_mm)):
        start,end=_number(first[axis],'Chord start'),_number(last[axis],'Chord end')
        if start!=end:
            for boundary in values[1:-1]:
                fraction=(boundary-start)/(end-start)
                if 0 < fraction < 1:
                    fractions.add(fraction)
    return tuple(sorted(fractions))
