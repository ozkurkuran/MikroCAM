from types import SimpleNamespace
from dataclasses import replace
from PyQt6 import QtCore, QtWidgets
from test_pdf_vector_models import report
from mikrocam.ui.pdf_report import PdfReportSection, attach_pdf_report
import mikrocam.ui.pdf_report as module


def test_collapsed_plain_complete_historical_details(qtbot):
    section = PdfReportSection()
    qtbot.addWidget(section)
    section.set_report(
        replace(
            report(), source_name="<b>board.pdf</b>", notices=("literal <b>notice</b>",)
        )
    )
    assert not section.toggle.isChecked() and section.details.isHidden()
    assert section.details.isReadOnly()
    assert section.summary_label.textFormat() == QtCore.Qt.TextFormat.PlainText
    text = section.details.toPlainText()
    for token in (
        "Historical",
        "<b>board.pdf</b>",
        "a" * 64,
        "bounds",
        "0.01",
        "notice",
        "matrix",
    ):
        assert token.lower() in text.lower()
    section.toggle.setChecked(True)
    assert not section.details.isHidden()
    section.set_report(None, error="invalid record")
    assert not section.details.toPlainText() and not section.toggle.isChecked()
    assert "invalid record" in section.summary_label.text()


def test_attach_reuses_owner_ui_no_file_access_and_hides_missing(qtbot, monkeypatch):
    ui = QtWidgets.QWidget()
    qtbot.addWidget(ui)
    ui.custom_box = QtWidgets.QVBoxLayout(ui)
    owner = SimpleNamespace(ui=ui)
    monkeypatch.setattr(module, "read_pdf_report", lambda obj: report())
    attach_pdf_report(owner)
    section = ui.mikrocam_pdf_report
    assert section.parent() is ui and not section.isHidden()
    attach_pdf_report(owner)
    assert ui.mikrocam_pdf_report is section and ui.custom_box.count() == 1
    monkeypatch.setattr(module, "read_pdf_report", lambda obj: None)
    attach_pdf_report(owner)
    assert section.isHidden() and not section.details.toPlainText()

    def fail(obj):
        raise ValueError("unsupported schema")

    monkeypatch.setattr(module, "read_pdf_report", fail)
    attach_pdf_report(owner)
    assert (
        not section.isHidden() and "unsupported schema" in section.summary_label.text()
    )
