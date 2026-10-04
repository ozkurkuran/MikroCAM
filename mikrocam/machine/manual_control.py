"""Concrete single-operation GRBL coordinator, owned by MachineController."""
from dataclasses import replace
from typing import TYPE_CHECKING

from .manual_models import JogRequest, ZeroRequest, SelectG54Request, PARAMETER_NAMES
from .manual_protocol import encode_jog, encode_zero, parse_modal, parse_parameter, parse_startup, verify_zero
from .models import ConnectionState, MachineState, ManualObservation, ManualPhase

if TYPE_CHECKING:
    from .controller import MachineController


class ManualControl:
    """No transport of its own: all I/O uses the owning controller's bounded boundary."""

    def __init__(self, host: 'MachineController') -> None:
        self.host = host
        self.phase = ManualPhase.READY
        self.action: str | None = None
        self.message = ''
        self.stop_unverified = False
        self.startup_verified = False
        self.tainted = False
        self.request = None
        self.transaction: str | None = None
        self.records: dict = {}
        self.deadline = 0.0
        self.completed = None
        self.waiting_status: str | None = None
        self.minimum_query = 0
        self.jog_sent = False
        self.cancel_ack_pending = False
        self.before_parameters = ()
        self.expected_position = None
        self.before_work = None

    @property
    def active(self) -> bool:
        return self.request is not None

    def eligible(self, *, zero: bool = False) -> bool:
        value = self.host.snapshot()
        now = self.host._clock()
        fresh = value.last_report_at is not None and 0 <= now - value.last_report_at < 2
        return (not self.tainted and not self.active and not self.host._job.active
                and not self.host._probe.active and not self.host._probe.tainted
                and not self.host._console.active and not self.host._console.tainted
                and not self.host._job.tainted and self.host._settings_sent_at is None
                and value.connection is ConnectionState.CONNECTED and value.state is MachineState.IDLE
                and fresh and not value.stale and value.report_units is not None
                and value.machine_position_mm is not None and value.firmware.motion_allowed
                and (not zero or value.work_position_mm is not None))

    def publish(self) -> None:
        eligible = self.eligible()
        observation = ManualObservation(
            self.phase, self.action, self.message[:256], eligible,
            self.eligible(zero=True), eligible,
            self.active and isinstance(self.request, JogRequest), self.stop_unverified)
        self.host._snapshot = replace(self.host._snapshot, manual=observation)

    def start(self, request: JogRequest | ZeroRequest | SelectG54Request) -> None:
        if type(request) not in (JogRequest, ZeroRequest, SelectG54Request):
            raise ValueError('A typed manual request is required')
        if not self.eligible(zero=isinstance(request, ZeroRequest)):
            raise ValueError('Manual action requires fresh verified Idle state and no pending operation')
        self.request = request
        self.action = 'jog' if isinstance(request, JogRequest) else 'zero' if isinstance(request, ZeroRequest) else 'select_g54'
        self.phase, self.message = ManualPhase.PREPARING, 'Verifying controller startup blocks'
        self.startup_verified = False
        self.stop_unverified = self.jog_sent = False
        self.completed = ('begin', {})
        self.publish()

    def _command(self, purpose: str, data: bytes) -> None:
        if self.transaction is not None:
            raise ValueError('Another ordinary command is outstanding')
        self.transaction, self.records = purpose, {}
        self.deadline = self.host._clock() + 3
        self.host._send(data)

    def _write_gate(self) -> None:
        if self.host._interrupted():
            raise ValueError('Priority stop interrupted manual preparation before writing')
        value = self.host.snapshot()
        if (value.connection is not ConnectionState.CONNECTED or value.state is not MachineState.IDLE
                or value.stale or value.report_units is None or value.machine_position_mm is None
                or value.last_report_at is None or not 0 <= self.host._clock() - value.last_report_at < 2):
            raise ValueError('Fresh verified Idle evidence is required immediately before writing')

    def consume(self, line: str) -> bool:
        """Collect one transaction; never transmit its next phase inside this batch."""
        if self.transaction is not None and self.host._clock() >= self.deadline:
            self.fail('Manual transaction response timed out before evidence arrived')
            return True
        if line in ('ok',) or line.startswith('error:'):
            if self.phase is ManualPhase.CANCELLING and self.cancel_ack_pending:
                self.cancel_ack_pending = False
                if line != 'ok':
                    self.fail(f'Cancelled command returned {line}')
                return True
            if self.transaction is None:
                if self.host._settings_sent_at is not None:
                    return False
                self.fail(f'Unexpected controller acknowledgement: {line}')
                return True
            purpose, records = self.transaction, self.records
            self.transaction, self.records = None, {}
            if line != 'ok':
                self.fail(f'{purpose} rejected: {line}')
            else:
                self.completed = (purpose, records)
            return True
        if self.transaction is None:
            return False
        try:
            record = self._query_record(line)
            if record is not None:
                key, value = record
                if key in self.records:
                    raise ValueError(f'Duplicate {key} query evidence')
                self.records[key] = value
                return True
        except ValueError as error:
            self.fail(str(error))
            return True
        return False

    def _query_record(self, line: str):
        if self.transaction == 'startup':
            item = parse_startup(line)
            return (item.index, item.block) if item is not None else None
        if self.transaction in ('modal_off', 'modal_zero', 'modal_selected'):
            item = parse_modal(line)
            return ('modal', item) if item is not None else None
        if self.transaction in ('parameters_before', 'parameters_after'):
            item = parse_parameter(line, self.host.snapshot().report_units)
            return (item.name, item) if item is not None else None
        return None

    def tick(self) -> None:
        if not self.active:
            self.publish()
            return
        try:
            if (self.transaction or self.waiting_status) and self.host._clock() >= self.deadline:
                raise ValueError(f'{self.transaction or self.waiting_status} response timed out')
            if self.completed is not None:
                purpose, records = self.completed
                self.completed = None
                self._advance(purpose, records)
            if self.waiting_status is not None:
                self._status_progress()
        except ValueError as error:
            self.fail(str(error))
        self.publish()

    def _advance(self, purpose: str, records: dict) -> None:
        if purpose == 'begin':
            self._write_gate()
            self._command('startup', b'$N\n')
        elif purpose == 'startup':
            if records != {0: '', 1: ''}:
                raise ValueError('Both startup blocks must be verified empty before manual control')
            self.startup_verified = True
            self._after_startup()
        elif purpose == 'off':
            self._command('modal_off', b'$G\n')
        elif purpose.startswith('modal_'):
            self._after_modal(purpose, records)
        elif purpose == 'jog':
            self.phase = ManualPhase.MOVING
            self._await_status('jog_done', 30)
        elif purpose == 'select':
            self._clear_positions()
            self._command('modal_selected', b'$G\n')
        elif purpose == 'parameters_before':
            self.before_parameters = self._inventory(records)
            self._await_status('zero_ready')
        elif purpose == 'zero':
            self._clear_positions()
            self._command('parameters_after', b'$#\n')
        elif purpose == 'parameters_after':
            verify_zero(self.before_parameters, self._inventory(records), self.expected_position, self.request.axes)
            self._await_status('zero_done')

    def _after_startup(self) -> None:
        self._write_gate()
        if isinstance(self.request, JogRequest):
            self._command('off', b'M5 M9\n')
        elif isinstance(self.request, ZeroRequest):
            self._command('modal_zero', b'$G\n')
        else:
            self._command('select', b'G54\n')

    def _after_modal(self, purpose: str, records: dict) -> None:
        modal = records.get('modal')
        if modal is None:
            raise ValueError('Modal query did not return complete evidence')
        if purpose == 'modal_off':
            if modal.spindle != 'M5' or modal.coolant != ('M9',):
                raise ValueError('Output-off controller modes could not be verified')
            self._await_status('jog_ready')
        elif modal.work_system != 'G54':
            raise ValueError('Explicitly select G54 before setting its work zero')
        elif purpose == 'modal_zero':
            self._command('parameters_before', b'$#\n')
        else:
            self._await_status('select_done')

    @staticmethod
    def _inventory(records: dict) -> tuple:
        if set(records) != set(PARAMETER_NAMES):
            raise ValueError('Parameter query did not return all unique required records')
        return tuple(records[name] for name in PARAMETER_NAMES)

    def _await_status(self, purpose: str, timeout: float = 3) -> None:
        self.waiting_status = purpose
        self.minimum_query = self.host._query_sequence + 1
        self.deadline = self.host._clock() + timeout
        if purpose != 'jog_done':
            self.phase = ManualPhase.VERIFYING

    def _status_progress(self) -> None:
        if self.host._last_report_query < self.minimum_query:
            return
        value = self.host.snapshot()
        purpose = self.waiting_status
        if purpose == 'cancelled':
            if value.state is MachineState.IDLE and not self.cancel_ack_pending:
                self._finish('Jog cancellation verified by controller status')
            return
        if purpose == 'jog_done' and value.state is MachineState.JOG:
            return
        if value.state is not MachineState.IDLE or value.stale or value.machine_position_mm is None:
            raise ValueError('Fresh Idle coordinates could not be verified')
        self.waiting_status = None
        if purpose == 'jog_ready':
            self._write_gate()
            target = list(value.machine_position_mm)
            target['XYZ'.index(self.request.axis)] += self.request.distance_mm
            self.expected_position = tuple(target)
            self.jog_sent = True
            self._command('jog', encode_jog(self.request))
        elif purpose == 'jog_done':
            if not self._near(value.machine_position_mm, self.expected_position):
                raise ValueError('Jog ended at an unexpected position')
            self._finish('Jog endpoint verified')
        elif purpose == 'zero_ready':
            self._begin_zero(value)
        elif purpose == 'zero_done':
            self._verify_work_zero(value)
            self._finish('G54 zero and unchanged axes verified')
        else:
            if value.work_position_mm is None or value.work_offset_mm is None:
                raise ValueError('Fresh G54 work offset could not be verified')
            self._finish('G54 selection verified')

    def _begin_zero(self, value) -> None:
        self._write_gate()
        if value.work_position_mm is None:
            raise ValueError('Known work coordinates are required before zeroing')
        self.expected_position = value.machine_position_mm
        self.before_work = value.work_position_mm
        parameters = {item.name: item.value for item in self.before_parameters}
        expected_work = tuple(value.machine_position_mm[i] - parameters['G54'][i] - parameters['G92'][i]
                              - (parameters['TLO'] if i == 2 else 0) for i in range(3))
        if not self._near(value.work_position_mm, expected_work):
            raise ValueError('G54 parameter evidence does not agree with current work coordinates')
        self._command('zero', encode_zero(self.request))

    def _verify_work_zero(self, value) -> None:
        if value.work_offset_mm is None or value.work_position_mm is None:
            raise ValueError('Fresh work offset is missing after zero')
        if not self._near(value.machine_position_mm, self.expected_position):
            raise ValueError('Machine position changed while setting G54 zero')
        target = tuple(0 if axis in self.request.axes else self.before_work[i] for i, axis in enumerate('XYZ'))
        if not self._near(value.work_position_mm, target):
            raise ValueError('G54 work zero or omitted axes could not be verified')

    @staticmethod
    def _near(actual: tuple, expected: tuple) -> bool:
        return all(abs(a - b) <= .005 for a, b in zip(actual, expected))

    def _clear_positions(self) -> None:
        self.host._snapshot = replace(self.host._snapshot, machine_position_mm=None,
                                      work_position_mm=None, work_offset_mm=None, stale=True)

    def on_status(self) -> None:
        if not self.active:
            return
        state = self.host.snapshot().state
        allowed = (MachineState.IDLE, MachineState.JOG) if self.jog_sent else (MachineState.IDLE,)
        if self.phase is ManualPhase.CANCELLING:
            allowed = (MachineState.IDLE, MachineState.JOG, MachineState.DOOR)
        if state not in allowed:
            self.fail(f'Manual operation interrupted by {state.value}')

    def lost_evidence(self, message: str, *, reset: bool = False, framing: bool = False) -> None:
        if reset or framing:
            self.startup_verified = False
        if self.active:
            self.fail(message, attempt_stop=not reset)
        self.publish()

    def cancel(self) -> None:
        if not self.active or not isinstance(self.request, JogRequest):
            return
        if not self.jog_sent:
            self.fail('Jog cancelled before motion', attempt_stop=False)
            return
        if self.phase is ManualPhase.CANCELLING:
            return
        self.cancel_ack_pending = self.transaction == 'jog'
        self.transaction, self.completed = None, None
        self.phase, self.message = ManualPhase.CANCELLING, 'Waiting for verified jog cancellation'
        self.waiting_status = 'cancelled'
        self.minimum_query = self.host._query_sequence + 1
        self.deadline = self.host._clock() + 2
        self.host._send(b'\x85')
        self.publish()

    def abort(self, message: str = 'Abort requested; physical stop is unverified', *, failed: bool = False) -> None:
        reset_allowed = self.startup_verified
        command = b'\x18' if reset_allowed else b'\x84'
        if not reset_allowed:
            message += '; safety-door stop may perform configured parking'
        self._end(ManualPhase.FAILED if failed else ManualPhase.ABORTED, message, uncertain=True)
        self.startup_verified = False
        self.host._invalidate(clear_units=True)
        self.host._settings_sent_at = None
        try:
            self.host._send(command)
        except Exception as error:
            self.message = (self.message + f'; stop delivery failed: {error}')[:256]
        self.publish()

    def fail(self, message: str, *, attempt_stop: bool = True) -> None:
        if not self.active and self.stop_unverified:
            self.publish()
            return
        if self.active and self.jog_sent and attempt_stop:
            self.abort(message + '; stop unverified', failed=True)
        else:
            uncertain = self.active and self.jog_sent
            self._end(ManualPhase.FAILED, message, uncertain=uncertain)
            if self.action is not None:
                self.host._invalidate()
            self.publish()

    def _end(self, phase: ManualPhase, message: str, *, uncertain: bool) -> None:
        self.phase, self.message, self.stop_unverified = phase, message[:256], uncertain
        self.tainted = True
        self.request = self.transaction = self.completed = self.waiting_status = None
        self.records = {}

    def _finish(self, message: str) -> None:
        self.phase, self.message, self.stop_unverified = ManualPhase.COMPLETE, message, False
        self.request = self.transaction = self.completed = self.waiting_status = None
        self.records = {}
        self.jog_sent = False
        self.publish()
