"""One cancellable Qt thread operating only on detached laser planning values."""
from threading import Event

from PyQt6 import QtCore

from mikrocam.core.laser_job import LaserJob
from mikrocam.core.laser_paths import CopperFeatures, PlanOptions, PlanningCancelled
from mikrocam.laser.planner import plan_laser


class LaserWorker(QtCore.QThread):
    completed = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    cancelled = QtCore.pyqtSignal()

    def __init__(self, job: LaserJob, options: PlanOptions, features: CopperFeatures,
                 parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.job, self.options, self.features = job, options, features
        self._cancel = Event()

    def cancel(self) -> None:
        """Cooperatively invalidate this request, including already calculated results."""
        self._cancel.set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> None:
        try:
            plan = plan_laser(self.job, self.options, self.features, self.is_cancelled)
            if self.is_cancelled():
                self.cancelled.emit()
            else:
                self.completed.emit(plan)
        except PlanningCancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error))
