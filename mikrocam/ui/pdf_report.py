"""Collapsed historical PDF page evidence; never a current geometry or machine audit."""

import builtins
import gettext
from PyQt6 import QtCore, QtWidgets
from mikrocam.core.pdf_models import PdfImportReport
from mikrocam.bridge.pdf_import import read_pdf_report

_ = getattr(builtins, "_", gettext.gettext)
HISTORICAL = _(
    "Historical PDF import details. Geometry may have been edited since import."
)


def _plain(text: str) -> str:
    return "".join(
        c if c.isprintable() else c.encode("unicode_escape").decode("ascii")
        for c in text
    )


def format_pdf_report(report: PdfImportReport) -> str:
    """Display retained physical and source facts as literal plain text."""
    lines = [
        HISTORICAL,
        _("Source: {name}").format(name=_plain(report.source_name)),
        f"SHA-256: {report.source_sha256}",
        _("Page: {page} / {total}; rotation: {rotation}; UserUnit: {unit}").format(
            page=report.page.index + 1,
            total=report.page_count,
            rotation=report.page.rotation,
            unit=report.page.user_unit,
        ),
        _("Media box: {box}").format(box=report.page.media_box),
        _("Crop box: {box}").format(box=report.page.crop_box),
        _(
            "Selected box: {box}; physical crop mm: {crop}; vertical flip: {flip}"
        ).format(
            box=report.options.box_mode,
            crop=report.options.crop_mm,
            flip=_("Yes") if report.options.flip else _("No"),
        ),
        _("Physical viewport mm: {size}").format(size=report.viewport_mm),
        _("Page-to-mm matrix (a,b,d,e,xoff,yoff): {matrix}").format(
            matrix=report.matrix_mm
        ),
        _("Material bounds mm (minX,minY,maxX,maxY): {bounds}").format(
            bounds=report.bounds_mm
        ),
        _(
            "Components: {components}; source paths: {paths}; output coordinates: {points}"
        ).format(
            components=report.geometry_count,
            paths=report.path_count,
            points=report.point_count,
        ),
        f"Geometry SHA-256: {report.geometry_sha256}",
        _("Declared precision mm: {precision}").format(precision=report.precision_mm),
        _("Notices:"),
    ]
    lines.extend(_plain(notice) for notice in report.notices)
    if not report.notices:
        lines.append(_("None recorded."))
    return "\n".join(lines)


class PdfReportSection(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toggle = QtWidgets.QToolButton(self)
        self.toggle.setText(_("PDF import report"))
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

    def set_report(self, report: PdfImportReport | None, error: str = "") -> None:
        if report is not None and type(report) is not PdfImportReport:
            report, error = None, _("Invalid PDF report record.")
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
            + _("Page {page}; components: {count}.").format(
                page=report.page.index + 1, count=report.geometry_count
            )
        )
        self.details.setPlainText(format_pdf_report(report))


def attach_pdf_report(owner: object) -> None:
    """Reuse one child in the current owner UI and read persisted evidence only."""
    ui = owner.ui
    section = getattr(ui, "mikrocam_pdf_report", None)
    if section is None:
        section = PdfReportSection(ui)
        ui.custom_box.insertWidget(min(4, ui.custom_box.count()), section)
        ui.mikrocam_pdf_report = section
    try:
        report = read_pdf_report(owner)
    except ValueError as error:
        section.set_report(None, error=str(error))
        section.show()
        return
    section.set_report(report)
    section.setVisible(report is not None)
