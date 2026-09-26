"""One Qt worker owns controller creation, every I/O call and final resource release."""
from collections.abc import Callable
from dataclasses import replace
from threading import Event

from PyQt6 import QtCore

from mikrocam.machine.controller import MachineController
from mikrocam.machine.models import ConnectionState, MachineSnapshot


class MachineWorker(QtCore.QThread):
    snapshot_ready = QtCore.pyqtSignal(object)

    def __init__(self, factory: Callable[[], MachineController],
                 parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._factory = factory
        self._stop = Event()
        self.final_snapshot = MachineSnapshot()

    def stop(self) -> None:
        """Request closure safely without calling controller I/O from the GUI thread."""
        self._stop.set()

    def run(self) -> None:
        controller: MachineController | None = None
        failure: MachineSnapshot | None = None
        previous: MachineSnapshot | None = None
        try:
            if self._stop.is_set():
                return
            self.snapshot_ready.emit(MachineSnapshot(connection=ConnectionState.CONNECTING))
            controller = self._factory()
            if self._stop.is_set():
                return
            controller.connect()
            while not self._stop.is_set():
                snapshot = controller.snapshot()
                if snapshot != previous:
                    self.snapshot_ready.emit(snapshot)
                    previous = snapshot
                if snapshot.connection is ConnectionState.ERROR:
                    failure = snapshot
                    break
                controller.tick()
                if self._stop.wait(.02):
                    break
            snapshot = controller.snapshot()
            if snapshot.connection is ConnectionState.ERROR:
                failure = snapshot
        except Exception as error:
            failure = MachineSnapshot(connection=ConnectionState.ERROR, diagnostic=str(error)[:256])
        finally:
            final = MachineSnapshot()
            if controller is not None:
                try:
                    controller.disconnect()
                    final = controller.snapshot()
                except Exception as error:
                    final = MachineSnapshot(connection=ConnectionState.ERROR,
                                            diagnostic=f'Disconnect failed: {error}'[:256])
            if failure is not None:
                if final.connection is ConnectionState.ERROR:
                    failure = replace(failure, diagnostic=(failure.diagnostic + '; ' + final.diagnostic)[:256])
                final = failure
            self.final_snapshot = final
            self.snapshot_ready.emit(final)
