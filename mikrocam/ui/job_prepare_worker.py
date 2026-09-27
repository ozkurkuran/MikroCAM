"""Prepare reviewed immutable CNC input away from the GUI and serial owner."""
from threading import Event

from PyQt6 import QtCore

from mikrocam.core.cnc_job import PreparedJob
from mikrocam.core.gcode_models import PreflightCancelled, PreflightReport, SourceSnapshot


class JobPrepareWorker(QtCore.QThread):
    completed = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    cancelled = QtCore.pyqtSignal()

    def __init__(self, source: SourceSnapshot, report: PreflightReport,
                 parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.source, self.report = source, report
        self.final_job: PreparedJob | None = None
        self._cancel = Event()

    def cancel(self) -> None:
        self._cancel.set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> None:
        try:
            if self.is_cancelled():
                raise PreflightCancelled('Job preparation cancelled')
            job = PreparedJob(self.source, self.report, cancelled=self.is_cancelled)
            if self.is_cancelled():
                raise PreflightCancelled('Job preparation cancelled before delivery')
            self.final_job = job
            self.completed.emit(job)
        except PreflightCancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error)[:256])
