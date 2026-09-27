"""Immutable wire evidence and truthful machine snapshots, without I/O."""
from dataclasses import dataclass
from enum import Enum
from math import isfinite


XYZ = tuple[float, float, float]


class ConnectionState(Enum):
    DISCONNECTED = 'disconnected'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    ERROR = 'error'


class MachineState(Enum):
    UNKNOWN = 'unknown'
    IDLE = 'idle'
    JOG = 'jog'
    RUNNING = 'running'
    PAUSED = 'paused'
    ALARM = 'alarm'
    HOMING = 'homing'
    CHECK = 'check'
    SLEEP = 'sleep'
    DOOR = 'door'
    ERROR = 'error'


def _validate_xyz(value: XYZ | None) -> None:
    if value is None:
        return
    if (not isinstance(value, tuple) or len(value) != 3
            or any(type(axis) not in (int, float) for axis in value)):
        raise ValueError('Coordinates must be an immutable finite XYZ tuple')
    try:
        finite = all(isfinite(axis) for axis in value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError('Coordinates must be finite')


@dataclass(frozen=True)
class GrblStatus:
    """Directly reported wire-unit evidence; no conversion or derived position."""
    state: MachineState
    raw_state: str
    machine_position: XYZ | None
    work_position: XYZ | None
    work_offset: XYZ | None

    def __post_init__(self) -> None:
        if not isinstance(self.state, MachineState) or not isinstance(self.raw_state, str):
            raise ValueError('Status requires a machine state and its original text')
        for vector in (self.machine_position, self.work_position, self.work_offset):
            _validate_xyz(vector)
        if (self.machine_position is None) == (self.work_position is None):
            raise ValueError('Status requires exactly one directly reported position')


class ManualPhase(Enum):
    READY = 'ready'
    PREPARING = 'preparing'
    MOVING = 'moving'
    VERIFYING = 'verifying'
    CANCELLING = 'cancelling'
    COMPLETE = 'complete'
    FAILED = 'failed'
    ABORTED = 'aborted'


@dataclass(frozen=True)
class ManualObservation:
    """Owned operation eligibility and uncertainty, distinct from reported machine state."""
    phase: ManualPhase = ManualPhase.READY
    action: str | None = None
    diagnostic: str = ''
    can_jog: bool = False
    can_zero: bool = False
    can_select_g54: bool = False
    can_cancel: bool = False
    stop_unverified: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.phase, ManualPhase) or self.action not in (None, 'jog', 'zero', 'select_g54'):
            raise ValueError('Manual observation requires a known phase and action')
        if not isinstance(self.diagnostic, str) or len(self.diagnostic) > 256:
            raise ValueError('Manual diagnostic must be a string of at most 256 characters')
        if any(type(value) is not bool for value in (self.can_jog, self.can_zero, self.can_select_g54,
                                                    self.can_cancel, self.stop_unverified)):
            raise ValueError('Manual eligibility and uncertainty flags must be booleans')


@dataclass(frozen=True)
class MachineSnapshot:
    """A session observation; unavailable positions are None rather than zeroes."""
    connection: ConnectionState = ConnectionState.DISCONNECTED
    state: MachineState = MachineState.UNKNOWN
    raw_state: str = ''
    machine_position_mm: XYZ | None = None
    work_position_mm: XYZ | None = None
    work_offset_mm: XYZ | None = None
    report_units: str | None = None
    stale: bool = True
    last_report_at: float | None = None
    diagnostic: str = ''
    manual: ManualObservation = ManualObservation()

    def __post_init__(self) -> None:
        if not isinstance(self.manual, ManualObservation):
            raise ValueError('Snapshot requires an immutable manual observation')
        if not isinstance(self.connection, ConnectionState) or not isinstance(self.state, MachineState):
            raise ValueError('Snapshot requires explicit connection and machine states')
        if not isinstance(self.raw_state, str) or not isinstance(self.diagnostic, str):
            raise ValueError('Snapshot text must be strings')
        for vector in (self.machine_position_mm, self.work_position_mm, self.work_offset_mm):
            _validate_xyz(vector)
        if self.report_units not in (None, 'mm', 'inch') or type(self.stale) is not bool:
            raise ValueError('Snapshot requires known report units or None and a boolean stale flag')
        if self.last_report_at is not None:
            try:
                finite = type(self.last_report_at) in (int, float) and isfinite(self.last_report_at)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError('Report timestamp must be finite or None')
