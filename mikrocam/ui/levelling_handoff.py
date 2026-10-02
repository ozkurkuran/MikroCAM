"""Present the single-owner Machine route instead of legacy GRBL controls."""
import builtins
from functools import wraps
from typing import Any, Callable

from PyQt6 import QtWidgets


def reject_legacy_grbl(app: Any) -> None:
    app.inform.emit("[WARNING_NOTCL] " + builtins._(
        "Use the Machine panel for GRBL probing, auto-level and sending."))


def guard_grbl_callback(callback: Callable[..., Any]) -> Callable[..., Any]:
    """Reject stale/direct legacy callbacks before UI, worker or serial side effects."""
    @wraps(callback)
    def guarded(tool: Any, *args: Any, **kwargs: Any) -> Any:
        reject_legacy_grbl(tool.app)
        return None
    return guarded


def update_levelling_handoff(tool: Any) -> None:
    ui = tool.ui
    if not hasattr(ui, "machine_handoff"):
        card = QtWidgets.QFrame()
        card.setObjectName("mikrocam_levelling_machine_handoff")
        layout = QtWidgets.QVBoxLayout(card)
        label = QtWidgets.QLabel(builtins._(
            "GRBL uses the Machine panel for its single connection, probe grid, "
            "auto-level and job sending."))
        label.setWordWrap(True)
        layout.addWidget(label)
        button = QtWidgets.QPushButton(builtins._("Open Machine panel"))
        def open_panel() -> None:
            from .machine_panel import open_machine_panel
            open_machine_panel(tool.app)
        button.clicked.connect(open_panel)
        layout.addWidget(button)
        tool.layout.insertWidget(2, card)
        ui.machine_handoff = card
        ui.machine_handoff_button = button
    grbl = ui.al_controller_combo.get_value() == "GRBL"
    ui.grbl_frame.hide()
    ui.grbl_frame.setEnabled(False)
    ui.machine_handoff.setVisible(grbl)
    for button in (ui.h_gcode_button, ui.view_h_gcode_button, ui.import_heights_button):
        button.setVisible(not grbl)
