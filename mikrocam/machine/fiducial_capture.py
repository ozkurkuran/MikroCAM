"""Read fiducial machine coordinates from the single owner's snapshot; never sends commands."""
from mikrocam.core.placement import Point2D

from .models import ConnectionState, MachineSnapshot, MachineState


def _fresh(snapshot: object) -> MachineSnapshot:
    if type(snapshot) is not MachineSnapshot:
        raise ValueError('Capture requires a machine snapshot')
    if snapshot.connection is not ConnectionState.CONNECTED:
        raise ValueError('Capture requires a connected machine')
    if snapshot.state is not MachineState.IDLE:
        raise ValueError('Capture requires a fresh Idle report; wait until motion has stopped')
    if snapshot.stale or snapshot.report_units is None:
        raise ValueError('Capture requires a fresh status with verified report units')
    return snapshot


def capture_machine_xy(snapshot: MachineSnapshot) -> Point2D:
    """Machine (MPos) XY in mm from a connected, fresh, unit-verified Idle snapshot."""
    position = _fresh(snapshot).machine_position_mm
    if position is None:
        raise ValueError('Machine position is unavailable')
    return position[0], position[1]


def capture_work_offset_xy(snapshot: MachineSnapshot) -> Point2D:
    """Current reported work offset XY in mm; start-time G54 verification still applies."""
    offset = _fresh(snapshot).work_offset_mm
    if offset is None:
        raise ValueError('Work offset is unavailable')
    return offset[0], offset[1]
