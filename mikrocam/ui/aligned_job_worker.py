"""Cooperative aligned-job preparation off GUI and communication threads."""
from threading import Event

from PyQt6 import QtCore

from mikrocam.core.aligned_job import prepare_aligned_job
from mikrocam.core.gcode_models import PreflightCancelled, PreflightReport, SourceSnapshot


class AlignedJobWorker(QtCore.QThread):
    completed = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    cancelled = QtCore.pyqtSignal()

    def __init__(self, source: SourceSnapshot, report: PreflightReport, g54_xy: tuple[float, float],
                 chord_error_mm: float, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.source, self.report = source, report
        self.g54_xy, self.chord_error_mm = g54_xy, chord_error_mm
        self._cancel = Event()

    def cancel(self) -> None:
        self._cancel.set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> None:
        try:
            if self.is_cancelled():
                raise PreflightCancelled('Aligned job preparation cancelled')
            result = prepare_aligned_job(self.source, self.report, self.g54_xy,
                                         chord_error_mm=self.chord_error_mm, cancelled=self.is_cancelled)
            if self.is_cancelled():
                raise PreflightCancelled('Aligned job preparation cancelled before delivery')
            self.completed.emit(result)
        except PreflightCancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error)[:256])
