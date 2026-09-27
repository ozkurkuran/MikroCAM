from types import SimpleNamespace
from PyQt6 import QtCore, QtWidgets
from test_manufacturing_codec import report
from mikrocam.ui.manufacturing_report import (
    ManufacturingReportSection,
    attach_manufacturing_report,
)
import mikrocam.ui.manufacturing_report as module


def test_report_literal_historical_and_clear_invalid(qtbot):
    section = ManufacturingReportSection()
    qtbot.addWidget(section)
    section.set_report(report())
    assert not section.toggle.isChecked() and section.details.isHidden()
    assert section.summary_label.textFormat() == QtCore.Qt.TextFormat.PlainText
    for token in ("Historical", "F.Cu", "MM", "explicit", "MO marker", "board.gbr"):
        assert token in section.details.toPlainText()
    section.set_report(None, error="bad schema")
    assert (
        not section.details.toPlainText()
        and "bad schema" in section.summary_label.text()
    )


def test_attach_one_owned_section_hides_old_and_shows_invalid(qtbot, monkeypatch):
    ui = QtWidgets.QWidget()
    qtbot.addWidget(ui)
    ui.custom_box = QtWidgets.QVBoxLayout(ui)
    owner = SimpleNamespace(ui=ui)
    monkeypatch.setattr(module, "read_manufacturing_report", lambda obj: report())
    attach_manufacturing_report(owner)
    section = ui.mikrocam_manufacturing_report
    attach_manufacturing_report(owner)
    assert (
        section.parent() is ui and ui.custom_box.count() == 1 and not section.isHidden()
    )
    monkeypatch.setattr(module, "read_manufacturing_report", lambda obj: None)
    attach_manufacturing_report(owner)
    assert section.isHidden() and not section.details.toPlainText()

    def fail(obj):
        raise ValueError("bad schema")

    monkeypatch.setattr(module, "read_manufacturing_report", fail)
    attach_manufacturing_report(owner)
    assert not section.isHidden() and "bad schema" in section.summary_label.text()
