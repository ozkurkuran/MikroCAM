"""Conservative streaming representation check, not a GRBL firmware emulator."""
from math import isfinite
import struct

from .gcode_lexer import Block
from .gcode_models import PreflightSetup, XYZ
from .gcode_motion import make_arc, motion_bounds, placed_point
from .gcode_parser import Event
from .placement import Placement


def _float32(value: float) -> float:
    try:
        result = struct.unpack('f', struct.pack('f', value))[0]
    except OverflowError as error:
        raise ValueError('Controller precision overflow') from error
    if not isfinite(result) or (value != 0 and result == 0):
        raise ValueError('Controller precision loses finite nonzero value')
    return result


class ControllerPrecision:
    """Track float32 target accumulation and check its complete analytic motion extents.

    The reviewed double-precision source is never rewritten. Firmware arc interpolation,
    step rounding and physical positioning remain outside this representation guard.
    """

    def __init__(self, setup: PreflightSetup) -> None:
        self.setup = setup
        self.offset = tuple(_float32(value) for value in (*setup.placement.matrix[4:], setup.z_offset_mm))
        initial = placed_point(setup.initial_position_mm, setup.placement, setup.z_offset_mm)
        self.position = tuple(_float32(value) for value in initial)
        self.factor = 1.
        self.absolute = True
        self._verify(self.position, initial)

    def _verify(self, actual: XYZ, expected: XYZ) -> None:
        if any(abs(a - b) > .001 for a, b in zip(actual, expected)):
            raise ValueError('Controller precision drift exceeds .001mm')
        self._envelope((actual, actual))

    def _envelope(self, bounds: tuple[XYZ, XYZ]) -> None:
        if any(bounds[0][i] < self.setup.machine_min_mm[i] or bounds[1][i] > self.setup.machine_max_mm[i]
               for i in range(3)):
            raise ValueError('Controller precision may leave the declared envelope')

    def consume(self, block: Block, event: Event) -> None:
        """Check one already validated modal event, retaining incremental arithmetic drift."""
        words = dict(block.words)
        modes = {value for letter, value in block.words if letter == 'G'}
        if 20 in modes or 21 in modes:
            self.factor = _float32(25.4 if 20 in modes else 1.)
        if 90 in modes or 91 in modes:
            self.absolute = 90 in modes
        if event.motion is None:
            return
        target = list(self.position)
        for axis, letter in enumerate('XYZ'):
            if letter in words:
                value = _float32(_float32(words[letter]) * self.factor)
                target[axis] = _float32(value + (self.offset[axis] if self.absolute else self.position[axis]))
        end = tuple(target)
        expected = placed_point(event.end, self.setup.placement, self.setup.z_offset_mm)
        self._verify(end, expected)
        arc = self._arc(words, end, event)
        self._envelope(motion_bounds(self.position, end, placement=Placement(), z_offset=0., arc=arc))
        if event.motion == 0:
            horizontal = end[:2] != self.position[:2]
            if ((horizontal and min(end[2], self.position[2]) < self.setup.safe_z_mm)
                    or (end[2] < self.position[2] and end[2] < self.setup.safe_z_mm)):
                raise ValueError('Controller precision may violate rapid Safe-Z')
        self.position = end

    def _arc(self, words: dict, end: XYZ, event: Event):
        if event.arc is None:
            return None
        radius = _float32(_float32(words['R']) * self.factor) if 'R' in words else None
        ij = None if radius is not None else tuple(
            _float32(_float32(words.get(letter, 0.)) * self.factor) for letter in 'IJ')
        try:
            return make_arc(self.position, end, event.motion == 2, ij=ij, radius=radius, line=event.line)
        except ValueError as error:
            raise ValueError(f'Controller precision makes arc ambiguous: {error}') from error
