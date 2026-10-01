"""Certify generated float32 controller chords against the explicit approximation budgets."""
import math
import struct

from .autolevel_surface import AutoLevelSettings, cell_crossings, surface_height
from .autolevel_paths import lerp
from .gcode_models import XYZ


def word(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError('Auto-level generated a nonfinite coordinate')
    text=format(value,'.5f').rstrip('0').rstrip('.') or '0'
    return '0' if text=='-0' else text


def float32(value: float) -> float:
    try:
        number=struct.unpack('f',struct.pack('f',value))[0]
    except OverflowError as error:
        raise ValueError('Auto-level controller representation overflow') from error
    if not math.isfinite(number):
        raise ValueError('Auto-level controller representation is nonfinite')
    return number


def represented_point(serialized: XYZ, offset: XYZ) -> XYZ:
    """Actual absolute-mm target under GRBL float32 coordinate/offset addition."""
    return tuple(float32(float32(value)+float32(shift))-shift for value,shift in zip(serialized,offset))


def certify_chord(first: XYZ, last: XYZ, nominal_first: XYZ, nominal_last: XYZ,
                  settings: AutoLevelSettings, *, vertical_entry: bool=False) -> None:
    if first==last and math.dist(nominal_first,nominal_last)>1e-9:
        raise ValueError('Auto-level controller representation collapses a required segment')
    if math.dist(first[:2],last[:2])>settings.max_segment_mm:
        raise ValueError('Auto-level controller XY segment exceeds declared length')
    if any(math.dist(actual[:2],ideal[:2])>settings.chord_error_mm/4
           for actual,ideal in ((first,nominal_first),(last,nominal_last))):
        raise ValueError('Auto-level controller XY precision exceeds chord budget')
    def error(t: float) -> float:
        actual=lerp(first,last,t)
        baseline=nominal_first[2]+(nominal_last[2]-nominal_first[2])*t
        return actual[2]-(baseline+surface_height(settings.map,*actual[:2])-settings.reference_z_mm)
    if vertical_entry:
        if abs(error(1))>settings.surface_error_mm/4:
            raise ValueError('Auto-level controller depth precision exceeds surface budget')
        return
    fractions=cell_crossings(settings.map.grid,first[:2],last[:2])
    for a,b in zip(fractions,fractions[1:]):
        e0,e1,em=error(a),error(b),error((a+b)/2)
        bound=max(abs(e0),abs(e1))+abs(em-(e0+e1)/2)
        if bound>settings.surface_error_mm:
            raise ValueError('Auto-level serialized/controller surface error exceeds declared tolerance')
