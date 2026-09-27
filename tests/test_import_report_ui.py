"""Selected-object reports present bounded historical facts without active operations."""
from dataclasses import replace
from copy import deepcopy
from types import SimpleNamespace

import pytest
from PyQt6 import QtCore, QtWidgets
from PyQt6.sip import isdeleted

from mikrocam.core.import_report import ImportCoordinates, ImportQuality, ImportReport
from mikrocam.core.import_report_codec import report_to_dict
from mikrocam.core.svg_models import SvgNotice
from mikrocam.ui.import_report import ImportReportSection, attach_import_report


def report(name='<b>source.svg</b>', sha='a' * 64):
    return ImportReport(name, sha,
        ImportCoordinates('100mm', '50mm', ('mm', 'mm'), (0., 0., 200., 100.),
                          'xMidYMid meet', (100., 50.), (.5, 0., 0., -.5, 0., 50.), True),
        ImportQuality((10., 30., 30., 40.), 3, 2, 0, 1, 2, 1, .01),
        (SvgNotice('retained-centerline', '<b>Open centreline</b>\nNext line', 'path-1'),))


@pytest.fixture
def section(qtbot):
    value = ImportReportSection()
    qtbot.addWidget(value)
    return value


def owner(qtbot, payload):
    ui = QtWidgets.QWidget()
    ui.custom_box = QtWidgets.QVBoxLayout(ui)
    qtbot.addWidget(ui)
    return SimpleNamespace(ui=ui, import_report=payload)


def test_initial_section_collapsed_readonly_unavailable(section):
    assert not section.toggle.isChecked()
    assert section.details.isHidden()
    assert isinstance(section.details, QtWidgets.QPlainTextEdit)
    assert section.details.isReadOnly()
    assert section.summary_label.textFormat() == QtCore.Qt.TextFormat.PlainText
    assert 'historical' in section.summary_label.text().lower()
    assert 'unavailable' in section.summary_label.text().lower()


def test_complete_report_displays_source_physical_facts_without_rich_text(section):
    value = report()
    section.set_report(value)
    assert not section.toggle.isChecked()
    section.toggle.click()
    assert not section.details.isHidden()
    text = section.details.toPlainText()
    for token in (value.source_name, value.source_sha256, '100mm', '50mm', 'mm',
                  '200.0', '100.0', 'xMidYMid meet', '0.5', '-0.5', '50.0',
                  '10.0', '30.0', '40.0', '0.01', '<b>Open centreline</b>', 'path-1'):
        assert token in text
    lower = text.lower()
    assert 'viewport' in lower and 'material bounds' in lower and 'mapping' in lower
    assert 'flipped' in lower and 'yes' in lower
    assert 'valid' in lower and 'invalid' in lower and 'empty' in lower
    assert 'open' in lower and 'closed' in lower
    assert 'historical' in lower and 'current' in lower and 'machine' in lower
    assert section.findChildren(QtWidgets.QLineEdit) == []
    assert not section.findChildren(QtWidgets.QPushButton)


def test_none_or_error_clears_success_never_shows_stale_data(section):
    section.set_report(report('old-source'))
    section.toggle.click()
    section.set_report(None)
    assert 'old-source' not in section.details.toPlainText()
    assert 'unavailable' in section.summary_label.text().lower()
    section.set_report(report('new-source'))
    section.set_report(None, error='<b>Unsupported schema</b>' + 'x' * 2000)
    assert 'new-source' not in section.details.toPlainText()
    assert '<b>Unsupported schema</b>' in section.summary_label.text()
    assert len(section.summary_label.text()) < 800
    assert 'historical' in section.summary_label.text().lower()


def test_wrong_record_type_replaces_previous_evidence_with_unavailable(section):
    section.set_report(report('previous.svg'))
    section.set_report({'source_name': 'pretend.svg'})
    assert section.details.toPlainText() == ''
    assert 'previous.svg' not in section.summary_label.text()
    assert 'unavailable' in section.summary_label.text().lower()


