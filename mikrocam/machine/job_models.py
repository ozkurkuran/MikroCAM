"""Immutable streaming requests and observable progress, without transport dependencies."""
from dataclasses import dataclass
from enum import Enum
import re

from mikrocam.core.cnc_job import PreparedJob
from mikrocam.core.gcode_models import MAX_LINES


class StreamingMode(Enum):
    SEND_RESPONSE = "send-response"
    CHARACTER_COUNTING = "character-counting"


class JobPhase(Enum):
    READY = 'ready'
    PREPARING = 'preparing'
    RUNNING = 'running'
    PAUSING = 'pausing'
    PAUSED = 'paused'
    COMPLETING = 'completing'
    COMPLETE = 'complete'
    ABORTED = 'aborted'
    FAILED = 'failed'


@dataclass(frozen=True)
class JobObservation:
    phase: JobPhase = JobPhase.READY
    source_name: str = ''
    source_sha256: str = ''
    acknowledged: int = 0
    total: int = 0
    source_line: int | None = None
    diagnostic: str = ''
    can_start: bool = False
    can_pause: bool = False
    can_resume: bool = False
    can_stop: bool = False
    stop_unverified: bool = False

    def __post_init__(self) -> None:
        if type(self.phase) is not JobPhase:
            raise ValueError('Job phase must be JobPhase')
        for name in ('source_name', 'diagnostic'):
            value = getattr(self, name)
            if type(value) is not str or len(value) > 256:
                raise ValueError(f'{name} must be bounded text')
        if (type(self.source_sha256) is not str or (self.source_sha256
                and re.fullmatch('[0-9a-f]{64}', self.source_sha256) is None)):
            raise ValueError('Source digest must be empty or lowercase SHA256')
        for name in ('acknowledged', 'total'):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= MAX_LINES:
                raise ValueError(f'{name} must be a bounded integer')
        if self.acknowledged > self.total:
            raise ValueError('Acknowledged blocks exceed total')
        if self.source_line is not None and (type(self.source_line) is not int
                                            or not 1 <= self.source_line <= MAX_LINES):
            raise ValueError('Source line must be a bounded positive integer')
        for name in ('can_start', 'can_pause', 'can_resume', 'can_stop', 'stop_unverified'):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f'{name} must be boolean')


@dataclass(frozen=True)
class StartJobRequest:
    job: PreparedJob
    mechanical_confirmed: bool
    streaming_mode: StreamingMode = StreamingMode.SEND_RESPONSE

    def __post_init__(self) -> None:
        if type(self.streaming_mode) is not StreamingMode:
            raise ValueError('Streaming mode must be exact StreamingMode')
        if type(self.job) is not PreparedJob or self.mechanical_confirmed is not True:
            raise ValueError('Start requires an exact prepared job and explicit mechanical confirmation')
