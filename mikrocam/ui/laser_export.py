"""Concrete export controls and one worker with an atomic publication boundary."""
import builtins
import gettext
from pathlib import Path
from threading import Event

from PyQt6 import QtCore, QtWidgets

from mikrocam.core.laser_paths import LaserPlan, PlanningCancelled
from mikrocam.laser.export import export_plan


_ = getattr(builtins, '_', gettext.gettext)


class ExportWorker(QtCore.QThread):
    """Read only immutable plan data; widgets are accessed exclusively by the controls."""
    def __init__(self, plan: LaserPlan, destination: Path, format: str,
                 parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.plan, self.destination, self.format = plan, destination, format
        self.saved_path: Path | None = None
        self.error: str | None = None
        self.cancelled_before_commit = False
        self._cancel = Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        try:
            # Returning means os.replace committed; a later cancel cannot undo success.
            self.saved_path = Path(export_plan(self.plan, self.destination, self.format, self._cancel.is_set))
        except PlanningCancelled:
            self.cancelled_before_commit = True
        except Exception as error:
            self.error = str(error)


class LaserExportControls(QtWidgets.QWidget):
    status_changed = QtCore.pyqtSignal(str)
    busy_changed = QtCore.pyqtSignal(bool)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._plan: LaserPlan | None = None
        self._worker: ExportWorker | None = None
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel(_('Export format')))
        self.format_combo = QtWidgets.QComboBox()
        self.format_combo.addItem(_('SVG'), 'svg')
        self.format_combo.addItem(_('DXF'), 'dxf')
        layout.addWidget(self.format_combo)
        self.export_button = QtWidgets.QPushButton(_('Export ZIP'))
        self.export_button.clicked.connect(self.export_zip)
        self.export_button.setEnabled(False)
        layout.addWidget(self.export_button)
        QtWidgets.QApplication.instance().aboutToQuit.connect(self.shutdown)

    @property
    def busy(self) -> bool:
        return self._worker is not None

    def set_plan(self, plan: LaserPlan | None) -> None:
        """Supply only a current successful plan; invalidation cancels an active export."""
        if plan is not None and not isinstance(plan, LaserPlan):
            raise ValueError(_('Export requires a valid laser plan.'))
        if self.busy:
            self.cancel()
        self._plan = plan
        self._update_controls()

    def _update_controls(self) -> None:
        self.export_button.setEnabled(self._plan is not None and not self.busy)
        self.format_combo.setEnabled(not self.busy)

    def export_zip(self) -> None:
        """Choose a destination on GUI, then export one immutable snapshot off GUI."""
        if self.busy or self._plan is None or not self.isEnabled():
            return
        plan, format = self._plan, self.format_combo.currentData()
        filename, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, _('Export laser plan'), '', _('ZIP packages (*.zip)'))
        if not filename:
            return
        # The modal dialog can process other GUI events: recheck eligibility afterwards.
        if self.busy or self._plan is not plan or not self.isEnabled():
            return
        worker = ExportWorker(plan, Path(filename), format, self)
        self._worker = worker
        worker.finished.connect(self._finished, QtCore.Qt.ConnectionType.QueuedConnection)
        self._update_controls()
        self.busy_changed.emit(True)
        self.status_changed.emit(_('Exporting {format}…').format(format=worker.format.upper()))
        worker.start()

    def cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.status_changed.emit(_('Cancelling export…'))

    def _finished(self) -> None:
        self._release_worker(self.sender())

    def _release_worker(self, expected: QtCore.QObject) -> None:
        worker = self._worker
        if worker is None or expected is not worker:
            return
        self._worker = None
        if worker.saved_path is not None:
            status = _('Saved: {path} ({format})').format(path=worker.saved_path, format=worker.format.upper())
        elif worker.cancelled_before_commit:
            status = _('Cancelled export. No output was published.')
        else:
            status = _('Error exporting {format} to {path}: {message}').format(
                format=worker.format.upper(), path=worker.destination, message=_(worker.error or 'Unknown error'))
        worker.deleteLater()
        self._update_controls()
        self.status_changed.emit(status)
        self.busy_changed.emit(False)

    def shutdown(self) -> None:
        """Join before destruction; report committed output even with a queued finish signal."""
        if self._worker is not None:
            self.cancel()
            self._worker.wait()
            self._release_worker(self._worker)
