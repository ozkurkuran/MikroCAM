"""One read-only $I identification transaction owned by the MachineController (spec 042)."""
from dataclasses import replace
from typing import TYPE_CHECKING

from .firmware import (MAX_EVIDENCE_LINES, MAX_TEXT, FirmwareFamily, FirmwareObservation,
                       IdentificationPhase, banner_consistent, capabilities_for, identify)
from .fluidnc import RESTART_QUIET_SECONDS

if TYPE_CHECKING:
    from .controller import MachineController

IDENTIFY_COMMAND = b'$I\n'
IDENTIFY_TIMEOUT = 3.0


class FirmwareIdentification:
    """Claims only $I build-info records and their terminal ok/error while pending."""

    def __init__(self, host: 'MachineController') -> None:
        self.host = host
        self.sent_at: float | None = None
        self.lines: list[str] = []
        self.invalid = ''
        self.banner = ''
        self.observation = FirmwareObservation()
        self.restarting = False
        self.quiet_since = 0.

    @property
    def pending(self) -> bool:
        return self.sent_at is not None

    @property
    def fluidnc(self) -> bool:
        return (self.observation.phase is IdentificationPhase.IDENTIFIED
                and self.observation.capabilities.family is FirmwareFamily.FLUIDNC)

    def on_restart(self) -> None:
        """Boot output or FluidNC free text (spec 044): identity is void until the board is ready."""
        self.sent_at, self.lines, self.invalid, self.banner = None, [], '', ''
        self.restarting, self.quiet_since = True, self.host._clock()
        self.observation = FirmwareObservation(
            IdentificationPhase.FAILED, capabilities_for(FirmwareFamily.UNKNOWN),
            diagnostic='Controller restarting; identification resumes once it reports ready')
        self.publish()

    def chatter(self) -> None:
        """Any non-status line while restarting (boot log, greeting, MSG) restarts the quiet time."""
        if self.restarting:
            self.quiet_since = self.host._clock()

    def settled(self, raw_state: str) -> bool:
        """Ready after a quiet period and a fresh status that is not FluidNC's Starting state."""
        if (not self.restarting or raw_state == 'Starting'
                or self.host._clock() - self.quiet_since < RESTART_QUIET_SECONDS):
            return False
        self.restarting = False
        return True

    def publish(self) -> None:
        self.host._snapshot = replace(self.host._snapshot, firmware=self.observation)

    def start(self) -> None:
        """Write $I immediately before the session settings request; never retried."""
        self.sent_at, self.lines, self.invalid = self.host._clock(), [], ''
        self.restarting = False
        self.observation = FirmwareObservation(IdentificationPhase.PENDING, banner=self.banner)
        self.publish()
        self.host._send(IDENTIFY_COMMAND)

    def consume(self, line: str) -> bool:
        if not self.pending:
            return False
        if line == 'ok':
            self._finish()
        elif line.startswith('error:'):
            self._failed(f'Identification query rejected: {line[:32]}')
        elif line.startswith('[') and not line.startswith('[MSG:'):
            if len(self.lines) >= MAX_EVIDENCE_LINES or len(line) > MAX_TEXT or any(
                    not 32 <= ord(char) <= 126 for char in line):
                self.invalid = 'Identification evidence exceeds 32 printable lines of 256 bytes'
            else:
                self.lines.append(line)
        elif line.startswith('$'):
            self._failed('Settings evidence arrived out of order during identification', lost=True)
        else:
            return False
        return True

    def expire(self, now: float) -> None:
        if self.pending and now - self.sent_at >= IDENTIFY_TIMEOUT:
            self._failed('Firmware identification timed out', lost=True)

    def on_banner(self, line: str) -> bool:
        """Record a reset greeting; return True when identification must run again."""
        self.banner = line[:MAX_TEXT] if all(32 <= ord(char) <= 126 for char in line) else ''
        identified = self.observation.phase is IdentificationPhase.IDENTIFIED
        if not self.pending and identified and banner_consistent(self.observation.capabilities, line):
            self.observation = replace(self.observation, banner=self.banner)
            self.publish()
            return False
        self.sent_at = None
        self.observation = FirmwareObservation(
            IdentificationPhase.FAILED, capabilities_for(FirmwareFamily.UNKNOWN), self.banner,
            diagnostic='Controller restarted; firmware identity must be verified again')
        self.publish()
        return True

    def _finish(self) -> None:
        if self.invalid:
            self._failed(self.invalid)
            return
        evidence = tuple(self.lines)
        capabilities = identify(self.banner, evidence)
        known = capabilities.family is not FirmwareFamily.UNKNOWN
        self.sent_at = None
        self.observation = FirmwareObservation(
            IdentificationPhase.IDENTIFIED if known else IdentificationPhase.FAILED, capabilities,
            self.banner, evidence, '' if known else capabilities.note)
        self.publish()

    def _failed(self, message: str, *, lost: bool = False) -> None:
        self.sent_at = None
        self.observation = FirmwareObservation(
            IdentificationPhase.FAILED, capabilities_for(FirmwareFamily.UNKNOWN), self.banner,
            tuple(self.lines[:MAX_EVIDENCE_LINES]), message[:MAX_TEXT])
        self.publish()
        if lost:
            self.host._settings_sent_at = None
            self.host._invalidate(clear_units=True)
            self.host._diagnose(f'{message}; reconnect to verify firmware and settings')
