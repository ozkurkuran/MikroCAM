"""Concrete sequential CNC coordinator on the existing sole communication owner."""
from dataclasses import replace
import logging

_LOG = logging.getLogger(__name__)
from .job_models import JobObservation, JobPhase, StartJobRequest
from .queue_models import QueueObservation, QueuePhase, QueueResult, StartQueueRequest


class QueueControl:
    def __init__(self, host, previous=QueueObservation()):
        self.host = host
        self.request = None
        self.index = None
        self.boundary_hold = False
        self.observation = replace(previous, active_key=None, can_start=False,
                                   can_pause=False, can_resume=False, can_stop=False)

    @property
    def active(self):
        return self.request is not None

    def start(self, request):
        if type(request) is not StartQueueRequest or self.active or not self.host._job.eligible():
            raise ValueError("Queue requires fresh verified Idle and no competing/tainted owner")
        self.request = request
        self.index = None
        self.boundary_hold = False
        self.observation = QueueObservation(phase=QueuePhase.RUNNING,
            entries=tuple(QueueResult(e) for e in request.entries),
            diagnostic="Whole queue approved; each job is reverified before automatic advance")
        _LOG.info("Queue start approved: %d prepared snapshots", len(request.entries))
        self.publish()

    def _capture(self):
        if self.index is None:
            return
        values = list(self.observation.entries)
        values[self.index] = replace(values[self.index], job=self.host._job.observation)
        self.observation = replace(self.observation, entries=tuple(values))

    def reject(self, request, diagnostic, *, cancelled=False):
        if self.active or type(request) is not StartQueueRequest:
            raise ValueError("Cannot replace an active queue with rejected evidence")
        results = tuple(QueueResult(e) for e in request.entries)
        if not cancelled:
            first = request.entries[0].job
            results = (replace(results[0], job=JobObservation(phase=JobPhase.FAILED,
                source_name=first.source.name, source_sha256=first.source.sha256,
                total=len(first.blocks), diagnostic=diagnostic[:256])),) + results[1:]
        self.observation = QueueObservation(phase=QueuePhase.ABORTED if cancelled else QueuePhase.FAILED,
                                           entries=results, diagnostic=diagnostic[:256])
        self.publish()

    def tick(self):
        if not self.active:
            self.publish()
            return
        self._capture()
        job = self.host._job.observation
        if self.index is not None and job.phase in (JobPhase.FAILED, JobPhase.ABORTED):
            self._finish(QueuePhase.FAILED if job.phase is JobPhase.FAILED else QueuePhase.ABORTED,
                         job.diagnostic)
            return
        if self.host._interrupted() or self.host._pause_requested() or self.boundary_hold:
            self.publish()
            return
        if self.index is not None and self.host._job.active:
            self.publish()
            return
        if self.index is not None and job.phase is not JobPhase.COMPLETE:
            self._finish(QueuePhase.FAILED, "Queue lost verified active-job evidence")
            return
        next_index = 0 if self.index is None else self.index + 1
        if next_index == len(self.request.entries):
            self._finish(QueuePhase.COMPLETE, "Every queued job has verified final Idle and outputs off")
            return
        self.index = next_index
        entry = self.request.entries[self.index]
        self.observation = replace(self.observation, active_key=entry.key)
        try:
            self.host._job.start(StartJobRequest(entry.job, True, self.request.streaming_mode))
        except ValueError as error:
            self.host._job.observation = JobObservation(phase=JobPhase.FAILED,
                source_name=entry.job.source.name, source_sha256=entry.job.source.sha256,
                total=len(entry.job.blocks), diagnostic=str(error)[:256])
            self._capture()
            self._finish(QueuePhase.FAILED, str(error))
            return
        _LOG.info("Queue job %s: %s %s", entry.key, entry.job.source.name, entry.job.source.sha256)
        self._capture()
        self.publish()

    def _finish(self, phase, diagnostic):
        self.request = None
        self.boundary_hold = False
        self.observation = replace(self.observation, phase=phase, active_key=None,
                                   diagnostic=diagnostic[:256])
        _LOG.info("Queue end %s: %s", phase.value, diagnostic[:256])
        self.host._job.publish()
        self.host._manual.publish()
        self.host._console.publish()
        self.host._probe.publish()
        self.publish()

    def stop(self, diagnostic="Queue stopped; no remaining job will start"):
        if not self.active:
            return
        self.request = None  # revoke authorization before the priority stop's transport handoff
        self.boundary_hold = False
        if self.host._job.active:
            self.host._job.stop(diagnostic)
            self._capture()
        self._finish(QueuePhase.ABORTED, diagnostic)

    def fail(self, diagnostic):
        if self.active:
            self._capture()
            self._finish(QueuePhase.FAILED, diagnostic)

    def pause(self):
        if not self.active:
            raise ValueError("No active queue")
        if self.host._job.active:
            self.host._job.pause()
        else:
            self.boundary_hold = True
        self.publish()

    def resume(self):
        if not self.active:
            raise ValueError("No active queue")
        if self.boundary_hold:
            if not self.host._job.eligible():
                raise ValueError("Fresh verified Idle is required to resume the queue boundary")
            self.boundary_hold = False
        else:
            self.host._job.resume()
        self.publish()

    def publish(self):
        state = self.host.snapshot()
        paused = self.boundary_hold or (self.active and state.job.phase in (JobPhase.PAUSING, JobPhase.PAUSED))
        if self.active:
            phase = QueuePhase.PAUSED if paused else QueuePhase.RUNNING
            self.observation = replace(self.observation, phase=phase,
                can_start=False, can_stop=True,
                can_pause=state.job.can_pause or (not self.host._job.active and not paused),
                can_resume=state.job.can_resume or (self.boundary_hold and self.host._job.eligible()))
            self.host._snapshot = replace(state,
                manual=replace(state.manual, can_jog=False, can_zero=False, can_select_g54=False),
                job=replace(state.job, can_start=False, can_pause=self.observation.can_pause,
                            can_resume=self.observation.can_resume, can_stop=True),
                console=replace(state.console, can_query=False),
                probe=replace(state.probe, can_start=False))
        else:
            self.observation = replace(self.observation, can_start=self.host._job.eligible(),
                                       can_pause=False, can_resume=False, can_stop=False)
        self.host._snapshot = replace(self.host._snapshot, queue=self.observation)
