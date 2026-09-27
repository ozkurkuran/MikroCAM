"""Single-owner GRBL lifecycle, bounded manual actions and coordinate evidence."""
from collections.abc import Callable
from dataclasses import replace
import logging
from time import monotonic, sleep

from mikrocam.machine.grbl import LineFramer, parse_report_units, parse_status
from mikrocam.machine.models import ConnectionState, MachineSnapshot, MachineState, XYZ
from mikrocam.machine.transport import Transport
from mikrocam.machine.manual_control import ManualControl
from mikrocam.machine.manual_models import JogRequest, ZeroRequest, SelectG54Request
from mikrocam.machine.manual_protocol import validate_command
from mikrocam.machine.models import ManualPhase
from mikrocam.machine.job_control import JobControl, _PriorityPending
from mikrocam.machine.job_models import StartJobRequest, JobPhase
from mikrocam.machine.job_protocol import validate_job_command
from mikrocam.machine.console_models import ConsoleRequest
from mikrocam.machine.console_control import ConsoleControl
from mikrocam.machine.wire_log import WireLog

POLL_INTERVAL = 0.25
STATUS_TIMEOUT = 2.0
SETTINGS_TIMEOUT = 3.0
_LOG = logging.getLogger(__name__)


class MachineController:
    """Own one transport; call every method from the same communication worker."""

    def __init__(self, transport: Transport, clock: Callable[[], float] = monotonic) -> None:
        self._transport = transport
        self._clock = clock
        self._snapshot = MachineSnapshot()
        self._wire = WireLog(clock)
        self._framer = LineFramer()
        self._status_sent_at: float | None = None
        self._settings_sent_at: float | None = None
        self._last_query_at = float('-inf')
        self._settings_saw_units = False
        self._pending_units: str | None = None
        self._query_sequence = self._pending_query_sequence = self._last_report_query = 0
        self._manual = ManualControl(self)
        self._job = JobControl(self)
        self._console = ConsoleControl(self)
        self._interrupted: Callable[[], bool] = lambda: False
        self._pause_requested: Callable[[], bool] = lambda: False

    def snapshot(self) -> MachineSnapshot:
        """Return an immutable observation; this does not perform I/O."""
        return self._snapshot

    def request_manual(self, request: JogRequest | ZeroRequest | SelectG54Request) -> None:
        """Admit one typed request on the communication owner, never raw G-code."""
        try:
            self._manual.start(request)
            self._console.publish()
        except ValueError as error:
            if not self._manual.active:
                self._manual.phase = ManualPhase.FAILED
                self._manual.message = str(error)[:256]
                self._manual.publish()
            raise

    def request_console(self, request: ConsoleRequest) -> None:
        """Reserve a finite diagnostic query without performing transport I/O."""
        self._console.start(request)

    def cancel_console_request(self, request: ConsoleRequest) -> None:
        """Retain the outcome of a priority-discarded typed intent; never write bytes."""
        if type(request) is not ConsoleRequest:
            raise ValueError('A typed diagnostic query is required')
        self._console.cancel_reserved(request)

    def set_interrupt_check(self, check: Callable[[], bool]) -> None:
        """Install a thread-safe signal reader; it must never perform I/O or GUI work."""
        self._interrupted = check

    def set_pause_check(self, check: Callable[[], bool]) -> None:
        """Read pending feed-hold intent without doing I/O outside the owner."""
        self._pause_requested = check

    def request_job(self, request: StartJobRequest) -> None:
        """Admit a prepared immutable job; live setup proof follows on this owner."""
        try:
            self._job.start(request)
            self._console.publish()
        except ValueError as error:
            if not self._job.active and not self._job.tainted:
                self._job.observation = replace(self._job.observation, phase=JobPhase.FAILED,
                                                diagnostic=str(error)[:256])
                self._job.publish()
            raise

    def pause_job(self) -> None:
        self._job.pause()

    def resume_job(self) -> None:
        self._job.resume()

    def stop_job(self) -> None:
        self._console.fail('Stop cancelled the diagnostic query')
        self._job.stop()
        self._manual.publish()

    def cancel_jog(self) -> None:
        self._console.fail('Cancel cancelled the diagnostic query')
        try:
            if self._manual.active:
                self._manual.cancel()
            elif not self._manual.tainted:
                self._manual.phase = ManualPhase.ABORTED
                self._manual.message = 'Pending manual request cancelled before admission'
                self._manual.publish()
        except Exception as error:
            self._fail(error)

    def abort(self) -> None:
        """Best-effort controller abort; a failed link cannot prove physical stopping."""
        self._console.fail('Abort cancelled the diagnostic query')
        if self._snapshot.connection is ConnectionState.CONNECTED:
            if self._job.active:
                self.stop_job()
            elif not self._job.tainted:
                self._manual.abort()

    def connect(self) -> None:
        if self._snapshot.connection in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
            raise ValueError('Already connected or connecting')
        self._wire.reset()
        self._reset_session(ConnectionState.CONNECTING)
        try:
            self._transport.open()
            self._snapshot = replace(self._snapshot, connection=ConnectionState.CONNECTED)
            self._request_settings()
            self._request_status()
        except Exception as error:
            self._fail(error)

    def disconnect(self) -> None:
        """Stop owned motion before closing; idle read-only closure emits no stop command."""
        self._console.fail('Disconnected during diagnostic query')
        self._close_manual_operation()
        self._job.stop('Disconnected during job; physical stop unverified')
        job = self._snapshot.job
        manual = self._snapshot.manual
        preserve = manual.phase in (ManualPhase.FAILED, ManualPhase.ABORTED)
        try:
            self._transport.close()
        except Exception as error:
            self._record('IO', b'', 'error', f'Disconnect failed: {error}')
            self._reset_session(ConnectionState.ERROR)
            self._diagnose(f'Disconnect failed: {error}')
        else:
            self._reset_session(ConnectionState.DISCONNECTED)
        if preserve:
            self._snapshot = replace(self._snapshot, manual=manual)
        if job.phase is not JobPhase.READY:
            self._snapshot = replace(self._snapshot, job=replace(job, can_start=False,
                                     can_pause=False, can_resume=False, can_stop=False))

    def _close_manual_operation(self) -> None:
        if not self._manual.active:
            return
        if self._manual.jog_sent:
            self.cancel_jog()
            deadline = monotonic() + 2.25
            while self._manual.active and monotonic() < deadline:
                self.tick()
                sleep(.01)
            if self._manual.active:
                self._manual.abort('Close could not verify jog cancellation; stop unverified', failed=True)
        else:
            self._manual.fail('Disconnected before manual operation could be verified', attempt_stop=False)

    def tick(self) -> None:
        """Perform one bounded read, process reports and schedule read-only requests."""
        if self._snapshot.connection is not ConnectionState.CONNECTED:
            return
        try:
            self._expire_and_poll()
            chunk = self._transport.read(4096)
            if type(chunk) is bytes:
                self._record('RX', chunk, 'received')
            self._expire_and_poll()
            try:
                lines = self._framer.feed(chunk)
            except ValueError as error:
                self._manual.lost_evidence('Corrupt controller framing', framing=True)
                self._job.fail('Corrupt controller framing')
                self._console.fail('Corrupt controller framing')
                self._invalidate(clear_units=True)
                self._settings_sent_at = None
                self._diagnose(f'Invalid controller framing; reconnect to verify units: {error}')
                lines = ()
            for line in lines:
                self._consume(line)
            self._expire_and_poll()
            self._console.tick()
            self._job.tick()
            self._manual.tick()
        except Exception as error:
            self._fail(error)

    def _reset_session(self, connection: ConnectionState) -> None:
        console = self._snapshot.console
        self._snapshot = MachineSnapshot(connection=connection, wire=self._wire.snapshot())
        self._framer.reset()
        self._status_sent_at = None
        self._settings_sent_at = None
        self._last_query_at = float('-inf')
        self._settings_saw_units = False
        self._pending_units = None
        self._query_sequence = self._pending_query_sequence = self._last_report_query = 0
        self._manual = ManualControl(self)
        self._job = JobControl(self)
        self._console = ConsoleControl(self)
        if connection is not ConnectionState.CONNECTING:
            self._console.observation = replace(console, can_query=False)
            self._snapshot = replace(self._snapshot, console=self._console.observation)

    def _fail(self, error: Exception) -> None:
        diagnostic = f'Communication failed: {error}'
        self._record('IO', b'', 'error', diagnostic)
        self._console.fail(diagnostic)
        self._manual.lost_evidence(diagnostic)
        self._job.fail(diagnostic)
        manual = self._snapshot.manual
        job = self._snapshot.job
        try:
            self._transport.close()
        except Exception as close_error:
            diagnostic += f'; close failed: {close_error}'
            self._record('IO', b'', 'error', f'Close failed: {close_error}')
        self._reset_session(ConnectionState.ERROR)
        self._snapshot = replace(self._snapshot, manual=manual, job=job)
        self._diagnose(diagnostic)

    def _diagnose(self, message: str) -> None:
        message = message[:256]
        self._snapshot = replace(self._snapshot, diagnostic=message)
        _LOG.debug('GRBL: %s', message)

    def _send(self, data: bytes) -> None:
        validate_command(data)
        _LOG.debug('GRBL TX %r', data)
        self._transmit(data, self._transport.write)

    def _send_console(self, data: bytes) -> None:
        validate_command(data)
        if self._interrupted() or self._pause_requested():
            self._console.fail('Priority request cancelled diagnostic query before writing')
            return
        self._transmit(data, self._transport.write)

    def _record(self, direction: str, payload: bytes, outcome: str, diagnostic: str = '') -> None:
        self._wire.append(direction, payload, outcome, diagnostic[:256])
        self._snapshot = replace(self._snapshot, wire=self._wire.snapshot())

    def _transmit(self, data: bytes, writer: Callable[[bytes], int]) -> None:
        try:
            count = writer(data)
            if type(count) is not int or count != len(data):
                raise OSError('Incomplete or invalid serial write count')
        except Exception as error:
            self._record('TX', data, 'uncertain', str(error))
            raise
        self._record('TX', data, 'complete')

    def _send_job(self, data: bytes) -> None:
        validate_job_command(data)
        _LOG.debug('GRBL JOB TX %r', data)
        if data not in (b'!', b'~') and (self._interrupted() or self._pause_requested()):
            raise _PriorityPending()
        self._transmit(data, self._transport.write_job)

    def _request_settings(self) -> None:
        self._settings_sent_at = self._clock()
        self._settings_saw_units = False
        self._pending_units = None
        self._send(b'$$\n')

    def _request_status(self) -> None:
        self._query_sequence += 1
        self._pending_query_sequence = self._query_sequence
        self._status_sent_at = self._last_query_at = self._clock()
        self._send(b'?')

    def _invalidate(self, *, clear_units: bool = False) -> None:
        self._snapshot = replace(
            self._snapshot, state=MachineState.UNKNOWN, raw_state='',
            machine_position_mm=None, work_position_mm=None, work_offset_mm=None,
            stale=True, last_report_at=None,
            report_units=None if clear_units else self._snapshot.report_units)

    def _consume(self, line: str) -> None:
        _LOG.debug('GRBL RX %r', line[:256])
        if line.startswith('Grbl '):
            self._console.fail('Controller reset interrupted diagnostic query')
            self._manual.lost_evidence('Controller reset interrupted manual operation', reset=True)
            self._job.fail('Controller reset interrupted job', reset=True)
            self._invalidate(clear_units=True)
            self._status_sent_at = None
            if not self._console.tainted:
                self._request_settings()
            self._diagnose('Controller restarted; awaiting units and fresh status')
        elif line.startswith('<'):
            self._consume_status(line)
        elif self._console.consume(line):
            pass
        elif self._job.consume(line):
            pass
        elif self._manual.consume(line):
            pass
        elif line.startswith('$13'):
            self._consume_units(line)
        elif line == 'ok' and self._settings_sent_at is not None:
            self._settings_sent_at = None
            if not self._settings_saw_units:
                self._invalidate(clear_units=True)
                self._diagnose('Settings response did not provide report units ($13)')
            else:
                self._invalidate()
                self._snapshot = replace(self._snapshot, report_units=self._pending_units)
        elif line.startswith('error:'):
            if self._settings_sent_at is not None:
                self._settings_sent_at = None
                self._invalidate(clear_units=True)
            self._diagnose(f'Controller {line}')
        elif line.startswith('ALARM:'):
            self._console.fail(f'Controller {line}')
            self._manual.lost_evidence(f'Controller {line}')
            self._job.fail(f'Controller {line}')
            self._invalidate()
            self._snapshot = replace(self._snapshot, state=MachineState.ALARM, raw_state=line)
            self._diagnose(line)
        elif line.startswith('[MSG:'):
            self._diagnose(line)

    def _consume_units(self, line: str) -> None:
        try:
            units = parse_report_units(line)
        except ValueError as error:
            self._invalidate(clear_units=True)
            self._settings_saw_units = False
            self._diagnose(f'Invalid report units: {error}')
            return
        if units is None:
            return
        if self._settings_sent_at is None:
            self._manual.lost_evidence('Unsolicited report-unit evidence')
            self._invalidate(clear_units=True)
            self._diagnose('Unsolicited or late report units; reconnect to verify settings')
            return
        self._pending_units = units
        self._settings_saw_units = True

    def _consume_status(self, line: str) -> None:
        try:
            status = parse_status(line)
        except ValueError as error:
            self._console.fail(f'Invalid status: {error}')
            self._manual.lost_evidence(f'Invalid status: {error}')
            self._job.fail(f'Invalid status: {error}')
            self._invalidate()
            self._diagnose(f'Invalid status: {error}')
            return
        self._status_sent_at = None
        self._last_report_query = self._pending_query_sequence
        self._pending_query_sequence = 0
        machine = work = offset = None
        if self._snapshot.report_units is not None:
            factor = 25.4 if self._snapshot.report_units == 'inch' else 1.0
            offset = self._scale(status.work_offset, factor) or self._snapshot.work_offset_mm
            machine = self._scale(status.machine_position, factor)
            work = self._scale(status.work_position, factor)
            if offset is not None:
                if machine is not None:
                    work = tuple(a - b for a, b in zip(machine, offset))
                elif work is not None:
                    machine = tuple(a + b for a, b in zip(work, offset))
        self._snapshot = replace(
            self._snapshot, state=status.state, raw_state=status.raw_state,
            machine_position_mm=machine, work_position_mm=work, work_offset_mm=offset,
            stale=False, last_report_at=self._clock(),
            diagnostic='' if self._snapshot.report_units is not None else self._snapshot.diagnostic)
        self._manual.on_status()
        self._job.on_status()

    @staticmethod
    def _scale(vector: XYZ | None, factor: float) -> XYZ | None:
        if vector is None:
            return None
        return tuple(value * factor for value in vector)

    def _expire_and_poll(self) -> None:
        now = self._clock()
        last = self._snapshot.last_report_at
        if last is not None and now - last >= STATUS_TIMEOUT:
            self._console.fail('Status became stale during diagnostic query')
            self._manual.lost_evidence('Status became stale during manual operation')
            self._job.fail('Status became stale during job')
            self._invalidate()
            self._diagnose('Status is stale; awaiting a fresh report')
        if self._settings_sent_at is not None and now - self._settings_sent_at >= SETTINGS_TIMEOUT:
            self._settings_sent_at = None
            self._invalidate(clear_units=True)
            self._diagnose('Settings response timed out; report units are unknown')
        if self._status_sent_at is not None and now - self._status_sent_at >= STATUS_TIMEOUT:
            self._console.poll_timeout()
            self._status_sent_at = None
            if not self._snapshot.diagnostic:
                self._diagnose('Status response timed out')
        if self._status_sent_at is None and now - self._last_query_at >= POLL_INTERVAL:
            self._request_status()
