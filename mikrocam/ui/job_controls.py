"""Typed mechanical-job controls; no preparation, hardware or wire commands."""
import builtins
import gettext

from PyQt6 import QtCore, QtWidgets

from mikrocam.core.cnc_job import PreparedJob
from mikrocam.machine.job_models import JobPhase, StartJobRequest, StreamingMode
from mikrocam.machine.models import ConnectionState, MachineSnapshot


_ = getattr(builtins, '_', gettext.gettext)


class JobControls(QtWidgets.QWidget):
    start_requested = QtCore.pyqtSignal(object)
    pause_requested = QtCore.pyqtSignal()
    resume_requested = QtCore.pyqtSignal()
    stop_requested = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.prepared_job: PreparedJob | None = None
        self._snapshot = MachineSnapshot()
        self._worker_available = False
        self._pending = None
        layout = QtWidgets.QVBoxLayout(self)
        self.source_label = QtWidgets.QLabel(_('No reviewed job loaded.'))
        self.source_label.setWordWrap(True)
        self.source_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        layout.addWidget(self.source_label)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem(_('Send-response (default)'), StreamingMode.SEND_RESPONSE)
        self.mode_combo.addItem(_('Character counting (GRBL 1.1, verified RX)'), StreamingMode.CHARACTER_COUNTING)
        self.mode_combo.setToolTip(_('Buffered acceptance is not physical completion.'))
        layout.addWidget(self.mode_combo)
        self.confirm_checkbox = QtWidgets.QCheckBox(_(
            'For this Start: mechanical spindle only;\nno laser connected to spindle/PWM output.'))
        self.confirm_checkbox.toggled.connect(self._render)
        layout.addWidget(self.confirm_checkbox)
        actions = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton(_('Start job'))
        self.pause_button = QtWidgets.QPushButton(_('Pause job'))
        self.resume_button = QtWidgets.QPushButton(_('Resume job'))
        self.stop_button = QtWidgets.QPushButton(_('Stop job'))
        for button in (self.start_button, self.pause_button, self.resume_button, self.stop_button):
            actions.addWidget(button)
        self.start_button.clicked.connect(self._start)
        self.pause_button.clicked.connect(self.pause_requested)
        self.resume_button.clicked.connect(self.resume_requested)
        self.stop_button.clicked.connect(self.stop_requested)
        layout.addLayout(actions)
        self.progress_label = QtWidgets.QLabel()
        self.progress_label.setWordWrap(True)
        self.progress_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        layout.addWidget(self.progress_label)
        self._render()

    def set_job(self, job: PreparedJob | None) -> None:
        if job is not None and not isinstance(job, PreparedJob):
            raise ValueError(_('A prepared reviewed job is required.'))
        self.prepared_job = job
        self._pending = None
        self.reset_confirmation()
        self.source_label.setText(_('No reviewed job loaded.') if job is None else
                                  f'{job.source.name}\nSHA-256: {job.source.sha256}')
        self._render()

    def reset_confirmation(self) -> None:
        self.confirm_checkbox.setChecked(False)
        self._render()

    def set_pending(self) -> None:
        self._pending = self._snapshot.job
        self._render()

    def set_snapshot(self, snapshot: MachineSnapshot, worker_available: bool) -> None:
        if snapshot.connection is not self._snapshot.connection:
            self.reset_confirmation()
        self._snapshot, self._worker_available = snapshot, worker_available
        if snapshot.job != self._pending or not worker_available:
            self._pending = None
        self._render()

    def _start(self) -> None:
        if not self.start_button.isEnabled() or self.prepared_job is None:
            return
        request = StartJobRequest(self.prepared_job, self.confirm_checkbox.isChecked(), self.mode_combo.currentData())
        self.set_pending()
        self.reset_confirmation()
        self.start_requested.emit(request)

    def _render(self) -> None:
        observation = self._snapshot.job
        connected = self._worker_available and self._snapshot.connection is ConnectionState.CONNECTED
        available = connected and self._pending is None
        self.mode_combo.setEnabled(available and not observation.can_stop)
        self.start_button.setEnabled(available and observation.can_start
                                     and self.prepared_job is not None and self.confirm_checkbox.isChecked())
        self.confirm_checkbox.setEnabled(self.prepared_job is not None and observation.phase in (
            JobPhase.READY, JobPhase.COMPLETE, JobPhase.FAILED, JobPhase.ABORTED))
        self.pause_button.setEnabled(available and observation.can_pause)
        self.resume_button.setEnabled(available and observation.can_resume)
        self.stop_button.setEnabled(connected and observation.can_stop)
        text = _(observation.phase.value.capitalize())
        if observation.source_name:
            text += f': {observation.source_name}\nSHA-256: {observation.source_sha256}'
        text += '\n' + _('Accepted blocks: {done}/{total}; source line: {line}. '
                         'Acceptance is not physical completion. Pause does not promise outputs off.').format(
            done=observation.acknowledged, total=observation.total,
            line=observation.source_line if observation.source_line is not None else '—')
        if observation.diagnostic:
            text += '\n' + _(observation.diagnostic)
        if observation.stop_unverified:
            text += '\n' + _('Physical stop is unverified; use the machine safety procedure.')
        self.progress_label.setText(text)
