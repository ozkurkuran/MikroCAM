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
        self._framer = LineFramer()
        self._status_sent_at: float | None = None
        self._settings_sent_at: float | None = None
        self._last_query_at = float('-inf')
        self._settings_saw_units = False
        self._pending_units: str | None = None
        self._query_sequence = self._pending_query_sequence = self._last_report_query = 0
        self._manual = ManualControl(self)
        self._interrupted: Callable[[], bool] = lambda: False

    def snapshot(self) -> MachineSnapshot:
        """Return an immutable observation; this does not perform I/O."""
        return self._snapshot

    def request_manual(self, request: JogRequest | ZeroRequest | SelectG54Request) -> None:
        """Admit one typed request on the communication owner, never raw G-code."""
        try:
            self._manual.start(request)
        except ValueError as error:
            if not self._manual.active:
                self._manual.phase = ManualPhase.FAILED
                self._manual.message = str(error)[:256]
                self._manual.publish()
            raise

    def set_interrupt_check(self, check: Callable[[], bool]) -> None:
        """Install a thread-safe signal reader; it must never perform I/O or GUI work."""
        self._interrupted = check

    def cancel_jog(self) -> None:
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
        if self._snapshot.connection is ConnectionState.CONNECTED:
            self._manual.abort()

    def connect(self) -> None:
        if self._snapshot.connection in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
            raise ValueError('Already connected or connecting')
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
        self._close_manual_operation()
        manual = self._snapshot.manual
        preserve = manual.phase in (ManualPhase.FAILED, ManualPhase.ABORTED)
        try:
            self._transport.close()
        except Exception as error:
            self._reset_session(ConnectionState.ERROR)
            self._diagnose(f'Disconnect failed: {error}')
        else:
            self._reset_session(ConnectionState.DISCONNECTED)
        if preserve:
            self._snapshot = replace(self._snapshot, manual=manual)

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
            self._expire_and_poll()
            try:
                lines = self._framer.feed(chunk)
            except ValueError as error:
                self._manual.lost_evidence('Corrupt controller framing', framing=True)
                self._invalidate(clear_units=True)
                self._settings_sent_at = None
                self._diagnose(f'Invalid controller framing; reconnect to verify units: {error}')
                lines = ()
            for line in lines:
                self._consume(line)
            self._expire_and_poll()
            self._manual.tick()
        except Exception as error:
            self._fail(error)

    def _reset_session(self, connection: ConnectionState) -> None:
        self._snapshot = MachineSnapshot(connection=connection)
        self._framer.reset()
        self._status_sent_at = None
        self._settings_sent_at = None
        self._last_query_at = float('-inf')
        self._settings_saw_units = False
        self._pending_units = None
        self._query_sequence = self._pending_query_sequence = self._last_report_query = 0
        self._manual = ManualControl(self)

    def _fail(self, error: Exception) -> None:
        diagnostic = f'Communication failed: {error}'
        self._manual.lost_evidence(diagnostic)
        manual = self._snapshot.manual
        try:
            self._transport.close()
        except Exception as close_error:
            diagnostic += f'; close failed: {close_error}'
        self._reset_session(ConnectionState.ERROR)
        self._snapshot = replace(self._snapshot, manual=manual)
        self._diagnose(diagnostic)

    def _diagnose(self, message: str) -> None:
        message = message[:256]
        self._snapshot = replace(self._snapshot, diagnostic=message)
        _LOG.debug('GRBL: %s', message)

    def _send(self, data: bytes) -> None:
        validate_command(data)
        _LOG.debug('GRBL TX %r', data)
        if self._transport.write(data) != len(data):
            raise OSError('Incomplete serial write')

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
            self._manual.lost_evidence('Controller reset interrupted manual operation', reset=True)
            self._invalidate(clear_units=True)
            self._status_sent_at = None
            self._request_settings()
            self._diagnose('Controller restarted; awaiting units and fresh status')
        elif line.startswith('<'):
            self._consume_status(line)
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
            self._manual.lost_evidence(f'Controller {line}')
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
            self._manual.lost_evidence(f'Invalid status: {error}')
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

    @staticmethod
    def _scale(vector: XYZ | None, factor: float) -> XYZ | None:
        if vector is None:
            return None
        return tuple(value * factor for value in vector)

    def _expire_and_poll(self) -> None:
        now = self._clock()
        last = self._snapshot.last_report_at
        if last is not None and now - last >= STATUS_TIMEOUT:
            self._manual.lost_evidence('Status became stale during manual operation')
            self._invalidate()
            self._diagnose('Status is stale; awaiting a fresh report')
        if self._settings_sent_at is not None and now - self._settings_sent_at >= SETTINGS_TIMEOUT:
            self._settings_sent_at = None
            self._invalidate(clear_units=True)
            self._diagnose('Settings response timed out; report units are unknown')
        if self._status_sent_at is not None and now - self._status_sent_at >= STATUS_TIMEOUT:
            self._status_sent_at = None
            if not self._snapshot.diagnostic:
                self._diagnose('Status response timed out')
        if self._status_sent_at is None and now - self._last_query_at >= POLL_INTERVAL:
            self._request_status()
