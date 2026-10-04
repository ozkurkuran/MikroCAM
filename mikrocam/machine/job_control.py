"""Concrete single-job coordinator; the host remains the sole communication owner."""
from dataclasses import replace
from typing import TYPE_CHECKING

from .job_models import JobObservation, JobPhase, StartJobRequest, StreamingMode
from .job_preparation import near, query_record, verify_modal, verify_parameters, verify_settings
from .job_stream import JobStream, verified_capacity
from .models import ConnectionState, MachineState
from . import fluidnc
from .startup_evidence import StartupEvidence

if TYPE_CHECKING:
    from .controller import MachineController


class _PriorityPending(Exception):
    """The next owner cycle processes an already queued priority intent."""


class JobControl:
    def __init__(self, host: 'MachineController') -> None:
        self.host = host
        self.request: StartJobRequest | None = None
        self.observation = JobObservation()
        self.tainted = self.startup_verified = self.sent_source = False
        self.transaction: str | None = None
        self.records: dict = {}
        self.completed: tuple | None = None
        self.waiting_status: str | None = None
        self.minimum_query = 0
        self.deadline = 0.
        self.resume_phase = JobPhase.RUNNING
        self.pause_started = self.pause_deadline = 0.
        self.pause_query = 0
        self.resume_query = 0
        self.stream = None
        self.startup: StartupEvidence | None = None

    @property
    def active(self) -> bool:
        return self.request is not None

    def eligible(self) -> bool:
        return not self.tainted and not self.active and self.host._manual.eligible()

    def publish(self) -> None:
        state = self.host.snapshot()
        phase = self.observation.phase
        fresh = self._fresh()
        self.observation = replace(
            self.observation, can_start=self.eligible(),
            can_pause=self.active and phase in (JobPhase.RUNNING, JobPhase.COMPLETING),
            can_resume=self.active and phase is JobPhase.PAUSED and fresh
            and state.raw_state in ('Hold:0', 'Idle'), can_stop=self.active)
        self.host._snapshot = replace(self.host._snapshot, job=self.observation)

    def start(self, request: StartJobRequest) -> None:
        if type(request) is not StartJobRequest or not self.eligible():
            raise ValueError('Job Start requires fresh verified Idle and no competing/tainted operation')
        self.request = request
        self.stream = None
        job = request.job
        self.observation = JobObservation(phase=JobPhase.PREPARING, source_name=job.source.name,
                                         source_sha256=job.source.sha256, total=len(job.blocks),
                                         diagnostic='Verifying live mechanical CNC setup')
        self.startup_verified = self.sent_source = False
        self.completed = ('begin', {})
        self.publish()
        self.host._manual.publish()

    def _fresh(self) -> bool:
        state = self.host.snapshot()
        return (state.connection is ConnectionState.CONNECTED and not state.stale
                and state.report_units is not None and state.machine_position_mm is not None
                and state.last_report_at is not None
                and 0 <= self.host._clock() - state.last_report_at < 2)

    def _guard(self) -> None:
        if self.host._interrupted() or self.host._pause_requested():
            raise _PriorityPending()
        if not self._fresh():
            raise ValueError('Job requires fresh verified controller coordinates')
        permitted = (MachineState.IDLE,) if not self.sent_source else (MachineState.IDLE, MachineState.RUNNING)
        if self.host.snapshot().state not in permitted:
            raise ValueError('Controller state no longer permits job transmission')
        if self.sent_source and not near(self.host.snapshot().work_offset_mm, self.request.job.g54_offset_mm):
            raise ValueError('Work offset changed during the reviewed job')

    def _command(self, purpose: str, data: bytes, *, source: bool = False, long: bool = False) -> None:
        self._guard()
        if self.transaction is not None:
            raise ValueError('Another ordinary command still owns its acknowledgement')
        self.transaction, self.records = purpose, {}
        timeout = self.request.job.ack_timeout_seconds if source or long else 3
        self.deadline = self.host._clock() + timeout
        if source:
            previous = self.sent_source
            if not previous and (not near(self.host.snapshot().machine_position_mm, self.request.job.initial_machine_mm)
                                 or not near(self.host.snapshot().work_offset_mm, self.request.job.g54_offset_mm)):
                raise ValueError('Initial position/G54 changed before the first source write')
            self.sent_source = True
            try:
                self.host._send_job(data)
            except _PriorityPending:
                self.sent_source = previous
                self.transaction = None
                raise
        else:
            self.host._send(data)

    def consume(self, line: str) -> bool:
        if not self.active:
            return self.tainted and (line == 'ok' or line.startswith(('error:', '$', '[GC:', '[G5', '[G92:', '[TLO:')))
        if self.stream is not None and self.transaction is None and self.stream.pending:
            return self._consume_source(line)
        if (self.transaction is not None
                and self.observation.phase not in (JobPhase.PAUSING, JobPhase.PAUSED)
                and self.host._clock() >= self.deadline):
            self.fail('Job transaction response timed out before evidence arrived')
            return True
        if line == 'ok' or line.startswith('error:'):
            if self.transaction is None:
                self.fail('Unexpected or duplicate job acknowledgement')
            elif line != 'ok':
                self.fail(f'{self.transaction} rejected: {line}')
            else:
                purpose, records = self.transaction, self.records
                self.transaction, self.records = None, {}
                self.completed = (purpose, records)
                if purpose == 'source':
                    count = self.observation.acknowledged + 1
                    self.observation = replace(self.observation, acknowledged=count,
                                               source_line=self.request.job.blocks[count - 1].source_line)
            return True
        try:
            if self.transaction == 'startup':
                record = self.startup.record(line)
            elif self.transaction == 'firmware' and line.startswith(('[VER:', '[OPT:')):
                if not line.endswith(']') or len(line) > 256:
                    raise ValueError('Malformed GRBL capacity evidence')
                record = (line[1:4].lower(), line[5:-1])
            else:
                record = query_record(self.transaction, line, self.host.snapshot().report_units)
            if record is not None:
                key, value = record
                if key in self.records:
                    raise ValueError('Duplicate job query evidence')
                self.records[key] = value
                return True
            if line.startswith(('$', '[GC', '[G5', '[G92', '[TLO')):
                raise ValueError('Unsolicited or malformed job query evidence')
        except ValueError as error:
            self.fail(str(error))
            return True
        return False

    def tick(self) -> None:
        if not self.active:
            self.publish()
            return
        try:
            if self.host._interrupted() or self.host._pause_requested():
                return
            if self.observation.phase in (JobPhase.PAUSING, JobPhase.PAUSED):
                self._pause_progress()
                return
            if self.resume_query:
                if self.host._last_report_query < self.resume_query:
                    return
                self._guard()
                self.resume_query = 0
            if (self.transaction or self.waiting_status) and self.host._clock() >= self.deadline:
                raise ValueError(f'{self.transaction or self.waiting_status} job response timed out')
            if self.completed is not None:
                current = self.completed
                self.completed = None
                try:
                    self._advance(*current)
                except _PriorityPending:
                    self.completed = current
            if (self.stream is not None and self.observation.phase is JobPhase.RUNNING
                    and not self.transaction and not self.waiting_status and not self.resume_query):
                self._feed_window()
            if self.waiting_status:
                self._status_progress()
        except _PriorityPending:
            pass
        except ValueError as error:
            self.fail(str(error))
        finally:
            self.publish()

    def _advance(self, purpose: str, records: dict) -> None:
        job = self.request.job
        if purpose == 'begin':
            if self.request.streaming_mode is StreamingMode.CHARACTER_COUNTING:
                if self.host.snapshot().firmware.capabilities.streaming_rx_budget is None:
                    raise ValueError('Character counting requires a proven firmware RX budget')
                self._command('firmware', b'$I\n')
            else:
                self._begin_startup()
        elif purpose == 'firmware':
            self.stream = JobStream(self._streaming_capacity(records))
            if any(len(block.wire) > self.stream.capacity for block in job.blocks):
                raise ValueError('Reviewed source block exceeds verified GRBL RX capacity')
            self._begin_startup()
        elif purpose == 'startup':
            self._guard()  # A racing priority intent retries this step before evidence is consumed.
            self.startup.add(records)
            following = self.startup.next_query()
            if following is not None:  # FluidNC: macros/startup_line0/1, after_reset, $RI (044).
                self._command('startup', following)
                return
            problem = self.startup.problem('Both startup blocks must be empty before job execution')
            if problem:
                raise ValueError(problem)
            self.startup_verified = True
            self._command('settings', b'$$\n')
        elif purpose == 'settings':
            check = fluidnc.verify_settings if self.startup.fluidnc else verify_settings
            check(records, job, self.host.snapshot().report_units)
            self._command('off', b'M5 M9\n')
        elif purpose == 'off':
            self._command('modal', b'$G\n')
        elif purpose == 'modal':
            verify_modal(records)
            self._command('parameters', b'$#\n')
        elif purpose == 'parameters':
            verify_parameters(records, job)
            self._await_status('initial', 3)
        elif purpose in ('source', 'feed'):
            self._feed()
        elif purpose == 'final_off':
            self._command('final_modal', b'$G\n')
        elif purpose == 'final_modal':
            verify_modal(records)
            self._await_status('final', job.ack_timeout_seconds)

    def _begin_startup(self) -> None:
        self.startup = StartupEvidence(self.host.snapshot().firmware.capabilities.family)
        self._command('startup', self.startup.next_query())

    def _streaming_capacity(self, records: dict) -> int:
        """C3 evidence must still verify and match the identified session VER and OPT (042/043)."""
        capacity = verified_capacity(records)
        firmware = self.host.snapshot().firmware
        budget = firmware.capabilities.streaming_rx_budget
        if budget is None or any(f"[{tag.upper()}:{records.get(tag, '')}]" not in firmware.evidence
                                 for tag in ('ver', 'opt')):
            raise ValueError('Firmware build evidence changed since identification')
        return min(capacity, budget)

    def _feed(self) -> None:
        if self.stream is not None:
            self._feed_window()
            return
        job = self.request.job
        index = self.observation.acknowledged
        if index == len(job.blocks):
            self.observation = replace(self.observation, phase=JobPhase.COMPLETING,
                                       diagnostic='All blocks accepted; verifying output-off and final Idle')
            self._command('final_off', b'M5 M9\n', long=True)
        else:
            self._command('source', job.blocks[index].wire, source=True)

    def _await_status(self, purpose: str, timeout: float) -> None:
        self.waiting_status = purpose
        self.minimum_query = self.host._query_sequence + 1
        self.deadline = self.host._clock() + timeout

    def _status_progress(self) -> None:
        if self.host._last_report_query < self.minimum_query:
            return
        value, job = self.host.snapshot(), self.request.job
        if self.waiting_status == 'final' and value.state is MachineState.RUNNING:
            return
        self._guard()
        target = job.initial_machine_mm if self.waiting_status == 'initial' else job.final_machine_mm
        if (value.state is not MachineState.IDLE or not near(value.machine_position_mm, target)
                or not near(value.work_offset_mm, job.g54_offset_mm)):
            raise ValueError('Fresh Idle position/G54 does not match the reviewed job')
        if self.waiting_status == 'initial':
            self.observation = replace(self.observation, phase=JobPhase.RUNNING,
                                       diagnostic='Streaming reviewed source; counts mean accepted blocks')
            self.completed = ('feed', {})
        else:
            self._end(JobPhase.COMPLETE, 'Final Idle endpoint and controller-reported outputs off verified', False)
        self.waiting_status = None

    def pause(self) -> None:
        if not self.active or self.observation.phase not in (JobPhase.RUNNING, JobPhase.COMPLETING):
            raise ValueError('Only the active running job can be paused')
        self.resume_phase = self.observation.phase
        self.pause_started = self.host._clock()
        self.pause_deadline = self.pause_started + 3
        self.pause_query = self.host._query_sequence + 1
        self.observation = replace(self.observation, phase=JobPhase.PAUSING,
                                   diagnostic='Feed hold requested; spindle/coolant may remain on')
        if not self._realtime(b'!'):
            return
        self.publish()

    def _pause_progress(self) -> None:
        if self.observation.phase is JobPhase.PAUSED:
            return
        if self.host._clock() >= self.pause_deadline:
            raise ValueError('Stopped hold could not be verified before deadline')
        if self.host._last_report_query >= self.pause_query and self._fresh():
            if self.host.snapshot().raw_state in ('Hold:0', 'Idle'):
                self.observation = replace(self.observation, phase=JobPhase.PAUSED,
                                           diagnostic='Stopped hold verified; outputs may remain on')

    def resume(self) -> None:
        self.publish()
        if not self.observation.can_resume or self.host._interrupted():
            raise ValueError('Resume requires the same paused job and fresh stopped Hold:0/Idle')
        if self.host.snapshot().raw_state == 'Hold:0':
            if not self._realtime(b'~'):
                return
        held = self.host._clock() - self.pause_started
        self.deadline += held
        if self.stream is not None:
            self.stream.extend(held)
        self.resume_query = self.host._query_sequence + 1
        self.observation = replace(self.observation, phase=self.resume_phase,
                                   diagnostic='Explicit resume; awaiting fresh controller state')
        self.publish()

    def _realtime(self, data: bytes) -> bool:
        try:
            self.host._send_job(data)
            return True
        except Exception as error:
            self.host._fail(error)
            return False

    def on_status(self) -> None:
        if not self.active:
            return
        value = self.host.snapshot()
        if self.sent_source and not near(value.work_offset_mm, self.request.job.g54_offset_mm):
            self.fail('Work offset changed during the reviewed job')
            return
        if self.observation.phase is JobPhase.PAUSED and value.raw_state not in ('Hold:0', 'Idle'):
            self.fail('Controller left stopped hold without explicit job resume')
            return
        allowed = (MachineState.IDLE, MachineState.RUNNING)
        if self.observation.phase in (JobPhase.PAUSING, JobPhase.PAUSED) or self.resume_query:
            allowed += (MachineState.PAUSED,)
        if self.host.snapshot().state not in allowed:
            self.fail('Job interrupted by ' + self.host.snapshot().raw_state)

    def stop(self, message: str = 'Job stopped; physical stop unverified', *, failed: bool = False) -> None:
        if not self.active:
            return
        command = b'\x18' if self.startup_verified else b'\x84'
        if not self.startup_verified:
            message += '; safety-door stop may perform configured parking'
        self._end(JobPhase.FAILED if failed else JobPhase.ABORTED, message, True)
        self.startup_verified = False
        self.host._invalidate(clear_units=True)
        self.host._settings_sent_at = None
        try:
            self.host._send(command)
        except Exception as error:
            self.observation = replace(self.observation, diagnostic=(message + f'; stop delivery failed: {error}')[:256])
        self.publish()

    def fail(self, message: str, *, reset: bool = False) -> None:
        if not self.active:
            return
        if self.stream is not None and self.stream.pending:
            block = self.request.job.blocks[self.stream.pending[0].index]
            self.observation = replace(self.observation, source_line=block.source_line)
            message = f'Source line {block.source_line}: {message}; buffered motion may have executed'
        if reset:
            self.startup_verified = False
            self._end(JobPhase.FAILED, message + '; physical stop unverified', self.sent_source)
        elif self.sent_source:
            self.stop(message + '; physical stop unverified', failed=True)
        else:
            self._end(JobPhase.FAILED, message, False)
        self.host._invalidate(clear_units=True)
        self.publish()

    def _end(self, phase: JobPhase, message: str, uncertain: bool) -> None:
        self.observation = replace(self.observation, phase=phase, diagnostic=message[:256],
                                   stop_unverified=uncertain)
        self.tainted = phase is not JobPhase.COMPLETE
        self.request = self.transaction = self.completed = self.waiting_status = None
        self.records = {}
        self.stream = None
        self.resume_query = 0
        self.publish()

    def _consume_source(self, line: str) -> bool:
        held = self.observation.phase in (JobPhase.PAUSING, JobPhase.PAUSED)
        if not held and self.stream.expired(self.host._clock()):
            self.fail('Source FIFO acknowledgement timed out before evidence arrived')
            return True
        if line == 'ok' or line.startswith('error:'):
            head = self.stream.pending[0]
            block = self.request.job.blocks[head.index]
            if line != 'ok':
                self.fail(f'Source rejected: {line}')
            else:
                self.stream.ack()
                self.observation = replace(self.observation,
                    acknowledged=self.observation.acknowledged + 1, source_line=block.source_line)
            return True
        if line.startswith(('$', '[GC', '[G5', '[G92', '[TLO', '[VER:', '[OPT:')):
            self.fail('Unsolicited evidence during buffered source')
            return True
        return False

    def _feed_window(self) -> None:
        stream, job = self.stream, self.request.job
        if stream.expired(self.host._clock()):
            raise ValueError('Source FIFO acknowledgement timed out')
        while stream.next_index < len(job.blocks):
            data = job.blocks[stream.next_index].wire
            if not stream.fits(data):
                return
            self._guard()
            previous = self.sent_source
            if not previous and (not near(self.host.snapshot().machine_position_mm, job.initial_machine_mm)
                                 or not near(self.host.snapshot().work_offset_mm, job.g54_offset_mm)):
                raise ValueError('Initial position/G54 changed before buffered source')
            entry = stream.reserve(data, self.host._clock() + job.ack_timeout_seconds)
            self.sent_source = True
            try:
                self.host._send_job(data)
            except _PriorityPending:
                stream.cancel_last(entry)
                self.sent_source = previous
                raise
        if not stream.pending:
            self._command('final_off', b'M5 M9\n', long=True)
            self.observation = replace(self.observation, phase=JobPhase.COMPLETING,
                diagnostic='All blocks accepted; verifying output-off and final Idle')
