"""Reviewed fixed-plane dry-run dock; all execution uses the existing Machine handoff."""
import builtins
from collections.abc import Callable
import gettext
from io import StringIO
from itertools import islice
import math

from PyQt6 import QtCore, QtGui, QtWidgets

from mikrocam.core.dry_run import DryRunResult
from mikrocam.core.gcode_models import PreflightReport, SourceSnapshot
from .dry_run_worker import DryRunWorker


_ = getattr(builtins, '_', gettext.gettext)
JOIN_TIMEOUT_MS = 2000
PREVIEW_LINES = 200
Binding = tuple[SourceSnapshot, PreflightReport]


class DryRunPanel(QtWidgets.QDockWidget):
    reviewed_changed = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None, *, source: SourceSnapshot,
                 report: PreflightReport, binding_provider: Callable[[], Binding | None] | None = None,
                 job_receiver: Callable | None = None) -> None:
        super().__init__(_('XY dry run'), parent)
        self.setObjectName('MikroCAMDryRunPanel')
        self.job_receiver = job_receiver
        self.source = self.original_report = None
        self.result: DryRunResult | None = None
        self._worker: DryRunWorker | None = None
        self._generation = self._worker_generation = 0
        self._cancel_notice_generation = None
        self._alive = self._original_valid = True
        self._binding_provider = self._binding_origin = None
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
            'Choose an explicit machine Z for XY air-cut. Clearance is declared, not measured. '
            'The first upward retract also needs a clear path. Physical spindle stopping and '
            'interlocks are not verified by this preview.'))
        caveat.setWordWrap(True)
        layout.addWidget(caveat)
        self.height_edit = QtWidgets.QLineEdit()
        self.height_edit.setPlaceholderText(_('Required machine Z in mm'))
        self.height_edit.textChanged.connect(self._height_changed)
        form = QtWidgets.QFormLayout()
        form.addRow(_('Dry plane: machine Z (mm)'), self.height_edit)
        layout.addLayout(form)
        actions = QtWidgets.QHBoxLayout()
        self.prepare_button = QtWidgets.QPushButton(_('Prepare dry job'))
        self.cancel_button = QtWidgets.QPushButton(_('Cancel'))
        self.transfer_button = QtWidgets.QPushButton(_('Load reviewed dry job into Machine'))
        self.prepare_button.clicked.connect(self.prepare)
        self.cancel_button.clicked.connect(self.cancel)
        self.transfer_button.clicked.connect(self.transfer)
        for button in (self.prepare_button, self.cancel_button, self.transfer_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.summary_label = QtWidgets.QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.summary_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.summary_label)
        self.preview_table = QtWidgets.QTableWidget(0, 3)
        self.preview_table.setHorizontalHeaderLabels([_('Dry line'), _('Original line'), _('Preview')])
        self.preview_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.preview_table, 1)
        self.setWidget(content)

    @property
    def busy(self) -> bool:
        return self._worker is not None

    def _sync_controls(self) -> None:
        self.prepare_button.setEnabled(self._alive and self._original_valid and not self.busy)
        self.cancel_button.setEnabled(self.busy)
        self.transfer_button.setEnabled(self._alive and self._original_valid and self.result is not None
                                        and not self.busy and self.job_receiver is not None)

    def _invalidate(self, message: str) -> None:
        self._generation += 1
        self._cancel_notice_generation = None
        self.result = None
        self.preview_table.setRowCount(0)
        if self._worker is not None:
            self._worker.cancel()
        self.summary_label.setText(message)
        self._sync_controls()
        self.reviewed_changed.emit()

    def _height_changed(self) -> None:
        self._invalidate(_('Dry height changed. Prepare and review a new dry job.'))

    def set_source(self, source: SourceSnapshot, report: PreflightReport,
                   binding_provider: Callable[[], Binding | None] | None = None) -> None:
        if (not isinstance(source, SourceSnapshot) or not isinstance(report, PreflightReport)
                or not report.allowed or source.name != report.source_name or source.sha256 != report.source_sha256):
            raise ValueError(_('Dry run requires an exact successful original preflight.'))
        changed = (source, report) != (self.source, self.original_report)
        if self._binding_origin is not None:
            try:
                self._binding_origin.reviewed_changed.disconnect(self._refresh_original)
            except (TypeError, RuntimeError):
                pass
        self.source, self.original_report = source, report
        self._binding_provider = binding_provider
        self._binding_origin = getattr(binding_provider, '__self__', None)
        if self._binding_origin is not None and hasattr(self._binding_origin, 'reviewed_changed'):
            self._binding_origin.reviewed_changed.connect(self._refresh_original)
        self._alive = self._original_valid = True
        if changed:
            self.height_edit.clear()
        self._invalidate(_('Original snapshot: {name}\nSHA-256: {digest}\nEnter an explicit dry plane.').format(
            name=source.name, digest=source.sha256))
        self._refresh_original()

    def _refresh_original(self) -> bool:
        try:
            valid = (self._binding_provider is None
                     or self._binding_provider() == (self.source, self.original_report))
        except Exception:
            valid = False
        if not valid and self._original_valid:
            self._original_valid = False
            self._invalidate(_('Original preflight changed or closed. Reopen from a current reviewed source.'))
        return valid and self._original_valid

    def _height(self) -> float:
        try:
            height = float(self.height_edit.text().strip())
        except ValueError as error:
            raise ValueError(_('Enter the dry plane explicitly in mm.')) from error
        if not math.isfinite(height):
            raise ValueError(_('Dry plane must be finite.'))
        return height

    def prepare(self) -> None:
        if not self._alive or self.busy or not self._refresh_original():
            return
        try:
            height = self._height()
        except ValueError as error:
            self._invalidate(str(error))
            return
        self._invalidate(_('Preparing a separate reviewed dry snapshot…'))
        worker = DryRunWorker(self.source, self.original_report, height, self)
        self._worker, self._worker_generation = worker, self._generation
        worker.completed.connect(self._completed, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.failed.connect(self._failed, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.cancelled.connect(self._cancelled, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(self._finished, QtCore.Qt.ConnectionType.QueuedConnection)
        self._sync_controls()
        worker.start()

    def cancel(self) -> None:
        if self._worker is not None:
            self._invalidate(_('Cancelling dry preparation…'))
            self._cancel_notice_generation = self._generation

    def _current_result(self) -> bool:
        return (self._worker is not None and self.sender() is self._worker
                and not self._worker.is_cancelled() and self._worker_generation == self._generation
                and self._refresh_original())

    def _completed(self, result: DryRunResult) -> None:
        if not self._current_result():
            return
        if (not isinstance(result, DryRunResult) or result.original_source != self.source
                or result.original_report != self.original_report or result.dry_z_mm != self._height()):
            self._invalidate(_('Dry preparation returned mismatched source or height.'))
            return
        self.result = result
        self._render_result(result)
        self._sync_controls()

    def _render_result(self, result: DryRunResult) -> None:
        job = result.prepared_job
        duration = _('Unknown') if job.report.duration_seconds is None else f'{job.report.duration_seconds:.6g} s'
        self.summary_label.setText(_('Original: {original}\nOriginal SHA-256: {original_hash}\n'
            'Dry snapshot: {derived}\nDry SHA-256: {derived_hash}\nMachine dry Z: {height:.12g} mm\n'
            'Derived bounds (mm): {bounds}\nNominal duration: {duration}\n'
            'Preview: first {limit} of {total} lines; generated lines have no original line.\n'
            'Declared clearance only; no physical stop, fixture clearance or permission to run is verified.').format(
                original=result.original_source.name, original_hash=result.original_source.sha256,
                derived=job.source.name, derived_hash=job.source.sha256, height=result.dry_z_mm,
                bounds=job.report.bounds_mm, duration=duration, limit=PREVIEW_LINES, total=len(result.lineage)))
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
            self.summary_label.setText(_('Dry job transfer failed: ') + str(error)[:256])

    def _failed(self, message: str) -> None:
        if self._current_result():
            self.summary_label.setText(_('Dry preparation failed: ') + _(message))

    def _cancelled(self) -> None:
        if self.sender() is self._worker and self._cancel_notice_generation == self._generation:
            self.summary_label.setText(_('Dry preparation cancelled.'))

    def _finished(self) -> None:
        self._release_worker(self.sender())

    def _release_worker(self, expected: QtCore.QObject, timeout: int = JOIN_TIMEOUT_MS) -> bool:
        worker = self._worker
        if worker is None or worker is not expected:
            return worker is None
        if not worker.wait(timeout):
            self.summary_label.setText(_('Dry preparation is still stopping; keep this window open.'))
            return False
        if worker.is_cancelled() and self._cancel_notice_generation == self._generation:
            self.summary_label.setText(_('Dry preparation cancelled.'))
        self._worker = None
        worker.deleteLater()
        self._sync_controls()
        return True

    def shutdown(self, timeout: int = JOIN_TIMEOUT_MS) -> bool:
        self._alive = False
        self._refresh_timer.stop()
        self._invalidate(_('Dry review closed. Prepare again before transfer.'))
        return self._worker is None or self._release_worker(self._worker, timeout)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if not self.shutdown():
            event.ignore()
            return
        super().closeEvent(event)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        self._alive = True
        self._refresh_timer.start()
        self._refresh_original()
        self._sync_controls()
        super().showEvent(event)
