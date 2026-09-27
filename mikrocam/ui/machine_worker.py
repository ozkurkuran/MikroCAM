"""One Qt worker owns controller creation, every I/O call and final resource release."""
from collections.abc import Callable
from dataclasses import replace
from threading import Event, Lock

from PyQt6 import QtCore

from mikrocam.machine.controller import MachineController
from mikrocam.machine.manual_models import JogRequest, ZeroRequest, SelectG54Request
from mikrocam.machine.models import ConnectionState, MachineSnapshot


class MachineWorker(QtCore.QThread):
    snapshot_ready = QtCore.pyqtSignal(object)

    def __init__(self, factory: Callable[[], MachineController],
                 parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._factory = factory
        self._stop = Event()
        self._cancel = Event()
        self._abort = Event()
        self._lock = Lock()
        self._pending = None
        self._admission_open = False
        self._latest = MachineSnapshot()
        self.final_snapshot = MachineSnapshot()

    def submit(self, request: JogRequest | ZeroRequest | SelectG54Request) -> bool:
        """Reserve one intent slot; admission is rechecked by the communication owner."""
        flags = {JogRequest: 'can_jog', ZeroRequest: 'can_zero', SelectG54Request: 'can_select_g54'}
        if type(request) not in flags:
            return False
        with self._lock:
            if (self._interrupted() or not self._admission_open or self._pending is not None
                    or not getattr(self._latest.manual, flags[type(request)])):
                return False
            self._pending = request
            self._admission_open = False
            return True

    def _priority(self, event: Event) -> None:
        with self._lock:
            event.set()
            self._pending = None
            self._admission_open = False

    def cancel_jog(self) -> None:
        self._priority(self._cancel)

    def abort(self) -> None:
        self._priority(self._abort)

    def stop(self) -> None:
        """Request closure safely without calling controller I/O from the GUI thread."""
        self._priority(self._stop)

    def _interrupted(self) -> bool:
        return self._stop.is_set() or self._abort.is_set() or self._cancel.is_set()

    def _process_intent(self, controller: MachineController) -> None:
        with self._lock:
            if self._stop.is_set():
                return
            abort, cancel = self._abort.is_set(), self._cancel.is_set()
            self._abort.clear()
            self._cancel.clear()
            request, self._pending = self._pending, None
        if abort:
            controller.abort()
        elif cancel:
            controller.cancel_jog()
        elif request is not None:
            try:
                controller.request_manual(request)
            except ValueError:
                pass  # The controller publishes the rejected admission diagnostic.

    def _publish(self, snapshot: MachineSnapshot) -> None:
        with self._lock:
            changed = snapshot != self._latest
            self._latest = snapshot
            self._admission_open = (not self._interrupted() and self._pending is None
                                    and any((snapshot.manual.can_jog, snapshot.manual.can_zero,
                                             snapshot.manual.can_select_g54)))
        if changed:
            self.snapshot_ready.emit(snapshot)

    def run(self) -> None:
        controller: MachineController | None = None
        failure: MachineSnapshot | None = None
        try:
            if self._stop.is_set():
                return
            self.snapshot_ready.emit(MachineSnapshot(connection=ConnectionState.CONNECTING))
            controller = self._factory()
            if self._stop.is_set():
                return
            controller.set_interrupt_check(self._interrupted)
            controller.connect()
            while not self._stop.is_set():
                self._process_intent(controller)
                if self._stop.is_set():
                    break
                controller.tick()
                snapshot = controller.snapshot()
                self._publish(snapshot)
                if snapshot.connection is ConnectionState.ERROR:
                    failure = snapshot
                    break
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
            with self._lock:
                self._admission_open = False
                self._pending = None
                self._latest = final
            self.snapshot_ready.emit(final)
