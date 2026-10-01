"""Bounded immutable queue requests and offline ordered prepared-job snapshots."""
from dataclasses import dataclass
from enum import Enum
from .job_models import JobObservation, StreamingMode
from mikrocam.core.cnc_job import PreparedJob

MAX_QUEUE_ENTRIES = 32


@dataclass(frozen=True)
class QueueEntry:
    key: str
    job: PreparedJob

    def __post_init__(self):
        if type(self.key) is not str or not self.key or len(self.key) > 64:
            raise ValueError("Queue identity must be nonempty bounded text")
        if type(self.job) is not PreparedJob:
            raise ValueError("Queue requires an immutable prepared CNC snapshot")


@dataclass(frozen=True)
class StartQueueRequest:
    entries: tuple[QueueEntry, ...]
    mechanical_confirmed: bool
    streaming_mode: StreamingMode = StreamingMode.SEND_RESPONSE

    def __post_init__(self):
        if (type(self.entries) is not tuple or not 1 <= len(self.entries) <= MAX_QUEUE_ENTRIES
                or any(type(e) is not QueueEntry for e in self.entries)
                or len({e.key for e in self.entries}) != len(self.entries)
                or self.mechanical_confirmed is not True
                or type(self.streaming_mode) is not StreamingMode):
            raise ValueError("Queue Start requires unique bounded entries and whole-queue approval")


class QueuePhase(Enum):
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass(frozen=True)
class QueueResult:
    entry: QueueEntry
    job: JobObservation = JobObservation()

    def __post_init__(self):
        if type(self.entry) is not QueueEntry or type(self.job) is not JobObservation:
            raise ValueError("Queue result requires immutable identity and job evidence")


@dataclass(frozen=True)
class QueueObservation:
    phase: QueuePhase = QueuePhase.READY
    entries: tuple[QueueResult, ...] = ()
    active_key: str | None = None
    diagnostic: str = ""
    can_start: bool = False
    can_pause: bool = False
    can_resume: bool = False
    can_stop: bool = False

    def __post_init__(self):
        if (type(self.phase) is not QueuePhase or type(self.entries) is not tuple
                or len(self.entries) > MAX_QUEUE_ENTRIES
                or any(type(r) is not QueueResult for r in self.entries)
                or len({r.entry.key for r in self.entries}) != len(self.entries)):
            raise ValueError("Queue observation must contain bounded unique results")
        if self.active_key is not None and self.active_key not in {r.entry.key for r in self.entries}:
            raise ValueError("Active identity must belong to the queue")
        if type(self.diagnostic) is not str or len(self.diagnostic) > 256:
            raise ValueError("Queue diagnostic must be bounded text")
        if any(type(x) is not bool for x in (self.can_start, self.can_pause, self.can_resume, self.can_stop)):
            raise ValueError("Queue control flags must be boolean")


class QueueDraft:
    """Only offline snapshot bookkeeping; never holds a transport or a live source provider."""
    def __init__(self):
        self.entries: tuple[QueueEntry, ...] = ()
        self.locked = False
        self._sequence = 0

    def _editable(self):
        if self.locked:
            raise ValueError("An approved active queue cannot be edited")

    def add(self, job):
        self._editable()
        if len(self.entries) >= MAX_QUEUE_ENTRIES:
            raise ValueError("Queue is limited to 32 entries")
        entry = QueueEntry(f"q{self._sequence + 1}", job)
        self._sequence += 1
        self.entries += (entry,)
        return entry

    def move(self, key, index):
        self._editable()
        if type(index) is not int or not 0 <= index < len(self.entries):
            raise ValueError("Queue destination is out of range")
        entry = self._find(key)
        values = list(self.entries)
        values.remove(entry)
        values.insert(index, entry)
        self.entries = tuple(values)

    def _find(self, key):
        matches = [e for e in self.entries if e.key == key]
        if len(matches) != 1:
            raise ValueError("Unknown queue identity")
        return matches[0]

    def remove(self, key):
        self._editable()
        entry = self._find(key)
        self.entries = tuple(e for e in self.entries if e is not entry)

    def clear(self):
        self._editable()
        self.entries = ()

    def start_request(self, confirmed, streaming_mode=StreamingMode.SEND_RESPONSE):
        self._editable()
        request = StartQueueRequest(self.entries, confirmed, streaming_mode)
        self.locked = True
        return request

    def unlock(self):
        self.locked = False

    def settle(self, observation):
        """Retire only terminal entries; unsent waiting snapshots remain for explicit Start."""
        from .job_models import JobPhase
        if type(observation) is not QueueObservation or observation.can_stop:
            raise ValueError("Only terminal queue evidence can settle a draft")
        terminal = {r.entry.key for r in observation.entries
                    if r.job.phase in (JobPhase.COMPLETE, JobPhase.FAILED, JobPhase.ABORTED)}
        self.entries = tuple(e for e in self.entries if e.key not in terminal)
        self.unlock()
