"""Read-only historical layer/source evidence shared by Gerber and Excellon."""

import builtins
import gettext
from PyQt6 import QtCore, QtWidgets
from mikrocam.core.manufacturing_models import ManufacturingReport
from mikrocam.bridge.manufacturing_import import read_manufacturing_report

_ = getattr(builtins, "_", gettext.gettext)
HISTORICAL = _(
    "Historical manufacturing source evidence; not a current geometry or stackup audit."
)


def _plain(text: str) -> str:
    return "".join(
        c if c.isprintable() else c.encode("unicode_escape").decode("ascii")
        for c in text
    )


def _details(report: ManufacturingReport) -> str:
    source = report.inspection
    lines = [
        HISTORICAL,
        _("Source: {name}").format(name=_plain(source.source_name)),
        f"SHA-256: {source.source_sha256}",
        _("Original bytes: {count}").format(count=source.byte_count),
        _("Confirmed format: {kind}; layer role: {role}").format(
            kind=report.kind, role=report.role
        ),
        _("Parsed source units: {units}; origin: {origin}").format(
            units=report.parsed_units, origin=report.units_origin
        ),
        _("Inspected proposals: {kind}; {role}; {units}").format(
            kind=source.format_hint, role=source.role_hint, units=source.units_hint
        ),
        _("Evidence:"),
    ]
    lines.extend(
        f"{v.origin}: {_plain(v.detail)} [{v.format_hint}; {v.role_hint}; {v.units_hint}]"
        for v in source.evidence
    )
    lines.append(_("Issues:"))
    lines.extend(_plain(v) for v in source.issues)
    if not source.issues:
        lines.append(_("None recorded."))
    return "\n".join(lines)


class ManufacturingReportSection(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toggle = QtWidgets.QToolButton(self)
        self.toggle.setText(_("Manufacturing source report"))
        self.toggle.setCheckable(True)
        self.toggle.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        layout.addWidget(self.toggle)
        self.summary_label = QtWidgets.QLabel(self)
        self.summary_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        self.details = QtWidgets.QPlainTextEdit(self)
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(120)
        self.details.setMaximumHeight(260)
        layout.addWidget(self.details)
        self.toggle.toggled.connect(self._toggle)
        self.set_report(None)

    def _toggle(self, expanded: bool) -> None:
        self.details.setVisible(expanded)
        self.toggle.setArrowType(
            QtCore.Qt.ArrowType.DownArrow
            if expanded
            else QtCore.Qt.ArrowType.RightArrow
        )

    def set_report(self, report: ManufacturingReport | None, error: str = "") -> None:
        if report is not None and type(report) is not ManufacturingReport:
            report, error = None, _("Invalid manufacturing report record.")
        if error:
            report = None
        if report is None:
            self.details.clear()
            self.toggle.setChecked(False)
            self._toggle(False)
            self.toggle.setEnabled(False)
            self.summary_label.setText(
                HISTORICAL
                + "\n"
                + _("Unavailable.")
                + (" " + _plain(str(error)[:512]) if error else "")
            )
            return
        self.toggle.setEnabled(True)
        self.summary_label.setText(
            HISTORICAL
            + "\n"
            + _("{kind}; {role}; source units {units} ({origin}).").format(
                kind=report.kind,
                role=report.role,
                units=report.parsed_units,
                origin=report.units_origin,
            )
        )
        self.details.setPlainText(_details(report))


def attach_manufacturing_report(owner: object) -> None:
    ui = owner.ui
    section = getattr(ui, "mikrocam_manufacturing_report", None)
    if section is None:
        section = ManufacturingReportSection(ui)
        ui.custom_box.insertWidget(min(5, ui.custom_box.count()), section)
        ui.mikrocam_manufacturing_report = section
    try:
        report = read_manufacturing_report(owner)
    except ValueError as error:
        section.set_report(None, error=str(error))
        section.show()
        return
    section.set_report(report)
    section.setVisible(report is not None)
