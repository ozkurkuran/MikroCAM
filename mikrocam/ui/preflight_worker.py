"""One cancellable offline analysis thread, owning only immutable core values."""
from threading import Event

from PyQt6 import QtCore

from mikrocam.core.gcode_models import (PreflightCancelled, PreflightReport, PreflightSetup,
                                      SourceSnapshot)
from mikrocam.core.gcode_preflight import analyze_gcode


class PreflightWorker(QtCore.QThread):
    completed = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    cancelled = QtCore.pyqtSignal()

    def __init__(self, source: SourceSnapshot, setup: PreflightSetup,
                 parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.source, self.setup = source, setup
        self._cancel = Event()
        self.final_report: PreflightReport | None = None

    def cancel(self) -> None:
        self._cancel.set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> None:
        try:
            if self.is_cancelled():
                raise PreflightCancelled('Preflight cancelled before analysis')
            report=analyze_gcode(self.source,self.setup,self.is_cancelled)
            if self.is_cancelled():
                raise PreflightCancelled('Preflight cancelled before delivery')
            self.final_report=report
            self.completed.emit(report)
        except PreflightCancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error)[:256])
