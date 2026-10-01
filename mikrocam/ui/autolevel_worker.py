"""Cooperative pure compensation away from the GUI and machine owner."""
from threading import Event
from PyQt6 import QtCore
from mikrocam.core.autolevel import prepare_autolevel, AutoLevelResult
from mikrocam.core.autolevel_surface import AutoLevelSettings
from mikrocam.core.gcode_models import SourceSnapshot, PreflightReport, PreflightCancelled


class AutoLevelWorker(QtCore.QThread):
    completed=QtCore.pyqtSignal(object)
    failed=QtCore.pyqtSignal(str)
    cancelled=QtCore.pyqtSignal()

    def __init__(self, source: SourceSnapshot, report: PreflightReport, settings: AutoLevelSettings,
                 parent: QtCore.QObject | None=None) -> None:
        super().__init__(parent)
        self.source,self.report,self.settings=source,report,settings
        self.final_result: AutoLevelResult | None=None
        self._cancel=Event()

    def cancel(self) -> None:
        self._cancel.set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> None:
        try:
            result=prepare_autolevel(self.source,self.report,self.settings,cancelled=self.is_cancelled)
            if self.is_cancelled():raise PreflightCancelled('Auto-level delivery cancelled')
            self.final_result=result;self.completed.emit(result)
        except PreflightCancelled:self.cancelled.emit()
        except Exception as error:self.failed.emit(str(error)[:512])
