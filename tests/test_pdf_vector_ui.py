from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
import pytest
from PyQt6 import QtCore, QtWidgets
from test_pdf_vector_models import report, page, geometry
from mikrocam.core.pdf_models import PdfDocumentInfo, PdfGeometryResult, PdfImportReview
from mikrocam.ui.pdf_import import PdfImportDialog, open_pdf_import
import mikrocam.ui.pdf_import as module


def review():
    data = b"%PDF-authored"
    return PdfImportReview(
        data,
        PdfGeometryResult(
            replace(report(), source_sha256=sha256(data).hexdigest()), geometry()
        ),
    )


@pytest.fixture
def dialog(qtbot, monkeypatch):
    parent = QtWidgets.QMainWindow()
    qtbot.addWidget(parent)
    doc = PdfDocumentInfo("board.pdf", "a" * 64, (page(), replace(page(), index=1)))
    calls = []
    monkeypatch.setattr(module, "inspect_pdf_file", lambda path: doc)
    monkeypatch.setattr(
        module, "load_pdf_review", lambda *args: calls.append(args) or review()
    )
    value = PdfImportDialog(SimpleNamespace(ui=parent))
    qtbot.addWidget(value)
    return value, calls


def inspect(value):
    value.path_edit.setText("board.pdf")
    value.inspect_document()


def test_defaults_inert_parent_owned_explicit_inspection(dialog):
    value, calls = dialog
    assert value.parent() is value.app.ui and value.isModal()
    assert value.document is None and value.review is None and not calls
    assert not value.create_button.isEnabled() and not value.flip_check.isChecked()
    assert not value.crop_check.isChecked() and value.box_combo.currentData() == "crop"
    inspect(value)
    assert value.page_combo.count() == 2 and value.document is not None
    value.analyse()
    assert len(calls) == 1 and calls[0][1].page_index == 0
    assert "bounds" in value.report_view.toPlainText().lower()
    assert not value.create_button.isEnabled()


@pytest.mark.parametrize(
    "edit", ["path", "page", "box", "flip", "crop", "xmin", "ymin", "xmax", "ymax"]
)
def test_edits_invalidate_review(dialog, edit):
    value, _ = dialog
    inspect(value)
    value.analyse()
    value.name_edit.setText("physical vectors")
    assert value.create_button.isEnabled()
    if edit == "path":
        value.path_edit.setText("other.pdf")
    elif edit == "page":
        value.page_combo.setCurrentIndex(1)
    elif edit == "box":
        value.box_combo.setCurrentIndex(1)
    elif edit == "flip":
        value.flip_check.setChecked(True)
    elif edit == "crop":
        value.crop_check.setChecked(True)
    else:
        getattr(value, edit + "_edit").setText("1")
    assert value.review is None and not value.create_button.isEnabled()
    assert not value.report_view.toPlainText()
    if edit == "path":
        assert value.document is None


def test_crop_requires_explicit_finite_bounds(dialog):
    value, calls = dialog
    inspect(value)
    value.crop_check.setChecked(True)
    value.analyse()
    assert not calls and "failed" in value.status_label.text().lower()
    for name, text in [("xmin", "1"), ("ymin", "2"), ("xmax", "4"), ("ymax", "5")]:
        getattr(value, name + "_edit").setText(text)
    value.flip_check.setChecked(True)
    value.analyse()
    assert calls[0][1].crop_mm == (1, 2, 4, 5) and calls[0][1].flip


@pytest.mark.parametrize("result", [None, "fail", False])
def test_creation_failed_results_keep_open(dialog, monkeypatch, result):
    value, _ = dialog
    inspect(value)
    value.analyse()
    value.name_edit.setText("physical vectors")
    monkeypatch.setattr(module, "create_pdf_geometry", lambda *args: result)
    value.create_selected()
    assert value.result() != QtWidgets.QDialog.DialogCode.Accepted


def test_creation_guard_error_and_explicit_success(dialog, monkeypatch):
    value, _ = dialog
    inspect(value)
    value.analyse()
    value.name_edit.setText("  physical vectors  ")

    def fail(*args):
        raise ValueError("Source changed")

    monkeypatch.setattr(module, "create_pdf_geometry", fail)
    value.create_selected()
    assert "Source changed" in value.status_label.text()
    calls = []
    monkeypatch.setattr(
        module, "create_pdf_geometry", lambda *args: calls.append(args) or object()
    )
    value.create_selected()
    assert calls == [(value.app, "board.pdf", value.review, "physical vectors")]
    assert value.result() == QtWidgets.QDialog.DialogCode.Accepted


def test_inspection_failure_clears_old_pages(dialog, monkeypatch):
    value, _ = dialog
    inspect(value)

    def fail(*args):
        raise ValueError("Encrypted PDF")

    monkeypatch.setattr(module, "inspect_pdf_file", fail)
    value.inspect_document()
    assert value.document is None and value.page_combo.count() == 0
    assert "Encrypted PDF" in value.status_label.text()
