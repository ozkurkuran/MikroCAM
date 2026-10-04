"""Immutable requests for the exact supported read-only controller query set."""
from dataclasses import dataclass
from enum import Enum


CONSOLE_COMMANDS = ('?', '$$', '$G', '$#', '$N', '$I')
FLUIDNC_CONSOLE_COMMANDS = ('$CD',)  # FluidNC Config/Dump YAML, readonly (spec 044)


def _command(value: str) -> None:
    if type(value) is not str or value not in CONSOLE_COMMANDS + FLUIDNC_CONSOLE_COMMANDS:
        raise ValueError('Console command must be one of ?, $$, $G, $#, $N, $I, $CD')


@dataclass(frozen=True)
class ConsoleRequest:
    command: str

    def __post_init__(self) -> None:
        _command(self.command)


class ConsolePhase(Enum):
    READY = 'ready'
    PENDING = 'pending'
    COMPLETE = 'complete'
    FAILED = 'failed'


@dataclass(frozen=True)
class ConsoleObservation:
    phase: ConsolePhase = ConsolePhase.READY
    command: str | None = None
    diagnostic: str = ''
    can_query: bool = False

    def __post_init__(self) -> None:
        if type(self.phase) is not ConsolePhase:
            raise ValueError('Console phase must be ConsolePhase')
        if self.command is not None:
            _command(self.command)
        if type(self.diagnostic) is not str or len(self.diagnostic) > 256:
            raise ValueError('Console diagnostic must be text of at most256 characters')
        if type(self.can_query) is not bool:
            raise ValueError('Console eligibility must be boolean')