def test_unavailable_precision_and_source_dimensions_are_not_invented(section):
    value = report()
    coordinates = replace(value.coordinates, source_width=None, source_height=None,
                          source_units=('absent', 'absent'), view_box=None, flipped=False)
    section.set_report(replace(value, coordinates=coordinates, quality=replace(value.quality, precision_mm=None)))
    text = section.details.toPlainText().lower()
    assert 'absent' in text and 'unavailable' in text
    assert 'precision' in text
    assert '100mm' not in text and '0.01' not in text
    assert 'flipped' in text and 'no' in text


def test_notice_text_has_bounded_blocks_even_with_many_line_breaks(section):
    value = replace(report(), notices=tuple(SvgNotice('notice', '\n' * 512, str(i)) for i in range(200)))
    section.set_report(value)
    assert len(section.details.toPlainText()) < 250000
    assert section.details.document().blockCount() < 500
    for _ in range(10):
        section.set_report(value)
    assert section.details.toPlainText().count('notice') == 200


def test_attach_reuses_one_parent_owned_section_and_reads_only_retained_payload(qtbot):
    value = owner(qtbot, report_to_dict(report()))
    attach_import_report(value)
    widget = value.ui.mikrocam_import_report
    assert widget.parent() is value.ui
    assert value.ui.custom_box.count() == 1
    attach_import_report(value)
    assert value.ui.mikrocam_import_report is widget
    assert value.ui.custom_box.count() == 1
    assert not widget.isHidden()
    assert '<b>source.svg</b>' in widget.details.toPlainText()
    value.import_report = None
    attach_import_report(value)
    assert widget.isHidden()
    assert '<b>source.svg</b>' not in widget.details.toPlainText()


def test_distinct_owners_and_corrupt_second_selection_never_share_success(qtbot):
    first = owner(qtbot, report_to_dict(report('first.svg', '1' * 64)))
    second = owner(qtbot, report_to_dict(report('second.svg', '2' * 64)))
    attach_import_report(first)
    attach_import_report(second)
    assert first.ui.mikrocam_import_report is not second.ui.mikrocam_import_report
    assert 'first.svg' not in second.ui.mikrocam_import_report.details.toPlainText()
    second.import_report = {'schema_version': 999}
    attach_import_report(second)
    widget = second.ui.mikrocam_import_report
    assert not widget.isHidden()
    assert 'second.svg' not in widget.details.toPlainText()
    assert 'unavailable' in widget.summary_label.text().lower()
    assert 'first.svg' in first.ui.mikrocam_import_report.details.toPlainText()


def test_absent_old_field_hides_without_reading_source_or_geometry(qtbot):
    class OldOwner:
        def __getattr__(self, name):
            if name in ('source_file', 'solid_geometry', 'controller', 'filename'):
                pytest.fail(f'Report display accessed {name}')
            raise AttributeError(name)

    value = OldOwner()
    value.ui = owner(qtbot, None).ui
    attach_import_report(value)
    assert value.ui.mikrocam_import_report.isHidden()


def test_valid_report_display_and_toggle_do_not_inspect_or_mutate_owner_data(qtbot):
    class RetainedOwner:
        def __getattr__(self, name):
            pytest.fail(f'Report presentation inspected unrelated owner field: {name}')

    value = RetainedOwner()
    value.ui = owner(qtbot, None).ui
    value.import_report = report_to_dict(report())
    before = deepcopy(value.import_report)
    attach_import_report(value)
    value.ui.mikrocam_import_report.toggle.click()
    assert value.import_report == before
    assert '<b>source.svg</b>' in value.ui.mikrocam_import_report.details.toPlainText()


def test_parent_deletion_releases_section_without_global_retention(qtbot):
    value = owner(qtbot, report_to_dict(report()))
    attach_import_report(value)
    widget = value.ui.mikrocam_import_report
    value.ui.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    assert isdeleted(widget)
