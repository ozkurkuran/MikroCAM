"""Machine dock with bounded typed intents and GUI-owned snapshot presentation."""
import builtins
from collections.abc import Callable
import gettext
from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets

from mikrocam.bridge.machine import make_controller
from mikrocam.bridge.serial_transport import PortInfo, list_ports
from mikrocam.machine.controller import MachineController
from mikrocam.machine.manual_models import JogRequest, SelectG54Request, ZeroRequest
from mikrocam.machine.models import ConnectionState, MachineSnapshot, MachineState
from .machine_controls import MachineManualControls
from .machine_worker import MachineWorker


_ = getattr(builtins, '_', gettext.gettext)
JOIN_TIMEOUT_MS = 4000


class MachinePanel(QtWidgets.QDockWidget):
    def __init__(self, parent: QtWidgets.QMainWindow,
                 controller_factory: Callable[[str], MachineController] = make_controller,
                 ports_provider: Callable[[], tuple[PortInfo, ...]] = list_ports) -> None:
        super().__init__(_('Machine'), parent)
        self.setObjectName('mikrocam_machine_panel')
        self.controller_factory, self.ports_provider = controller_factory, ports_provider
        self._worker: MachineWorker | None = None
        self._stopping = False
        self.last_snapshot = MachineSnapshot()
        content = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(content)
        caveat = QtWidgets.QLabel(_('Opening a serial port may reset the controller. '
                                   'A reset can execute configured startup blocks. '
                                   'Disconnect closes communication; it does not stop external motion.'))
        caveat.setWordWrap(True)
        layout.addWidget(caveat)
        self.port_combo = QtWidgets.QComboBox(content)
        layout.addWidget(self.port_combo)
        actions = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton(_('Refresh ports'))
        self.connect_button = QtWidgets.QPushButton(_('Connect'))
        self.disconnect_button = QtWidgets.QPushButton(_('Disconnect'))
        for button in (self.refresh_button, self.connect_button, self.disconnect_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        form = QtWidgets.QFormLayout()
        self.connection_label, self.state_label = QtWidgets.QLabel(), QtWidgets.QLabel()
        form.addRow(_('Connection'), self.connection_label)
        form.addRow(_('Machine state'), self.state_label)
        self.machine_labels = self._position_row(form, _('Machine XYZ (mm)'))
        self.work_labels = self._position_row(form, _('Work XYZ (mm)'))
        layout.addLayout(form)
        self.status_label = QtWidgets.QLabel(content)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.manual_controls = MachineManualControls(content)
        self.manual_controls.requested.connect(self.submit_manual)
        self.manual_controls.cancel_requested.connect(self.cancel_manual_jog)
        self.manual_controls.abort_requested.connect(self.abort_machine)
        layout.addWidget(self.manual_controls)
        layout.addStretch()
        self.setWidget(content)
        self.refresh_button.clicked.connect(self.refresh_ports)
        self.connect_button.clicked.connect(self.connect_machine)
        self.disconnect_button.clicked.connect(self.disconnect_machine)
        self.port_combo.currentIndexChanged.connect(self._update_actions)
        QtWidgets.QApplication.instance().aboutToQuit.connect(self.shutdown)
        self._render_snapshot()
        self.refresh_ports()

    @property
    def busy(self) -> bool:
        return self._worker is not None

    def _position_row(self, form: QtWidgets.QFormLayout, title: str) -> tuple[QtWidgets.QLabel, ...]:
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        labels = tuple(QtWidgets.QLabel(_('Unavailable')) for _axis in range(3))
        for axis, label in zip(('X', 'Y', 'Z'), labels):
            layout.addWidget(QtWidgets.QLabel(axis))
            layout.addWidget(label)
        form.addRow(title, row)
        return labels

    def refresh_ports(self) -> None:
        """Enumerate metadata only; a live worker keeps its explicitly chosen port."""
        if self.busy:
            return
        selected = self.port_combo.currentData()
        self.port_combo.clear()
        try:
            for port in self.ports_provider():
                self.port_combo.addItem(f'{port.device} — {port.description}', port.device)
            index = self.port_combo.findData(selected)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)
        except Exception as error:
            self.status_label.setText(_('Port enumeration failed: ') + str(error)[:256])
        self._update_actions()

    def connect_machine(self) -> None:
        if self.busy or self.port_combo.currentData() is None:
            return
        port = self.port_combo.currentData()
        factory = self.controller_factory
        self._stopping = False
        self.last_snapshot = MachineSnapshot(connection=ConnectionState.CONNECTING)
        self._render_snapshot()
        self._worker = MachineWorker(lambda: factory(port), self)
        self._worker.snapshot_ready.connect(self._receive_snapshot, QtCore.Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(self._worker_finished, QtCore.Qt.ConnectionType.QueuedConnection)
        self._update_actions()
        self._worker.start()

    def disconnect_machine(self) -> None:
        """Ask the I/O owner to cancel/abort owned activity before bounded closure."""
        if self._worker is None:
            self.last_snapshot = MachineSnapshot()
            self._render_snapshot()
            self._update_actions()
            return
        self._stopping = True
        self._worker.stop()
        self.last_snapshot = MachineSnapshot()
        self._render_snapshot()
        self.status_label.setText(_('Closing communication…'))
        self._update_actions()

    @QtCore.pyqtSlot(object)
    def submit_manual(self, request: JogRequest | ZeroRequest | SelectG54Request) -> None:
        """Submit one typed intent; worker/domain gates remain authoritative."""
        worker = self._worker
        try:
            accepted = worker is not None and not self._stopping and worker.submit(request)
        except ValueError as error:
            self.status_label.setText(_('Manual request rejected: ') + str(error)[:256])
            return
        if accepted:
            self.manual_controls.set_pending()
        else:
            self.status_label.setText(_('Manual request rejected; connection or operation is unavailable'))

    def cancel_manual_jog(self) -> None:
        if self._worker is not None and not self._stopping:
            self._worker.cancel_jog()
            self.manual_controls.set_pending()

    def abort_machine(self) -> None:
        if self._worker is not None and not self._stopping:
            self._worker.abort()
            self.manual_controls.set_pending()

    @QtCore.pyqtSlot(object)
    def _receive_snapshot(self, snapshot: MachineSnapshot) -> None:
        if self.sender() is not self._worker or self._stopping:
            return
        self.last_snapshot = snapshot
        self._render_snapshot()

    @QtCore.pyqtSlot()
    def _worker_finished(self) -> None:
        if self.sender() is not self._worker:
            return
        self._release_worker()

    def _release_worker(self) -> None:
        worker = self._worker
        if worker is None:
            return
        if not worker.wait(JOIN_TIMEOUT_MS):
            self.status_label.setText(_('Communication is still closing; keep this window open.'))
            return
        self.last_snapshot = worker.final_snapshot
        self._worker = None
        worker.deleteLater()
        self._stopping = False
        self._render_snapshot()
        self._update_actions()

    def _update_actions(self) -> None:
        self.connect_button.setEnabled(not self.busy and self.port_combo.currentData() is not None)
        self.disconnect_button.setEnabled(self.busy or self.last_snapshot.connection is ConnectionState.ERROR)
        self.refresh_button.setEnabled(not self.busy)
        self.port_combo.setEnabled(not self.busy)

    def _render_snapshot(self) -> None:
        snapshot = self.last_snapshot
        connection = {ConnectionState.DISCONNECTED: _('Disconnected'), ConnectionState.CONNECTING: _('Connecting'),
                      ConnectionState.CONNECTED: _('Connected'), ConnectionState.ERROR: _('Error')}
        states = {MachineState.UNKNOWN: _('Unknown'), MachineState.IDLE: _('Idle'), MachineState.JOG: _('Jog'),
                  MachineState.RUNNING: _('Running'), MachineState.PAUSED: _('Paused'), MachineState.ALARM: _('Alarm'),
                  MachineState.HOMING: _('Homing'), MachineState.CHECK: _('Check'), MachineState.SLEEP: _('Sleep'),
                  MachineState.DOOR: _('Door'), MachineState.ERROR: _('Error')}
        self.connection_label.setText(connection[snapshot.connection])
        state = states[snapshot.state]
        if snapshot.raw_state:
            state += f' ({snapshot.raw_state})'
        self.state_label.setText(state)
        available = (snapshot.connection is ConnectionState.CONNECTED and not snapshot.stale
                     and snapshot.report_units is not None)
        for labels, vector in ((self.machine_labels, snapshot.machine_position_mm),
                               (self.work_labels, snapshot.work_position_mm)):
            for index, label in enumerate(labels):
                label.setText(f'{vector[index]:.3f}' if available and vector is not None else _('Unavailable'))
        status = snapshot.diagnostic
        if not status:
            if snapshot.report_units is None and snapshot.connection is ConnectionState.CONNECTED:
                status = _('Report units are unknown; positions are unverified')
            elif snapshot.stale:
                status = _('Stale or unverified position')
        self.status_label.setText(status)
        self.manual_controls.set_snapshot(snapshot, self._worker is not None and not self._stopping)

    def shutdown(self) -> bool:
        """Join owned I/O before disposal; retain the live QThread if a driver violates its bound."""
        worker = self._worker
        if worker is None:
            return True
        self.disconnect_machine()
        if not worker.wait(JOIN_TIMEOUT_MS):
            self.status_label.setText(_('Communication is still closing; keep this window open.'))
            return False
        self._release_worker()
        return True

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.shutdown():
            super().closeEvent(event)
        else:
            event.ignore()


def open_machine_panel(app: Any) -> MachinePanel:
    """Reuse the application's dock without creating a controller or connection."""
    panel = getattr(app, '_mikrocam_machine_panel', None)
    if panel is None:
        panel = MachinePanel(app.ui, ports_provider=list_ports)
        app.ui.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, panel)
        app._mikrocam_machine_panel = panel
    panel.show()
    panel.raise_()
    return panel
