"""Typed probe intent and immutable acquisition observations."""
from dataclasses import dataclass
from enum import Enum
from mikrocam.core.probe_map import ProbePlan, ProbeMap


class ProbePhase(Enum):
    READY = 'ready'
    PREPARING = 'preparing'
    PROBING = 'probing'
    COMPLETE = 'complete'
    FAILED = 'failed'
    ABORTED = 'aborted'


@dataclass(frozen=True)
class StartProbeGridRequest:
    plan: ProbePlan

    def __post_init__(self) -> None:
        if type(self.plan) is not ProbePlan:
            raise ValueError('Probe start requires a validated immutable plan')


@dataclass(frozen=True)
class ProbeObservation:
    phase: ProbePhase = ProbePhase.READY
    completed: int = 0
    total: int = 0
    map: ProbeMap | None = None
    diagnostic: str = ''
    can_start: bool = False
    can_stop: bool = False
    stop_unverified: bool = False

    def __post_init__(self) -> None:
        if type(self.phase) is not ProbePhase:
            raise ValueError('Probe phase requires a known state')
        if (type(self.completed) is not int or type(self.total) is not int
                or not 0 <= self.completed <= self.total <= 1024):
            raise ValueError('Probe progress requires bounded integer counts')
        if self.map is not None and type(self.map) is not ProbeMap:
            raise ValueError('Probe observation requires a validated map')
        if self.map is not None and (self.map.completed != self.completed or self.map.grid.count != self.total):
            raise ValueError('Map and progress must agree')
        if type(self.diagnostic) is not str or len(self.diagnostic) > 256:
            raise ValueError('Probe diagnostic requires at most256 characters')
        if any(type(v) is not bool for v in (self.can_start, self.can_stop, self.stop_unverified)):
            raise ValueError('Probe flags require booleans')
