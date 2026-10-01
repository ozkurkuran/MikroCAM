"""Explicit probe-grid review and typed intents for the existing machine owner."""

import builtins
import gettext
from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets

from mikrocam.core.probe_map import ProbePlan, ProbeMap, uniform_grid
from mikrocam.machine.models import ConnectionState, MachineSnapshot, MachineState
from mikrocam.machine.probe_models import ProbePhase, StartProbeGridRequest
from mikrocam.ui.probe_view import ProbeMapView

_ = getattr(builtins, "_", gettext.gettext)


class ProbeDialog(QtWidgets.QDialog):
    def __init__(self, panel: Any, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.panel = panel
        self._snapshot = panel.last_snapshot
        self.plan: ProbePlan | None = None
        self._pending = False
        self.setWindowTitle(_("Probe grid and height map"))
        self.resize(700, 750)
        self.fields: dict[str, QtWidgets.QLineEdit] = {}
        self._labels: dict[str, str] = {}
        layout = QtWidgets.QVBoxLayout(self)
        help_label = QtWidgets.QLabel(
            _(
                "Probing moves the machine. Verify probe wiring, clearance and "
                "physical E-stop. G54 and all bounds must be explicit. Stop is best effort and may "
                "park or lose position. Height maps never automatically compensate or start a job."
            )
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QtWidgets.QWidget()
        form = QtWidgets.QGridLayout(form_widget)
        labels = [
            ("x_min", _("X minimum (mm)")),
            ("x_max", _("X maximum (mm)")),
            ("nx", _("X point count")),
            ("y_min", _("Y minimum (mm)")),
            ("y_max", _("Y maximum (mm)")),
            ("ny", _("Y point count")),
            ("safe_z", _("Safe work Z (mm)")),
            ("min_z", _("Minimum probe work Z (mm)")),
            ("probe_feed", _("Probe feed (mm/min)")),
            ("travel_feed", _("Travel feed (mm/min)")),
            ("timeout", _("Transaction timeout (s)")),
        ]
        labels += [
            (
                f"machine_{bound}_{axis}",
                _("Machine {bound} {axis} (mm)").format(
                    bound=_(bound), axis=axis.upper()
                ),
            )
            for bound in ("min", "max")
            for axis in "xyz"
        ]
        for index, (key, label) in enumerate(labels):
            edit = QtWidgets.QLineEdit()
            edit.setPlaceholderText(_("Required"))
            edit.textChanged.connect(self._invalidate)
            self.fields[key] = edit
            self._labels[key] = label
            form.addWidget(QtWidgets.QLabel(label), index // 3 * 2, index % 3)
            form.addWidget(edit, index // 3 * 2 + 1, index % 3)
        scroll.setWidget(form_widget)
        layout.addWidget(scroll)
        self.status_label = QtWidgets.QLabel(
            _("Enter all values and review before starting")
        )
        self.status_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        buttons = QtWidgets.QHBoxLayout()
        self.review_button = QtWidgets.QPushButton(_("Review grid"))
        self.start_button = QtWidgets.QPushButton(_("Start probing"))
        self.stop_button = QtWidgets.QPushButton(_("Stop probing"))
        self.review_button.clicked.connect(self.review_grid)
        self.start_button.clicked.connect(self.start_grid)
        self.stop_button.clicked.connect(panel.stop_probe)
        for button in (self.review_button, self.start_button, self.stop_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.viewer = ProbeMapView(self)
        layout.addWidget(self.viewer)
        self._render()

    @property
    def busy(self) -> bool:
        return self._pending or self._snapshot.probe.phase in (
            ProbePhase.PREPARING,
            ProbePhase.PROBING,
        )

    def _admitted(self) -> bool:
        value = self._snapshot
        return (
            value.connection is ConnectionState.CONNECTED
            and value.state is MachineState.IDLE
            and not value.stale
            and value.probe.can_start
            and value.machine_position_mm is not None
            and value.work_offset_mm is not None
        )

    def _invalidate(self) -> None:
        self.plan = None
        self._render()

    def _number(self, key: str, integer: bool = False) -> float | int:
        text = self.fields[key].text().strip()
        if not text:
            raise ValueError(_("Missing required value: ") + self._labels[key])
        try:
            return int(text) if integer else float(text)
        except ValueError as error:
            raise ValueError(_("Invalid number: ") + self._labels[key]) from error

    def review_grid(self) -> None:
        if self.busy:
            return
        self.plan = None
        try:
            if not self._admitted():
                raise ValueError(
                    _(
                        "Fresh connected Idle coordinates and probe admission are required"
                    )
                )
            grid = uniform_grid(
                self._number("x_min"),
                self._number("x_max"),
                self._number("nx", True),
                self._number("y_min"),
                self._number("y_max"),
                self._number("ny", True),
            )
            self.plan = ProbePlan(
                grid,
                self._number("safe_z"),
                self._number("min_z"),
                self._number("probe_feed"),
                self._number("travel_feed"),
                tuple(self._number("machine_min_" + axis) for axis in "xyz"),
                tuple(self._number("machine_max_" + axis) for axis in "xyz"),
                self._snapshot.machine_position_mm,
                self._snapshot.work_offset_mm,
                self._number("timeout"),
            )
            self.viewer.preview_grid(grid)
            self.status_label.setText(
                _("Reviewed {count} points; explicit Start is required").format(
                    count=grid.count
                )
            )
        except ValueError as error:
            self.status_label.setText(str(error))
        self._render()

    def start_grid(self) -> None:
        if self.busy or self.plan is None or not self._admitted():
            return
        if self.panel.submit_probe(StartProbeGridRequest(self.plan)):
            self._pending = True
            self.status_label.setText(_("Probe request pending"))
        else:
            self.status_label.setText(_("Probe request rejected; review again"))
        self.plan = None
        self._render()

    def update_snapshot(self, snapshot: MachineSnapshot) -> None:
        old = self._snapshot
        self._snapshot = snapshot
        if (
            snapshot.machine_position_mm != old.machine_position_mm
            or snapshot.work_offset_mm != old.work_offset_mm
            or not self._admitted()
        ):
            self.plan = None
        if (
            snapshot.probe != old.probe
            or snapshot.connection is not ConnectionState.CONNECTED
        ):
            self._pending = False
        if snapshot.probe.map is not None and snapshot.probe.map != old.probe.map:
            self.set_map(snapshot.probe.map)
        if snapshot.probe.phase is not ProbePhase.READY:
            self.status_label.setText(
                _("Probe: {phase}; {done}/{total}. {diagnostic} {uncertain}").format(
                    phase=snapshot.probe.phase.value,
                    done=snapshot.probe.completed,
                    total=snapshot.probe.total,
                    diagnostic=snapshot.probe.diagnostic,
                    uncertain=_("Physical stop is unverified")
                    if snapshot.probe.stop_unverified
                    else "",
                )
            )
        self._render()

    def set_map(self, value: ProbeMap) -> None:
        self.viewer.set_map(value)

    def _render(self) -> None:
        busy = self.busy
        for field in self.fields.values():
            field.setEnabled(not busy)
        self.review_button.setEnabled(not busy)
        self.start_button.setEnabled(
            not busy and self.plan is not None and self._admitted()
        )
        self.stop_button.setEnabled(
            busy and (self._pending or self._snapshot.probe.can_stop)
        )
        self.viewer.load_button.setEnabled(not busy)
        self.viewer.save_button.setEnabled(not busy and self.viewer.map is not None)

    def reject(self) -> None:
        if not self.busy:
            super().reject()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.busy:
            event.ignore()
        else:
            super().closeEvent(event)
