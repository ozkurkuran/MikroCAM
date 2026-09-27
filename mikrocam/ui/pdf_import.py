"""Explicit bounded PDF file, page and physical options review before Geometry publication."""

import builtins
import gettext
import math
from typing import Any
from PyQt6 import QtCore, QtWidgets
from mikrocam.core.pdf_models import PdfDocumentInfo, PdfImportReview, PdfOptions
from mikrocam.bridge.pdf_import import (
    inspect_pdf_file,
    load_pdf_review,
    create_pdf_geometry,
)
from .pdf_report import format_pdf_report

_ = getattr(builtins, "_", gettext.gettext)


def _plain(text: str) -> str:
    return "".join(
        c if c.isprintable() else c.encode("unicode_escape").decode("ascii")
        for c in text
    )


class PdfImportDialog(QtWidgets.QDialog):
    def __init__(self, app: Any, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent if parent is not None else getattr(app, "ui", None))
        self.app = app
        self.document: PdfDocumentInfo | None = None
        self.review: PdfImportReview | None = None
        self.setWindowTitle(_("Import PDF vector page"))
        self.setModal(True)
        self.resize(780, 680)
        layout = QtWidgets.QVBoxLayout(self)
        warning = QtWidgets.QLabel(
            _(
                "Supports opaque vector paths. Pages containing images, visible text, forms "
                "or transparency require conversion to supported paths before import."
            ),
            self,
        )
        warning.setWordWrap(True)
        warning.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        layout.addWidget(warning)
        row = QtWidgets.QHBoxLayout()
        self.path_edit = QtWidgets.QLineEdit(self)
        self.browse_button = QtWidgets.QPushButton(_("Browse…"), self)
        self.inspect_button = QtWidgets.QPushButton(_("Inspect pages"), self)
        row.addWidget(self.path_edit, 1)
        row.addWidget(self.browse_button)
        row.addWidget(self.inspect_button)
        layout.addLayout(row)
        self._options(layout)
        self.analyse_button = QtWidgets.QPushButton(_("Analyse selected page"), self)
        layout.addWidget(self.analyse_button)
        self.report_view = QtWidgets.QPlainTextEdit(self)
        self.report_view.setReadOnly(True)
        layout.addWidget(self.report_view, 1)
        form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit(self)
        form.addRow(_("New Geometry name"), self.name_edit)
        layout.addLayout(form)
        self.status_label = QtWidgets.QLabel(self)
        self.status_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        buttons = QtWidgets.QHBoxLayout()
        self.create_button = QtWidgets.QPushButton(_("Create reviewed Geometry"), self)
        cancel = QtWidgets.QPushButton(_("Cancel"), self)
        buttons.addStretch(1)
        buttons.addWidget(self.create_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self.browse_button.clicked.connect(self._browse)
        self.inspect_button.clicked.connect(self.inspect_document)
        self.analyse_button.clicked.connect(self.analyse)
        self.create_button.clicked.connect(self.create_selected)
        cancel.clicked.connect(self.reject)
        self.path_edit.textChanged.connect(self._source_changed)
        self.name_edit.textChanged.connect(self._update_create)
        self._source_changed()

    def _options(self, layout: QtWidgets.QVBoxLayout) -> None:
        form = QtWidgets.QFormLayout()
        self.page_combo = QtWidgets.QComboBox(self)
        self.box_combo = QtWidgets.QComboBox(self)
        self.box_combo.addItem(_("Crop box"), "crop")
        self.box_combo.addItem(_("Media box"), "media")
        form.addRow(_("Page"), self.page_combo)
        form.addRow(_("Page frame"), self.box_combo)
        self.crop_check = QtWidgets.QCheckBox(
            _("Explicit oriented physical crop (mm)"), self
        )
        form.addRow(self.crop_check)
        row = QtWidgets.QHBoxLayout()
        for name, label in (
            ("xmin", "min X"),
            ("ymin", "min Y"),
            ("xmax", "max X"),
            ("ymax", "max Y"),
        ):
            edit = QtWidgets.QLineEdit(self)
            edit.setPlaceholderText(_(label))
            edit.setAccessibleName(_(label))
            setattr(self, name + "_edit", edit)
            column = QtWidgets.QVBoxLayout()
            column.addWidget(QtWidgets.QLabel(_(label), self))
            column.addWidget(edit)
            row.addLayout(column)
            edit.textChanged.connect(self._invalidate)
        form.addRow(row)
        self.flip_check = QtWidgets.QCheckBox(
            _("Flip vertically about final viewport height"), self
        )
        form.addRow(self.flip_check)
        layout.addLayout(form)
        self.page_combo.currentIndexChanged.connect(self._invalidate)
        self.box_combo.currentIndexChanged.connect(self._invalidate)
        self.crop_check.toggled.connect(self._invalidate)
        self.flip_check.toggled.connect(self._invalidate)

    def _invalidate(self) -> None:
        self.review = None
        self.report_view.clear()
        self.create_button.setEnabled(False)
        self.analyse_button.setEnabled(self.document is not None)
        self.status_label.setText(
            _("Inspect the file and analyse explicit page options before creation.")
        )

    def _source_changed(self) -> None:
        self.document = None
        self.page_combo.clear()
        self._invalidate()
        self.inspect_button.setEnabled(bool(self.path_edit.text().strip()))

    def _browse(self) -> None:
        filename, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, _("Select PDF source"), "", _("PDF files (*.pdf)")
        )
        if filename:
            self.path_edit.setText(filename)

    @QtCore.pyqtSlot()
    def inspect_document(self) -> None:
        self._source_changed()
        try:
            document = inspect_pdf_file(self.path_edit.text().strip())
        except (ValueError, TypeError, OSError, UnicodeError) as error:
            self.status_label.setText(
                _("Inspection failed: ") + _plain(str(error)[:512])
            )
            return
        blocker = QtCore.QSignalBlocker(self.page_combo)
        for page in document.pages:
            self.page_combo.addItem(
                _("Page {page} — rotation {rotation}°").format(
                    page=page.index + 1, rotation=page.rotation
                ),
                page.index,
            )
        del blocker
        self.document = document
        self._invalidate()
        self.status_label.setText(
            _(
                "Pages inspected: {count}. Choose page, box and optional physical crop."
            ).format(count=len(document.pages))
        )

    def _value(self) -> PdfOptions:
        if self.document is None or self.page_combo.currentData() is None:
            raise ValueError(_("Inspect a PDF and select a page first."))
        crop = None
        if self.crop_check.isChecked():
            values = []
            for name in ("xmin", "ymin", "xmax", "ymax"):
                text = getattr(self, name + "_edit").text().strip()
                try:
                    value = float(text)
                except ValueError as error:
                    raise ValueError(
                        _("Every crop bound requires an explicit finite number.")
                    ) from error
                if not math.isfinite(value):
                    raise ValueError(_("Crop bounds must be finite."))
                values.append(value)
            crop = tuple(values)
        return PdfOptions(
            self.page_combo.currentData(),
            self.box_combo.currentData(),
            crop,
            self.flip_check.isChecked(),
        )

    @QtCore.pyqtSlot()
    def analyse(self) -> None:
        self._invalidate()
        try:
            self.review = load_pdf_review(self.path_edit.text().strip(), self._value())
        except (ValueError, TypeError, OSError, UnicodeError) as error:
            self.status_label.setText(_("Analysis failed: ") + _plain(str(error)[:512]))
            return
        self.report_view.setPlainText(format_pdf_report(self.review.result.report))
        self.status_label.setText(
            _("Review physical dimensions. Creation uses current destination defaults.")
        )
        self._update_create()

    def _update_create(self) -> None:
        name = self.name_edit.text().strip()
        try:
            valid = (
                bool(name) and name.isprintable() and len(name.encode("utf-8")) <= 256
            )
        except UnicodeError:
            valid = False
        self.create_button.setEnabled(self.review is not None and valid)

    @QtCore.pyqtSlot()
    def create_selected(self) -> None:
        self._update_create()
        if not self.create_button.isEnabled():
            self.status_label.setText(
                _("Analyse a supported page and enter a printable Geometry name.")
            )
            return
        try:
            created = create_pdf_geometry(
                self.app,
                self.path_edit.text().strip(),
                self.review,
                self.name_edit.text().strip(),
            )
            if created is None or isinstance(created, (str, bool, int, float)):
                raise ValueError(_("PDF creation did not return a completed object."))
        except (ValueError, TypeError, OSError, UnicodeError) as error:
            self.status_label.setText(_("Creation failed: ") + _plain(str(error)[:512]))
            return
        self.accept()


def open_pdf_import(app: Any) -> None:
    dialog = PdfImportDialog(app, getattr(app, "ui", None))
    try:
        dialog.exec()
    finally:
        dialog.deleteLater()
