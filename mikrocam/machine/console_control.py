"""One finite read-only query; the host owns all transport and raw evidence."""
from dataclasses import replace
from typing import TYPE_CHECKING

from .console_models import ConsoleObservation, ConsolePhase, ConsoleRequest
from .grbl import parse_report_units
from .models import ConnectionState, MachineState

if TYPE_CHECKING:
    from .controller import MachineController


class ConsoleControl:
    def __init__(self, host: 'MachineController') -> None:
        self.host = host
        self.observation = ConsoleObservation()
        self.active = self.tainted = self.sent = self.acknowledged = False
        self.deadline = 0.
        self.minimum_query = 0
        self.saw_units = False
        self.causality_lost = False

    def _idle(self) -> bool:
        value = self.host.snapshot()
        return (not self.causality_lost
                and value.connection is ConnectionState.CONNECTED and value.state is MachineState.IDLE
                and not value.stale and value.report_units is not None
                and value.machine_position_mm is not None and value.last_report_at is not None
                and 0 <= self.host._clock() - value.last_report_at < 2
                and not self.host._manual.active and not self.host._manual.tainted
                and not self.host._job.active and not self.host._job.tainted
                and not self.host._probe.active and not self.host._probe.tainted
                and self.host._settings_sent_at is None and not self.host._firmware.pending)

    def publish(self) -> None:
        self.observation = replace(self.observation,
                                   can_query=not self.active and not self.tainted and self._idle())
        self.host._snapshot = replace(self.host._snapshot, console=self.observation)

    def start(self, request: ConsoleRequest) -> None:
        if type(request) is not ConsoleRequest or self.active or self.tainted or not self._idle():
            raise ValueError('Query requires fresh verified Idle and no competing or uncertain operation')
        self.active, self.sent, self.acknowledged, self.saw_units = True, False, False, False
        self.deadline = self.host._clock() + 3
        self.minimum_query = self.host._query_sequence + 1
        self.observation = ConsoleObservation(ConsolePhase.PENDING, request.command, 'Query pending')
        self.publish()
        self.host._manual.publish()
        self.host._job.publish()

    def fail(self, message: str) -> None:
        if self.tainted or not self.active:
            return
        self.active, self.tainted = False, True
        self.observation = replace(self.observation, phase=ConsolePhase.FAILED,
                                   diagnostic=message[:256], can_query=False)
        self.host._invalidate(clear_units=True)
        self.publish()

    def cancel_reserved(self, request: ConsoleRequest) -> None:
        """Report a GUI intent cancelled before owner admission, with no wire ambiguity."""
        if self.active:
            self.fail('Priority request cancelled diagnostic query')
        elif not self.tainted:
            self.observation = ConsoleObservation(ConsolePhase.FAILED, request.command,
                                                   'Query cancelled before owner admission')
            self.publish()

    def consume(self, line: str) -> bool:
        if line.startswith('ALARM:'):
            return False
        if self.tainted:
            return True  # Late traffic cannot release quarantined ACK ownership.
        acknowledgement = line == 'ok' or line.startswith('error:')
        if not self.active:
            if (self.observation.phase is ConsolePhase.COMPLETE and acknowledgement
                    and not self.host._manual.active and not self.host._job.active
                    and self.host._settings_sent_at is None):
                self.active = True
                self.fail('Unsolicited acknowledgement after console query')
                return True
            return False
        if any(not 32 <= ord(char) <= 126 for char in line):
            self.fail('Invalid control bytes in diagnostic response')
            return True
        if acknowledgement:
            if not self.sent or self.observation.command == '?' or self.acknowledged:
                self.fail('Unexpected or duplicate query acknowledgement')
            elif line != 'ok':
                self.fail(f'Query rejected: {line}')
            elif self.observation.command == '$$' and not self.saw_units:
                self.fail('Settings query did not provide unique matching report units')
            else:
                self.acknowledged = True
        elif self.observation.command == '$$' and line.startswith('$13'):
            try:
                units = parse_report_units(line)
                if (not self.sent or self.acknowledged or self.saw_units
                        or units is None or units != self.host.snapshot().report_units):
                    raise ValueError('Duplicate, late or changed report units in settings query')
                self.saw_units = True
            except ValueError as error:
                self.fail(str(error))
        return True

    def poll_timeout(self) -> None:
        """GRBL status replies have no IDs: a timed-out poll loses causal attribution."""
        self.causality_lost = True
        self.fail('Status query timed out; reconnect to restore diagnostic query attribution')
        if not self.tainted:
            self.observation = replace(self.observation,
                                       diagnostic='Status poll timed out; reconnect before diagnostic queries')
        self.publish()

    def tick(self) -> None:
        if self.active:
            if self.host._interrupted() or self.host._pause_requested():
                self.fail('Priority request cancelled the diagnostic query')
            elif self.host._clock() >= self.deadline:
                self.fail('Diagnostic query timed out; reconnect before another operation')
            elif not self._idle():
                self.fail('Fresh verified Idle evidence was lost during diagnostic query')
            elif self.observation.command == '?':
                if self.host._last_report_query >= self.minimum_query:
                    self._complete()
            elif self.acknowledged:
                self._complete()
            elif not self.sent:
                self.sent = True
                self.host._send_console((self.observation.command + '\n').encode('ascii'))
        self.publish()

    def _complete(self) -> None:
        self.active = False
        self.observation = replace(self.observation, phase=ConsolePhase.COMPLETE,
                                   diagnostic='Query complete; raw response is shown in the wire log')
