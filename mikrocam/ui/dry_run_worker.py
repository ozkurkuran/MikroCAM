"""Cooperative pure dry-run preparation off GUI and communication threads."""
from threading import Event

from PyQt6 import QtCore

from mikrocam.core.dry_run import DryRunResult, prepare_dry_run
from mikrocam.core.gcode_models import PreflightCancelled, PreflightReport, SourceSnapshot


class DryRunWorker(QtCore.QThread):
    completed = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    cancelled = QtCore.pyqtSignal()

    def __init__(self, source: SourceSnapshot, report: PreflightReport, dry_z_mm: float,
                 parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.source, self.report, self.dry_z_mm = source, report, dry_z_mm
        self.final_result: DryRunResult | None = None
        self._cancel = Event()

    def cancel(self) -> None:
        self._cancel.set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> None:
        try:
            if self.is_cancelled():
                raise PreflightCancelled('Dry-run preparation cancelled')
            result = prepare_dry_run(self.source, self.report, self.dry_z_mm,
                                     cancelled=self.is_cancelled)
            if self.is_cancelled():
                raise PreflightCancelled('Dry-run preparation cancelled before delivery')
            self.final_result = result
            self.completed.emit(result)
        except PreflightCancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error)[:256])
