"""Fixed typed manual intents; the controller remains the authority for admission."""
import builtins
import gettext

from PyQt6 import QtCore, QtWidgets

from mikrocam.machine.manual_models import JogRequest, SelectG54Request, ZeroRequest
from mikrocam.machine.models import ConnectionState, MachineSnapshot, ManualObservation, ManualPhase


_ = getattr(builtins, '_', gettext.gettext)


class MachineManualControls(QtWidgets.QWidget):
    requested = QtCore.pyqtSignal(object)
    cancel_requested = QtCore.pyqtSignal()
    abort_requested = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._snapshot = MachineSnapshot()
        self._worker_available = False
        self._pending_baseline: ManualObservation | None = None
        layout = QtWidgets.QVBoxLayout(self)
        help_label = QtWidgets.QLabel(_('Jog commands outputs off and requires empty startup blocks. '
                                        'Set G54 zero changes persistent offsets for the selected axes. '
                                        'Abort may cause parking or lose position; physical E-stop and '
                                        'interlocks remain necessary.'))
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        presets = QtWidgets.QFormLayout()
        self.step_combo, self.feed_combo = QtWidgets.QComboBox(), QtWidgets.QComboBox()
        for step in (.1, 1., 10.):
            self.step_combo.addItem(f'{step:g}', step)
        for feed in (100., 300., 600.):
            self.feed_combo.addItem(f'{feed:g}', feed)
        presets.addRow(_('Step (mm)'), self.step_combo)
        presets.addRow(_('Feed (mm/min)'), self.feed_combo)
        layout.addLayout(presets)
        jog = QtWidgets.QGridLayout()
        self.jog_buttons: dict[tuple[str, int], QtWidgets.QPushButton] = {}
        for row, axis in enumerate(('X', 'Y', 'Z')):
            for column, sign in enumerate((-1, 1)):
                button = QtWidgets.QPushButton(f'{axis}{"−" if sign < 0 else "+"}')
                button.setAutoRepeat(False)
                button.clicked.connect(lambda checked=False, axis=axis, sign=sign: self._jog(axis, sign))
                self.jog_buttons[axis, sign] = button
                jog.addWidget(button, row, column)
        layout.addLayout(jog)
        self.select_g54_button = QtWidgets.QPushButton(_('Use G54'))
        self.select_g54_button.clicked.connect(lambda: self.requested.emit(SelectG54Request()))
        layout.addWidget(self.select_g54_button)
        zero = QtWidgets.QHBoxLayout()
        self.zero_buttons: dict[str, QtWidgets.QPushButton] = {}
        for axes in ('XY', 'Z', 'XYZ'):
            button = QtWidgets.QPushButton(_('Set G54 zero ') + axes)
            button.clicked.connect(lambda checked=False, axes=axes: self.requested.emit(ZeroRequest(tuple(axes))))
            self.zero_buttons[axes] = button
            zero.addWidget(button)
        layout.addLayout(zero)
        stops = QtWidgets.QHBoxLayout()
        self.cancel_button, self.abort_button = QtWidgets.QPushButton(_('Cancel jog')), QtWidgets.QPushButton(_('Abort'))
        self.cancel_button.clicked.connect(self.cancel_requested)
        self.abort_button.clicked.connect(self.abort_requested)
        stops.addWidget(self.cancel_button)
        stops.addWidget(self.abort_button)
        layout.addLayout(stops)
        self.operation_label = QtWidgets.QLabel()
        self.operation_label.setWordWrap(True)
        layout.addWidget(self.operation_label)
        self._render()

    def _jog(self, axis: str, sign: int) -> None:
        self.requested.emit(JogRequest(axis, sign * self.step_combo.currentData(), self.feed_combo.currentData()))

    def set_snapshot(self, snapshot: MachineSnapshot, worker_available: bool) -> None:
        """Display immutable admission evidence on the GUI thread only."""
        self._snapshot, self._worker_available = snapshot, worker_available
        if snapshot.manual != self._pending_baseline or not worker_available:
            self._pending_baseline = None
        self._render()

    def set_pending(self) -> None:
        """Lock new actions immediately, including across queued unchanged old snapshots."""
        self._pending_baseline = self._snapshot.manual
        self._render()

    def _render(self) -> None:
        observation = self._snapshot.manual
        connected = self._worker_available and self._snapshot.connection is ConnectionState.CONNECTED
        admitted = connected and self._pending_baseline is None
        for button in self.jog_buttons.values():
            button.setEnabled(admitted and observation.can_jog)
        for button in self.zero_buttons.values():
            button.setEnabled(admitted and observation.can_zero)
        self.select_g54_button.setEnabled(admitted and observation.can_select_g54)
        self.step_combo.setEnabled(admitted and observation.can_jog)
        self.feed_combo.setEnabled(admitted and observation.can_jog)
        self.cancel_button.setEnabled(connected and observation.can_cancel)
        self.abort_button.setEnabled(connected)
        phases = {ManualPhase.READY: _('Ready'), ManualPhase.PREPARING: _('Preparing'),
                  ManualPhase.MOVING: _('Moving'), ManualPhase.VERIFYING: _('Verifying'),
                  ManualPhase.CANCELLING: _('Cancelling'), ManualPhase.COMPLETE: _('Complete'),
                  ManualPhase.FAILED: _('Failed'), ManualPhase.ABORTED: _('Aborted')}
        text = _('Request pending') if self._pending_baseline is not None else phases[observation.phase]
        if observation.diagnostic:
            text += ': ' + observation.diagnostic
        if observation.stop_unverified:
            text += ' — ' + _('Stop is unverified')
        self.operation_label.setText(_('Manual operation: ') + text)
