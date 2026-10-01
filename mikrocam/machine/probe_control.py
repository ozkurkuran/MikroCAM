"""One finite probe transaction at a time on the existing communication owner."""
from dataclasses import replace
from typing import TYPE_CHECKING
from mikrocam.core.probe_map import ProbeMap
from .probe_models import StartProbeGridRequest, ProbeObservation, ProbePhase
from .probe_protocol import probe_move, parse_probe_result, parse_probe_record
from .job_preparation import near, query_record, verify_modal
from .manual_models import PARAMETER_NAMES
from .models import ConnectionState, MachineState

if TYPE_CHECKING:
    from .controller import MachineController


class ProbeControl:
    def __init__(self, host: 'MachineController') -> None:
        self.host = host
        self.request: StartProbeGridRequest | None = None
        self.observation = ProbeObservation()
        self.tainted = self.sent_motion = self.startup_verified = False
        self.transaction = self.completed = self.waiting = None
        self.records: dict = {}
        self.heights: list[float | None] = []
        self.position = self.target = self.contact = None
        self.minimum_query = 0
        self.deadline = 0.
        self.report_units = None

    @property
    def active(self) -> bool:
        return self.request is not None

    def eligible(self) -> bool:
        return not self.active and not self.tainted and self.host._manual.eligible(zero=True)

    def publish(self) -> None:
        self.observation = replace(self.observation, can_start=self.eligible(), can_stop=self.active)
        self.host._snapshot = replace(self.host._snapshot, probe=self.observation)

    def start(self, request: StartProbeGridRequest) -> None:
        if type(request) is not StartProbeGridRequest or not self.eligible():
            raise ValueError('Probe requires verified Idle with no competing or uncertain operation')
        value, plan = self.host.snapshot(), request.plan
        if not near(value.machine_position_mm, plan.initial_machine_mm) or not near(value.work_offset_mm, plan.g54_offset_mm):
            raise ValueError('Reviewed probe position/G54 changed; review again')
        self.request = request
        self.position = plan.initial_machine_mm
        self.heights = [None] * plan.grid.count
        self.sent_motion = self.startup_verified = False
        self.report_units = value.report_units
        self.completed = ('begin', {})
        self.observation = ProbeObservation(ProbePhase.PREPARING, total=plan.grid.count,
                                             diagnostic='Verifying probe setup')
        self.publish()
        self.host._manual.publish()
        self.host._job.publish()
        self.host._console.publish()

    def _guard(self, *, moving: bool = False) -> None:
        value, plan = self.host.snapshot(), self.request.plan
        if (value.connection is not ConnectionState.CONNECTED or value.stale
                or value.last_report_at is None or not 0 <= self.host._clock() - value.last_report_at < 2
                or value.report_units != self.report_units or value.machine_position_mm is None):
            raise ValueError('Probe requires fresh coordinates and unchanged report units')
        if not near(value.work_offset_mm, plan.g54_offset_mm):
            raise ValueError('Probe work offset changed')
        allowed = (MachineState.IDLE, MachineState.RUNNING) if moving else (MachineState.IDLE,)
        if value.state not in allowed:
            raise ValueError('Controller state does not permit probing')
        if any(p < lo - .005 or p > hi + .005 for p, lo, hi in zip(
                value.machine_position_mm, plan.machine_min_mm, plan.machine_max_mm)):
            raise ValueError('Reported probe position outside the reviewed machine envelope')
        if not moving and not near(value.machine_position_mm, self.position):
            raise ValueError('Position changed before probe command')

    def _command(self, purpose: str, data: bytes, target: tuple | None = None) -> None:
        if self.host._interrupted() or self.host._pause_requested():
            raise ValueError('Priority request interrupted probing before writing')
        self._guard()
        if self.transaction is not None:
            raise ValueError('Another probe command still owns its acknowledgement')
        self.transaction, self.records, self.target = purpose, {}, target
        self.deadline = self.host._clock() + (self.request.plan.timeout_seconds if target else 3.)
        if target is None:
            self.host._send(data)
        else:
            self.sent_motion = True
            self.host._send_probe(data)

    def consume(self, line: str) -> bool:
        if not self.active:
            if line.startswith('[PRB') and not self.tainted:
                return self._inactive_result()
            return self.tainted and (line == 'ok' or line.startswith(('error:', '[PRB:', '$', '[GC:', '[G5', '[G92:', '[TLO:')))
        try:
            if self.transaction is not None and self.host._clock() >= self.deadline:
                raise ValueError('Probe transaction response timed out before evidence arrived')
            if line == 'ok' or line.startswith('error:'):
                if self.transaction is None or line != 'ok':
                    raise ValueError('Unexpected, duplicate or rejected probe acknowledgement: ' + line)
                if self.transaction == 'probe' and 'contact' not in self.records:
                    raise ValueError('Probe acknowledged without successful contact evidence')
                self.completed = (self.transaction, self.records)
                self.transaction, self.records = None, {}
                return True
            if line.startswith('[PRB'):
                if self.transaction == 'parameters':
                    key, record = 'cached_probe', parse_probe_record(line, self.report_units)
                elif self.transaction == 'probe':
                    key, record = 'contact', parse_probe_result(line, self.report_units)
                else:
                    raise ValueError('Unsolicited or late probe result')
            else:
                item = query_record(self.transaction, line, self.report_units)
                if item is None:
                    if line.startswith(('$', '[GC', '[G5', '[G92', '[TLO')):
                        raise ValueError('Unsolicited probe setup evidence')
                    return False
                key, record = item
            if key in self.records:
                raise ValueError('Duplicate probe evidence')
            self.records[key] = record
            return True
        except ValueError as error:
            self.fail(str(error))
            return True

    def _inactive_result(self) -> bool:
        host = self.host
        cached = (host._manual.transaction in ('parameters_before', 'parameters_after')
                  or host._job.transaction == 'parameters'
                  or (host._console.active and host._console.observation.command == '$#'))
        if cached:
            return False
        diagnostic = 'Unsolicited probe result; reconnect before another operation'
        self.tainted = True
        self.observation = replace(self.observation, phase=ProbePhase.FAILED, diagnostic=diagnostic)
        host._manual.lost_evidence(diagnostic)
        host._job.fail(diagnostic)
        host._console.fail(diagnostic)
        host._invalidate(clear_units=True)
        self.publish()
        return True

    def tick(self) -> None:
        if not self.active:
            self.publish()
            return
        try:
            if self.host._interrupted() or self.host._pause_requested():
                return
            self._guard(moving=self.sent_motion)
            if (self.transaction or self.waiting) and self.host._clock() >= self.deadline:
                raise ValueError('Probe response or Idle confirmation timed out')
            if self.completed is not None:
                purpose, records = self.completed
                self.completed = None
                self._advance(purpose, records)
            if self.waiting:
                self._status_progress()
        except ValueError as error:
            self.fail(str(error))
        finally:
            self.publish()

    def _advance(self, purpose: str, records: dict) -> None:
        if purpose == 'begin':
            self._command('startup', b'$N\n')
        elif purpose == 'startup':
            if records != {0: '', 1: ''}:
                raise ValueError('Both startup blocks must be empty for probing')
            self.startup_verified = True
            self._command('settings', b'$$\n')
        elif purpose == 'settings':
            if records.get(13) != (1 if self.report_units == 'inch' else 0) or records.get(32) != 0:
                raise ValueError('Probing requires unchanged report units and mechanical mode $32=0')
            self._command('outputs', b'M5 M9\n')
        elif purpose == 'outputs':
            self._command('modal', b'$G\n')
        elif purpose == 'modal':
            verify_modal(records)
            self._command('parameters', b'$#\n')
        elif purpose == 'parameters':
            values = {key: value for key, value in records.items() if key != 'cached_probe'}
            if (set(values) != set(PARAMETER_NAMES) or values.get('G92') != (0., 0., 0.)
                    or values.get('TLO') != 0 or not near(values.get('G54'), self.request.plan.g54_offset_mm)):
                raise ValueError('Probing requires verified G54 and zero G92/tool offsets')
            self._wait_status('initial', self.position)
        elif purpose in ('clearance', 'xy', 'retract', 'probe'):
            if purpose == 'probe':
                contact = records['contact']
                self._check_contact(contact)
                self.contact = self.target = contact
            self._wait_status(purpose, self.target)

    def _wait_status(self, purpose: str, target: tuple) -> None:
        self.waiting, self.target = purpose, target
        self.minimum_query = self.host._query_sequence + 1
        self.deadline = self.host._clock() + self.request.plan.timeout_seconds

    def _check_contact(self, contact: tuple) -> None:
        plan = self.request.plan
        if not near(contact[:2], self.target[:2]):
            raise ValueError('Probe contact XY differs from the reviewed point')
        z = contact[2] - plan.g54_offset_mm[2]
        if not plan.min_z_mm - .005 <= z < plan.safe_z_mm:
            raise ValueError('Probe contact Z outside the reviewed downward segment')

    def _status_progress(self) -> None:
        if self.host._last_report_query < self.minimum_query:
            return
        self._guard(moving=True)
        value = self.host.snapshot()
        if value.state is MachineState.RUNNING:
            return
        if self.waiting == 'probe':
            self._check_stopped(value.machine_position_mm)
        elif not near(value.machine_position_mm, self.target):
            raise ValueError('Fresh probe Idle endpoint differs from expected motion/contact')
        purpose, self.waiting = self.waiting, None
        self.position = value.machine_position_mm
        plan = self.request.plan
        if purpose == 'initial':
            self.observation = replace(self.observation, phase=ProbePhase.PROBING,
                                         diagnostic='Acquiring grid; retracting before travel')
            self._vertical('clearance', plan.safe_z_mm)
        elif purpose in ('clearance', 'retract'):
            if all(height is not None for height in self.heights):
                self._end(ProbePhase.COMPLETE, 'All contacts and final clearance verified', False)
            else:
                x, y = plan.grid.points[self.observation.completed]
                target = (x + plan.g54_offset_mm[0], y + plan.g54_offset_mm[1], self.position[2])
                self._command('xy', probe_move(x=x, y=y, feed=plan.travel_feed_mm_min), target)
        elif purpose == 'xy':
            self._vertical('probe', plan.min_z_mm)
        elif purpose == 'probe':
            index = self.observation.completed
            self.heights[index] = self.contact[2] - plan.g54_offset_mm[2]
            self.observation = replace(self.observation, completed=index + 1,
                                         map=self._map('incomplete'), diagnostic='Contact verified; retracting')
            self._vertical('retract', plan.safe_z_mm)

    def _check_stopped(self, position: tuple) -> None:
        plan = self.request.plan
        minimum = plan.min_z_mm + plan.g54_offset_mm[2]
        if (not near(position[:2], self.contact[:2])
                or not minimum - .005 <= position[2] <= self.contact[2] + .005):
            raise ValueError('Stopped probe position lies outside the downward contact segment')

    def _vertical(self, purpose: str, z: float) -> None:
        plan = self.request.plan
        target = (*self.position[:2], z + plan.g54_offset_mm[2])
        feed = plan.probe_feed_mm_min if purpose == 'probe' else plan.travel_feed_mm_min
        self._command(purpose, probe_move(z=z, feed=feed, probing=purpose == 'probe'), target)

    def on_status(self) -> None:
        if self.active:
            try:
                self._guard(moving=self.sent_motion)
            except ValueError as error:
                self.fail(str(error))

    def _map(self, outcome: str) -> ProbeMap:
        plan = self.request.plan
        origin = getattr(self.host._transport, 'probe_origin', 'measured')
        return ProbeMap(plan.grid, tuple(self.heights), plan.g54_offset_mm, outcome, origin)

    def _end(self, phase: ProbePhase, message: str, uncertain: bool) -> None:
        result = self._map(phase.value)
        self.tainted = phase is not ProbePhase.COMPLETE
        self.request = self.transaction = self.completed = self.waiting = None
        self.records = {}
        self.observation = replace(self.observation, phase=phase, map=result,
                                     diagnostic=message[:256], stop_unverified=uncertain)
        self.publish()
        self.host._manual.publish()
        self.host._job.publish()
        self.host._console.publish()

    def stop(self, message: str = 'Probe stopped; physical stopping unverified', *, failed: bool = False) -> None:
        if not self.active:
            return
        sent = self.sent_motion
        command = b'\x18' if self.startup_verified else b'\x84'
        self._end(ProbePhase.FAILED if failed else ProbePhase.ABORTED, message, sent)
        if sent:
            self.host._invalidate(clear_units=True)
            self.host._settings_sent_at = None
            try:
                self.host._send(command)
            except Exception as error:
                self.observation = replace(self.observation, diagnostic=(message + '; stop delivery failed: ' + str(error))[:256])
        self.publish()

    def fail(self, message: str, *, reset: bool = False) -> None:
        if not self.active:
            return
        if reset or not self.sent_motion:
            self._end(ProbePhase.FAILED, message, self.sent_motion)
        else:
            self.stop(message + '; physical stopping unverified', failed=True)
