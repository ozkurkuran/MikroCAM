"""Collapsed read-only query controls and bounded escaped wire presentation."""
import builtins
import gettext

from PyQt6 import QtCore, QtWidgets

from mikrocam.machine.console_models import CONSOLE_COMMANDS, ConsoleRequest
from mikrocam.machine.models import ConnectionState, MachineSnapshot


_ = getattr(builtins, '_', gettext.gettext)


class ConsoleControls(QtWidgets.QWidget):
    query_requested = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._snapshot = MachineSnapshot()
        self._worker_available = False
        self._pending = None
        self._clear_sequence = 0
        self._rendered_wire = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toggle_button = QtWidgets.QToolButton(self)
        self.toggle_button.setText(_('Console — read-only queries'))
        self.toggle_button.setCheckable(True)
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        layout.addWidget(self.toggle_button)
        self.body = QtWidgets.QWidget(self)
        body_layout = QtWidgets.QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        actions = QtWidgets.QHBoxLayout()
        self.query_combo = QtWidgets.QComboBox(self.body)
        self.query_combo.addItems(CONSOLE_COMMANDS)
        self.send_button = QtWidgets.QPushButton(_('Send query'), self.body)
        self.clear_button = QtWidgets.QPushButton(_('Clear view'), self.body)
        for widget in (self.query_combo, self.send_button, self.clear_button):
            actions.addWidget(widget)
        body_layout.addLayout(actions)
        self.diagnostic_label = QtWidgets.QLabel(self.body)
        self.diagnostic_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.diagnostic_label.setWordWrap(True)
        body_layout.addWidget(self.diagnostic_label)
        self.log_view = QtWidgets.QPlainTextEdit(self.body)
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(180)
        self.log_view.setMinimumHeight(80)
        self.log_view.document().setMaximumBlockCount(513)
        body_layout.addWidget(self.log_view)
        layout.addWidget(self.body)
        self.body.hide()
        self.toggle_button.toggled.connect(self._toggle)
        self.send_button.clicked.connect(self._send)
        self.clear_button.clicked.connect(self._clear)
        self.set_snapshot(self._snapshot, False)

    def _toggle(self, expanded: bool) -> None:
        self.body.setVisible(expanded)
        self.toggle_button.setArrowType(QtCore.Qt.ArrowType.DownArrow if expanded
                                        else QtCore.Qt.ArrowType.RightArrow)

    def set_snapshot(self, snapshot: MachineSnapshot, worker_available: bool) -> None:
        if (snapshot.connection is ConnectionState.CONNECTING
                and self._snapshot.connection is not ConnectionState.CONNECTING):
            self._clear_sequence = 0
            self._rendered_wire = None
        if snapshot.console != self._pending or not worker_available:
            self._pending = None
        self._snapshot, self._worker_available = snapshot, worker_available
        eligible = (worker_available and snapshot.connection is ConnectionState.CONNECTED
                    and snapshot.console.can_query and self._pending is None)
        self.send_button.setEnabled(eligible)
        self.query_combo.setEnabled(eligible)
        observation = snapshot.console
        text = _(observation.phase.value.capitalize())
        if observation.command:
            text += ': ' + observation.command
        if observation.diagnostic:
            text += '\n' + _(observation.diagnostic)
        self.diagnostic_label.setText(text)
        self._render_log()

    def reject_pending(self, message: str) -> None:
        """Release a locally queued click rejected before owner admission."""
        self._pending = None
        self.set_snapshot(self._snapshot, self._worker_available)
        self.diagnostic_label.setText(_('Query rejected: ') + message[:256])

    def _send(self) -> None:
        if not self.send_button.isEnabled():
            return
        request = ConsoleRequest(self.query_combo.currentText())
        self._pending = self._snapshot.console
        self.send_button.setEnabled(False)
        self.query_combo.setEnabled(False)
        self.query_requested.emit(request)

    def _clear(self) -> None:
        records = self._snapshot.wire.records
        if records:
            self._clear_sequence = records[-1].sequence
        self._rendered_wire = None
        self._render_log()

    def _render_log(self) -> None:
        wire = self._snapshot.wire
        if wire == self._rendered_wire:
            return
        lines = [_('Omitted entries: {entries}; omitted bytes: {bytes}').format(
            entries=wire.dropped_entries, bytes=wire.dropped_bytes)]
        for record in wire.records:
            if record.sequence <= self._clear_sequence:
                continue
            line = (f'#{record.sequence} {record.timestamp:.3f} '
                    f'{record.direction}/{record.outcome} {record.payload!r}')
            if record.omitted_bytes:
                line += ' ' + _('omitted bytes: {count}').format(count=record.omitted_bytes)
            if record.diagnostic:
                line += f' {record.diagnostic!r}'
            lines.append(line)
        self.log_view.setPlainText('\n'.join(lines))
        self._rendered_wire = wire
