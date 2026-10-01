"""Offline numeric height-map view; never talks to a machine owner."""

import builtins
import gettext
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

from mikrocam.bridge.probe_files import load_probe_map, save_probe_map
from mikrocam.core.probe_map import ProbeGrid, ProbeMap

_ = getattr(builtins, "_", gettext.gettext)


class ProbeMapView(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.map: ProbeMap | None = None
        layout = QtWidgets.QVBoxLayout(self)
        self.status_label = QtWidgets.QLabel(_("No height map"))
        self.status_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.status_label.setWordWrap(True)
        self.table = QtWidgets.QTableWidget()
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)
        buttons = QtWidgets.QHBoxLayout()
        self.load_button = QtWidgets.QPushButton(_("Load map"))
        self.save_button = QtWidgets.QPushButton(_("Save map"))
        self.load_button.clicked.connect(self._load)
        self.save_button.clicked.connect(self._save)
        buttons.addWidget(self.load_button)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)
        self.save_button.setEnabled(False)

    def set_map(self, value: ProbeMap) -> None:
        if type(value) is not ProbeMap:
            raise ValueError(_("A validated height map is required"))
        self.map = value
        self._axes(value.grid)
        heights = [height for height in value.heights_mm if height is not None]
        low, high = (min(heights), max(heights)) if heights else (0.0, 0.0)
        for index, height in enumerate(value.heights_mm):
            item = QtWidgets.QTableWidgetItem(
                "—" if height is None else f"{height:.6f}"
            )
            if height is not None:
                fraction = (height - low) / (high - low) if high > low else 0.5
                item.setBackground(
                    QtGui.QColor.fromHsvF((1 - fraction) * 0.66, 0.45, 0.95)
                )
            self.table.setItem(
                index // len(value.grid.x_mm), index % len(value.grid.x_mm), item
            )
        self.status_label.setText(
            _(
                "Origin: {origin}; outcome: {outcome}; {done}/{total} measured. "
                "Work Z in mm; range: {low} to {high}; G54 machine offset: {offset}. "
                "Offline display does not arm probing."
            ).format(
                origin=value.origin,
                outcome=value.outcome,
                done=value.completed,
                total=value.grid.count,
                offset=value.g54_offset_mm,
                low=f"{low:.6f}" if heights else "—",
                high=f"{high:.6f}" if heights else "—",
            )
        )
        self.save_button.setEnabled(True)

    def _axes(self, grid: ProbeGrid) -> None:
        self.table.setRowCount(len(grid.y_mm))
        self.table.setColumnCount(len(grid.x_mm))
        self.table.setHorizontalHeaderLabels(
            [_("X {value} mm").format(value=f"{x:g}") for x in grid.x_mm]
        )
        self.table.setVerticalHeaderLabels(
            [_("Y {value} mm").format(value=f"{y:g}") for y in grid.y_mm]
        )

    def preview_grid(self, grid: ProbeGrid) -> None:
        """Display proposed coordinates without inventing measured map provenance."""
        self.map = None
        self._axes(grid)
        for row in range(len(grid.y_mm)):
            for column in range(len(grid.x_mm)):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem("—"))
        self.status_label.setText(
            _("Reviewed coordinates only; no measurements acquired")
        )
        self.save_button.setEnabled(False)

    def load_path(self, path: str | Path) -> None:
        self.set_map(load_probe_map(path))

    def save_path(self, path: str | Path) -> None:
        if self.map is None:
            raise ValueError(_("No height map to save"))
        save_probe_map(path, self.map)

    def _load(self) -> None:
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, _("Load height map"), "", _("JSON (*.json)")
        )
        if path:
            try:
                self.load_path(path)
            except (ValueError, OSError) as error:
                self.status_label.setText(str(error))

    def _save(self) -> None:
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, _("Save height map"), "", _("JSON (*.json)")
        )
        if path:
            try:
                self.save_path(path)
            except (ValueError, OSError) as error:
                self.status_label.setText(str(error))
