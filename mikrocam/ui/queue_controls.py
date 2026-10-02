"""Explicit ordered snapshot approval; all execution stays on MachineWorker."""
import builtins
import gettext
from PyQt6 import QtCore, QtWidgets
from mikrocam.core.cnc_job import PreparedJob
from mikrocam.machine.job_models import JobPhase, StreamingMode
from mikrocam.machine.models import MachineSnapshot, ConnectionState
from mikrocam.machine.queue_models import QueueDraft, QueuePhase, QueueResult

_ = getattr(builtins, "_", gettext.gettext)
_TERMINAL = (JobPhase.COMPLETE, JobPhase.FAILED, JobPhase.ABORTED)


class QueueControls(QtWidgets.QDialog):
    start_requested = QtCore.pyqtSignal(object)
    pause_requested = QtCore.pyqtSignal()
    resume_requested = QtCore.pyqtSignal()
    stop_requested = QtCore.pyqtSignal()

    def __init__(self, parent=None, candidate_validator=None):
        super().__init__(parent)
        self.setWindowTitle(_("Job queue — prepared snapshots"))
        self.resize(820, 560)
        self.draft = QueueDraft()
        self.candidate = None
        self._validator = candidate_validator or (lambda job: True)
        self._snapshot = MachineSnapshot()
        self._pending_keys = ()
        layout = QtWidgets.QVBoxLayout(self)
        explanation = QtWidgets.QLabel(_(
            "Add reviewed jobs as immutable snapshots. Each initial position must match the "
            "previous endpoint; no repositioning is generated. After Start, suitable jobs advance "
            "automatically. Tool/fixture changes require separate runs."))
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.candidate_label = QtWidgets.QLabel()
        self.candidate_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.candidate_label.setWordWrap(True)
        layout.addWidget(self.candidate_label)
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([_("Source snapshot"), _("State"), _("Accepted"), _("Result")])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._update_actions)
        layout.addWidget(self.table)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem(_('Send-response (default)'), StreamingMode.SEND_RESPONSE)
        self.mode_combo.addItem(_('Character counting (GRBL 1.1, verified RX)'), StreamingMode.CHARACTER_COUNTING)
        self.mode_combo.setToolTip(_('One sending mode for the approved queue; acceptance is not motion completion.'))
        layout.addWidget(self.mode_combo)
        self._setup_actions(layout)
        self.confirm = QtWidgets.QCheckBox(_(
            "For this whole queue: mechanical spindle only, no laser on spindle/PWM; all jobs "
            "are ready on the same setup without tool/fixture intervention. Following jobs start automatically."))
        self.confirm.toggled.connect(self._update_actions)
        layout.addWidget(self.confirm)
        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        layout.addWidget(self.status_label)
        self._render()

    def _setup_actions(self, layout):
        edits = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton(_("Add prepared job"))
        self.up_button = QtWidgets.QPushButton(_("Move up"))
        self.down_button = QtWidgets.QPushButton(_("Move down"))
        self.remove_button = QtWidgets.QPushButton(_("Remove"))
        self.clear_button = QtWidgets.QPushButton(_("Clear waiting"))
        for button in (self.add_button, self.up_button, self.down_button, self.remove_button, self.clear_button):
            edits.addWidget(button)
        self.add_button.clicked.connect(self._add)
        self.up_button.clicked.connect(lambda: self._move(-1))
        self.down_button.clicked.connect(lambda: self._move(1))
        self.remove_button.clicked.connect(self._remove)
        self.clear_button.clicked.connect(self._clear)
        layout.addLayout(edits)
        actions = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton(_("Start approved queue"))
        self.pause_button = QtWidgets.QPushButton(_("Hold queue"))
        self.resume_button = QtWidgets.QPushButton(_("Resume queue"))
        self.stop_button = QtWidgets.QPushButton(_("Stop queue"))
        for button in (self.start_button, self.pause_button, self.resume_button, self.stop_button):
            actions.addWidget(button)
        self.start_button.clicked.connect(self._start)
        self.pause_button.clicked.connect(self.pause_requested)
        self.resume_button.clicked.connect(self.resume_requested)
        self.stop_button.clicked.connect(self.stop_requested)
        layout.addLayout(actions)

    def set_candidate(self, job):
        if job is not None and type(job) is not PreparedJob:
            raise ValueError("A validated prepared candidate is required")
        self.candidate = job
        self.candidate_label.setText(_("No prepared candidate. Transfer a reviewed preflight result.")
            if job is None else f"{job.source.name}\nSHA-256: {job.source.sha256}")
        self._update_actions()

    def _add(self):
        job = self.candidate
        if not self.add_button.isEnabled() or job is None:
            return
        if not self._validator(job):
            self.status_label.setText(_("Candidate changed. Transfer a current reviewed result before Add."))
            return
        self.draft.add(job)
        self.confirm.setChecked(False)
        self._render()

    def _selected(self):
        item = self.table.item(self.table.currentRow(), 0)
        key = None if item is None else item.data(QtCore.Qt.ItemDataRole.UserRole)
        return next((e for e in self.draft.entries if e.key == key), None)

    def _move(self, offset):
        entry = self._selected()
        if entry is None or self.draft.locked:
            return
        index = self.draft.entries.index(entry) + offset
        if 0 <= index < len(self.draft.entries):
            self.draft.move(entry.key, index)
            self.confirm.setChecked(False)
            self._render()

    def _remove(self):
        entry = self._selected()
        if entry is not None and not self.draft.locked:
            self.draft.remove(entry.key)
            self.confirm.setChecked(False)
            self._render()

    def _clear(self):
        if not self.draft.locked:
            self.draft.clear()
            self.confirm.setChecked(False)
            self._render()

    def _start(self):
        if not self.start_button.isEnabled():
            return
        request = self.draft.start_request(self.confirm.isChecked(), self.mode_combo.currentData())
        self._pending_keys = tuple(e.key for e in request.entries)
        self.confirm.setChecked(False)
        self.status_label.setText(_("Queue requested; waiting for owner admission."))
        self._update_actions()
        self.start_requested.emit(request)

    def start_rejected(self, diagnostic):
        self._pending_keys = ()
        self.draft.unlock()
        self.confirm.setChecked(False)
        self.status_label.setText(_(diagnostic))
        self._update_actions()

    def update_snapshot(self, snapshot):
        if snapshot.connection is not self._snapshot.connection:
            self.confirm.setChecked(False)
        self._snapshot = snapshot
        queue = snapshot.queue
        admitted = tuple(r.entry.key for r in queue.entries) == self._pending_keys
        if self._pending_keys and admitted:
            self._pending_keys = ()
        if queue.can_stop:
            self.draft.locked = True
        elif (not self._pending_keys and queue.phase in
              (QueuePhase.COMPLETE, QueuePhase.FAILED, QueuePhase.ABORTED)):
            self.draft.settle(queue)
        self.status_label.setText(f"{_(queue.phase.value)}: {_(queue.diagnostic)}")
        self._render()

    def _render(self):
        queue = self._snapshot.queue
        rows = queue.entries if queue.can_stop else (
            tuple(r for r in queue.entries if r.job.phase in _TERMINAL)
            + tuple(QueueResult(e) for e in self.draft.entries))
        self.table.setRowCount(len(rows))
        for row, result in enumerate(rows):
            entry, job = result.entry, result.job
            source = QtWidgets.QTableWidgetItem(f"[{entry.key}] {entry.job.source.name}")
            source.setData(QtCore.Qt.ItemDataRole.UserRole, entry.key)
            source.setToolTip(f"SHA-256: {entry.job.source.sha256}\n"
                              f"Initial: {entry.job.initial_machine_mm}\nFinal: {entry.job.final_machine_mm}\n"
                              f"G54: {entry.job.g54_offset_mm}")
            values = (source, QtWidgets.QTableWidgetItem(_(job.phase.value)),
                      QtWidgets.QTableWidgetItem(f"{job.acknowledged}/{len(entry.job.blocks)}"),
                      QtWidgets.QTableWidgetItem(_(job.diagnostic)))
            for column, item in enumerate(values):
                self.table.setItem(row, column, item)
        if hasattr(self, "confirm"):
            self._update_actions()

    def _update_actions(self, *_):
        if not hasattr(self, "confirm"):
            return
        editable = not self.draft.locked and not self._pending_keys
        entry = self._selected()
        index = self.draft.entries.index(entry) if entry is not None else -1
        self.add_button.setEnabled(editable and self.candidate is not None and len(self.draft.entries) < 32)
        self.up_button.setEnabled(editable and index > 0)
        self.down_button.setEnabled(editable and 0 <= index < len(self.draft.entries) - 1)
        self.remove_button.setEnabled(editable and entry is not None)
        self.clear_button.setEnabled(editable and bool(self.draft.entries))
        self.confirm.setEnabled(editable)
        self.mode_combo.setEnabled(editable)
        queue = self._snapshot.queue
        self.start_button.setEnabled(editable and bool(self.draft.entries)
                                     and self.confirm.isChecked() and queue.can_start)
        self.pause_button.setEnabled(queue.can_pause and not self._pending_keys)
        self.resume_button.setEnabled(queue.can_resume and not self._pending_keys)
        self.stop_button.setEnabled(queue.can_stop or bool(self._pending_keys))

    def closeEvent(self, event):
        if self.draft.locked or self._pending_keys:
            self.status_label.setText(_("Stop the queue before closing its active control window."))
            event.ignore()
        else:
            event.accept()

    def reject(self):
        if self.draft.locked or self._pending_keys:
            self.status_label.setText(_("Stop the queue before closing its active control window."))
            return
        super().reject()
