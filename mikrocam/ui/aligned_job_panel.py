"""Reviewed fiducial-aligned job dock; execution uses the existing Machine and dry-run handoffs."""
import builtins
from collections.abc import Callable
import gettext
from io import StringIO
from itertools import islice

from PyQt6 import QtCore, QtGui, QtWidgets

from mikrocam.core.aligned_job import AlignedJobResult
from mikrocam.core.gcode_models import PreflightReport, SourceSnapshot
from mikrocam.machine.fiducial_capture import capture_work_offset_xy
from .aligned_job_worker import AlignedJobWorker
from .dry_run_panel import DryRunPanel


_ = getattr(builtins, '_', gettext.gettext)
JOIN_TIMEOUT_MS = 2000
PREVIEW_LINES = 200
DEFAULT_CHORD_MM = '0.005'
Binding = tuple[SourceSnapshot, PreflightReport]


class AlignedJobPanel(QtWidgets.QDockWidget):
    reviewed_changed = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None, *, source: SourceSnapshot,
                 report: PreflightReport, binding_provider: Callable[[], Binding | None] | None = None,
                 job_receiver: Callable | None = None,
                 snapshot_provider: Callable[[], object] | None = None) -> None:
        super().__init__(_('Aligned job'), parent)
        self.setObjectName('MikroCAMAlignedJobPanel')
        self.job_receiver, self.snapshot_provider = job_receiver, snapshot_provider
        self.source = self.original_report = None
        self.result: AlignedJobResult | None = None
        self._worker: AlignedJobWorker | None = None
        self._generation = self._worker_generation = 0
        self._alive = self._original_valid = True
        self._binding_provider = None
        self._dry_run_panel: DryRunPanel | None = None
        self._build_ui()
        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.setInterval(500)
        self._refresh_timer.timeout.connect(self._refresh_original)
        self.set_source(source, report, binding_provider)
        self._refresh_timer.start()

    def _build_ui(self) -> None:
        content = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(content)
        caveat = QtWidgets.QLabel(_(
            'The reviewed fiducial placement is written into XY coordinates of a separate G54 job; '
            'arcs become chords. Enter the controller G54 XY that will be active. Start verifies the '
            'live G54 again. Run the dry run before cutting; physical clearance is not verified.'))
        caveat.setWordWrap(True)
        layout.addWidget(caveat)
        form = QtWidgets.QFormLayout()
        self.g54_x_edit, self.g54_y_edit = QtWidgets.QLineEdit(), QtWidgets.QLineEdit()
        self.chord_edit = QtWidgets.QLineEdit(DEFAULT_CHORD_MM)
        for edit in (self.g54_x_edit, self.g54_y_edit, self.chord_edit):
            edit.textChanged.connect(lambda text: self._invalidate(_('Input changed. Prepare again.')))
        self.g54_x_edit.setPlaceholderText(_('Required'))
        self.g54_y_edit.setPlaceholderText(_('Required'))
        form.addRow(_('G54 X (mm)'), self.g54_x_edit)
        form.addRow(_('G54 Y (mm)'), self.g54_y_edit)
        form.addRow(_('Arc chord tolerance (mm)'), self.chord_edit)
        layout.addLayout(form)
        actions = QtWidgets.QHBoxLayout()
        self.use_machine_button = QtWidgets.QPushButton(_('Use machine G54 XY'))
        self.prepare_button = QtWidgets.QPushButton(_('Prepare aligned job'))
        self.cancel_button = QtWidgets.QPushButton(_('Cancel'))
        self.transfer_button = QtWidgets.QPushButton(_('Load aligned job into Machine'))
        self.dry_run_button = QtWidgets.QPushButton(_('Dry run aligned job'))
        for button, slot in ((self.use_machine_button, self.use_machine_g54), (self.prepare_button, self.prepare),
                             (self.cancel_button, self.cancel), (self.transfer_button, self.transfer),
                             (self.dry_run_button, self.open_dry_run)):
            button.clicked.connect(slot)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.summary_label = QtWidgets.QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.summary_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.summary_label)
        self.preview_table = QtWidgets.QTableWidget(0, 3)
        self.preview_table.setHorizontalHeaderLabels([_('Aligned line'), _('Original line'), _('Preview')])
        self.preview_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.preview_table, 1)
        self.setWidget(content)

    @property
    def busy(self) -> bool:
        return self._worker is not None

    def _sync_controls(self) -> None:
        ready = self._alive and self._original_valid and not self.busy
        self.prepare_button.setEnabled(ready)
        self.cancel_button.setEnabled(self.busy)
        self.use_machine_button.setEnabled(ready and self.snapshot_provider is not None)
        done = ready and self.result is not None
        self.transfer_button.setEnabled(done and self.job_receiver is not None)
        self.dry_run_button.setEnabled(done)

    def _invalidate(self, message: str) -> None:
        self._generation += 1
        self.result = None
        self.preview_table.setRowCount(0)
        if self._worker is not None:
            self._worker.cancel()
        self.summary_label.setText(message)
        self._sync_controls()
        self.reviewed_changed.emit()

    def set_source(self, source: SourceSnapshot, report: PreflightReport,
                   binding_provider: Callable[[], Binding | None] | None = None) -> None:
        if (not isinstance(source, SourceSnapshot) or not isinstance(report, PreflightReport)
                or not report.allowed or source.sha256 != report.source_sha256):
            raise ValueError(_('Aligned job requires an exact successful original preflight.'))
        self.source, self.original_report = source, report
        self._binding_provider = binding_provider
        self._alive = self._original_valid = True
        self._invalidate(_('Original snapshot: {name}\nSHA-256: {digest}\nPlacement matrix: {matrix}').format(
            name=source.name, digest=source.sha256,
            matrix=', '.join(f'{v:.9g}' for v in report.setup.placement.matrix)))
        self._refresh_original()

    def _refresh_original(self) -> bool:
        try:
            valid = (self._binding_provider is None
                     or self._binding_provider() == (self.source, self.original_report))
        except Exception:
            valid = False
        if not valid and self._original_valid:
            self._original_valid = False
            self._invalidate(_('Original preflight changed or closed. Reopen from a current review.'))
        return valid and self._original_valid

    def use_machine_g54(self) -> None:
        try:
            if self.snapshot_provider is None:
                raise ValueError(_('Open and connect the Machine panel first'))
            x, y = capture_work_offset_xy(self.snapshot_provider())
        except ValueError as error:
            self.summary_label.setText(_('Machine G54 unavailable: ') + str(error))
            return
        self.g54_x_edit.setText(format(x, '.10g'))
        self.g54_y_edit.setText(format(y, '.10g'))

    def _inputs(self) -> tuple[tuple[float, float], float]:
        try:
            g54 = (float(self.g54_x_edit.text().strip()), float(self.g54_y_edit.text().strip()))
            chord = float(self.chord_edit.text().strip())
        except ValueError as error:
            raise ValueError(_('Enter G54 X/Y and chord tolerance explicitly in mm.')) from error
        return g54, chord

    def prepare(self) -> None:
        if not self._alive or self.busy or not self._refresh_original():
            return
        try:
            g54, chord = self._inputs()
        except ValueError as error:
            self._invalidate(str(error))
            return
        self._invalidate(_('Preparing a separate aligned job…'))
        worker = AlignedJobWorker(self.source, self.original_report, g54, chord, self)
        self._worker, self._worker_generation = worker, self._generation
        worker.completed.connect(self._completed, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.failed.connect(self._failed, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.cancelled.connect(self._cancelled, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(self._finished, QtCore.Qt.ConnectionType.QueuedConnection)
        self._sync_controls()
        worker.start()

    def cancel(self) -> None:
        if self._worker is not None:
            self._invalidate(_('Cancelling aligned preparation…'))

    def _current(self) -> bool:
        return (self._worker is not None and self.sender() is self._worker and not self._worker.is_cancelled()
                and self._worker_generation == self._generation and self._refresh_original())

    def _completed(self, result: AlignedJobResult) -> None:
        if not self._current():
            return
        if (not isinstance(result, AlignedJobResult) or result.original_source != self.source
                or result.original_report != self.original_report):
            self._invalidate(_('Aligned preparation returned a mismatched source.'))
            return
        self.result = result
        self._render(result)
        self._sync_controls()

    def _render(self, result: AlignedJobResult) -> None:
        job = result.prepared_job
        self.summary_label.setText(_(
            'Original: {original}\nAligned snapshot: {derived}\nAligned SHA-256: {digest}\n'
            'G54 offset (mm): {g54}\nChord tolerance: {chord:g} mm\nMachine bounds (mm): {bounds}\n'
            'Preview: first {limit} of {total} lines. Declared setup only; no physical check.').format(
                original=result.original_source.name, derived=job.source.name, digest=job.source.sha256,
                g54=result.g54_offset_mm, chord=result.chord_error_mm, bounds=job.report.bounds_mm,
                limit=PREVIEW_LINES, total=len(result.lineage)))
        self.preview_table.setRowCount(min(PREVIEW_LINES, len(result.lineage)))
        for row, (text, origin) in enumerate(zip(islice(StringIO(job.source.text), PREVIEW_LINES), result.lineage)):
            for column, value in enumerate((str(row + 1), _('Generated') if origin is None else str(origin),
                                             text.rstrip('\r\n'))):
                self.preview_table.setItem(row, column, QtWidgets.QTableWidgetItem(value))

    def reviewed_binding(self) -> Binding | None:
        if not self._alive or not self._refresh_original() or self.result is None or self.busy:
            return None
        job = self.result.prepared_job
        return job.source, job.report

    def transfer(self) -> None:
        binding = self.reviewed_binding()
        if binding is None or self.job_receiver is None:
            return
        try:
            self.job_receiver(*binding, self.reviewed_binding)
        except Exception as error:
            self.summary_label.setText(_('Aligned job transfer failed: ') + str(error)[:256])

    def open_dry_run(self) -> DryRunPanel | None:
        binding = self.reviewed_binding()
        if binding is None:
            return None
        if self._dry_run_panel is None:
            parent = self.parentWidget()
            self._dry_run_panel = DryRunPanel(parent or self, source=binding[0], report=binding[1],
                                              binding_provider=self.reviewed_binding, job_receiver=self.job_receiver)
            if isinstance(parent, QtWidgets.QMainWindow):
                parent.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self._dry_run_panel)
            else:
                self._dry_run_panel.setFloating(True)
        else:
            self._dry_run_panel.set_source(*binding, self.reviewed_binding)
            self._dry_run_panel.job_receiver = self.job_receiver
        self._dry_run_panel.show()
        self._dry_run_panel.raise_()
        return self._dry_run_panel

    def _failed(self, message: str) -> None:
        if self._current():
            self.summary_label.setText(_('Aligned preparation failed: ') + _(message))

    def _cancelled(self) -> None:
        if self.sender() is self._worker:
            self.summary_label.setText(_('Aligned preparation cancelled.'))

    def _finished(self) -> None:
        self._release_worker(self.sender())

    def _release_worker(self, expected: QtCore.QObject, timeout: int = JOIN_TIMEOUT_MS) -> bool:
        worker = self._worker
        if worker is None or worker is not expected:
            return worker is None
        if not worker.wait(timeout):
            self.summary_label.setText(_('Aligned preparation is still stopping; keep this window open.'))
            return False
        self._worker = None
        worker.deleteLater()
        self._sync_controls()
        return True

    def shutdown(self, timeout: int = JOIN_TIMEOUT_MS) -> bool:
        self._alive = False
        self._refresh_timer.stop()
        self._invalidate(_('Aligned review closed. Prepare again before transfer.'))
        dry_closed = self._dry_run_panel is None or self._dry_run_panel.shutdown(timeout)
        return dry_closed and (self._worker is None or self._release_worker(self._worker, timeout))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if not self.shutdown():
            event.ignore()
            return
        super().closeEvent(event)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        self._alive = True
        self._refresh_timer.start()
        self._refresh_original()
        super().showEvent(event)
