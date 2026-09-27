"""Explicit GUI drill review never creates from stale or unselected evidence."""
from types import SimpleNamespace

import pytest
from PyQt6 import QtCore, QtWidgets
from PyQt6.sip import isdeleted

from mikrocam.core.svg_drills import DrillCandidate, DrillReview
from mikrocam.core.svg_models import SvgNotice
from mikrocam.ui.svg_drills import SvgDrillDialog, open_svg_drills
import mikrocam.ui.svg_drills as module


def review():
    return DrillReview('<b>source.svg</b>', 'a' * 64, True,
        (DrillCandidate((1., 2.), .8, 'opening-1', 'pad-1'),
         DrillCandidate((3., 4.), .805, 'opening-2', 'pad-2'),
         DrillCandidate((5., 6.), 1.2, 'opening-3', 'pad-3')),
        (SvgNotice('heuristic', '<b>Artwork is evidence, not drill intent</b>\nReview it.'),))


@pytest.fixture
def dialog(qtbot, monkeypatch):
    parent = QtWidgets.QMainWindow()
    qtbot.addWidget(parent)
    app = SimpleNamespace(ui=parent)
    calls = []
    monkeypatch.setattr(module, 'load_drill_review', lambda path, **kwargs: calls.append((path, kwargs)) or review())
    monkeypatch.setattr(module, 'verify_drill_source', lambda *args: None)
    value = SvgDrillDialog(app, parent)
    yield value, calls
    value.reject()


def check(value, row):
    value.table.item(row, 0).setCheckState(QtCore.Qt.CheckState.Checked)


def test_initial_modal_inert_and_candidates_unchecked(dialog):
    value, calls = dialog
    assert value.isModal() and value.parent() is value.app.ui
    assert not value.create_button.isEnabled() and value.table.rowCount() == 0
    assert not calls
    value.path_edit.setText('board.svg')
    value.analyse()
    assert calls == [('board.svg', {'flip': True})]
    assert value.table.rowCount() == 3
    assert all(value.table.item(row, 0).checkState() == QtCore.Qt.CheckState.Unchecked for row in range(3))
    assert not value.create_button.isEnabled()
    assert value.table.editTriggers() == QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers


def test_plain_source_hash_tolerances_notices_and_grouping(dialog):
    value, _ = dialog
    value.path_edit.setText('board.svg')
    value.analyse()
    text = value.source_label.text() + value.notices_view.toPlainText() + value.status_label.text()
    for token in ('<b>source.svg</b>', 'a' * 64, '0.01', '0.02', '2%', 'heuristic', '<b>Artwork'):
        assert token in text
    assert value.source_label.textFormat() == QtCore.Qt.TextFormat.PlainText
    assert value.status_label.textFormat() == QtCore.Qt.TextFormat.PlainText
    assert value.notices_view.isReadOnly()
    value.name_edit.setText('drills')
    check(value, 0)
    check(value, 1)
    assert '0.8025' in value.grouping_label.text()
    assert '2' in value.grouping_label.text()
    check(value, 2)
    assert '1.2' in value.grouping_label.text()
    assert value.create_button.isEnabled()


@pytest.mark.parametrize('change', ['path', 'flip'])
def test_input_change_clears_rows_review_and_disables_create(dialog, change, monkeypatch):
    value, _ = dialog
    value.path_edit.setText('first.svg')
    value.analyse()
    value.name_edit.setText('drills')
    check(value, 0)
    assert value.create_button.isEnabled()
    if change == 'path':
        value.path_edit.setText('other.svg')
    else:
        value.flip_check.setChecked(False)
    assert value.table.rowCount() == 0 and not value.create_button.isEnabled()
    assert '<b>source.svg</b>' not in value.source_label.text()
    assert value.notices_view.toPlainText() == ''
    monkeypatch.setattr(module, 'create_drill_object', lambda *args: pytest.fail('Stale review cannot create'))
    value.create_selected()
    assert value.result() != QtWidgets.QDialog.DialogCode.Accepted


def test_only_explicit_subset_and_trimmed_name_reaches_bridge(dialog, monkeypatch):
    value, _ = dialog
    calls = []
    monkeypatch.setattr(module, 'create_drill_object', lambda *args: calls.append(args) or object())
    value.path_edit.setText('board.svg')
    value.analyse()
    value.name_edit.setText('  reviewed drills  ')
    check(value, 2)
    check(value, 0)
    value.create_selected()
    assert len(calls) == 1
    assert calls[0] == (value.app, review(), (0, 2), 'reviewed drills')
    assert value.result() == QtWidgets.QDialog.DialogCode.Accepted


def test_source_is_verified_before_creation(dialog, monkeypatch):
    value, _ = dialog
    calls = []
    monkeypatch.setattr(module, 'verify_drill_source', lambda path, source: calls.append(('verify', path, source)))
    monkeypatch.setattr(module, 'create_drill_object', lambda *args: calls.append(('create', args)) or object())
    value.path_edit.setText('board.svg')
    value.analyse()
    value.name_edit.setText('drills')
    check(value, 0)
    value.create_selected()
    assert calls[0] == ('verify', 'board.svg', review())
    assert calls[1][0] == 'create' and len(calls) == 2


@pytest.mark.parametrize('exception', [ValueError('Source content changed'), OSError('Source no longer available')])
def test_changed_or_missing_source_clears_review_before_refusing_create(dialog, monkeypatch, exception):
    value, _ = dialog
    def fail(*args):
        raise exception
    monkeypatch.setattr(module, 'verify_drill_source', fail)
    monkeypatch.setattr(module, 'create_drill_object', lambda *args: pytest.fail('Changed source must not publish'))
    value.path_edit.setText('board.svg')
    value.analyse()
    value.name_edit.setText('drills')
    check(value, 0)
    value.create_selected()
    assert value.review is None and value.table.rowCount() == 0
    assert not value.create_button.isEnabled()
    assert 'a' * 64 not in value.source_label.text()
    assert value.notices_view.toPlainText() == ''
    assert 'reanalyse' in value.status_label.text().lower()
    assert str(exception) in value.status_label.text()
    assert value.result() != QtWidgets.QDialog.DialogCode.Accepted


def test_empty_selection_name_and_cancel_never_create(dialog, monkeypatch):
    value, _ = dialog
    monkeypatch.setattr(module, 'create_drill_object', lambda *args: pytest.fail('Creation must be explicit'))
    value.path_edit.setText('board.svg')
    value.analyse()
    value.create_selected()
    check(value, 0)
    value.create_selected()
    assert not value.create_button.isEnabled()
    value.reject()
    assert value.result() == QtWidgets.QDialog.DialogCode.Rejected


@pytest.mark.parametrize('name', [' ', 'x' * 257, 'bad\x00name'])
def test_invalid_name_does_not_enable_create(dialog, name):
    value, _ = dialog
    value.path_edit.setText('board.svg')
    value.analyse()
    check(value, 0)
    value.name_edit.setText(name)
    assert not value.create_button.isEnabled()


def test_analysis_failure_clears_previous_success_and_is_actionable(dialog, monkeypatch):
    value, _ = dialog
    value.path_edit.setText('board.svg')
    value.analyse()
    value.name_edit.setText('drills')
    check(value, 0)
    def fail(*args, **kwargs):
        raise ValueError('Unsupported clipping; outline in your editor')
    monkeypatch.setattr(module, 'load_drill_review', fail)
    value.analyse()
    assert value.table.rowCount() == 0
    assert not value.create_button.isEnabled()
    assert 'outline in your editor' in value.status_label.text()
    assert 'a' * 64 not in value.source_label.text()


def test_no_candidates_displays_reason_without_creation(dialog, monkeypatch):
    value, _ = dialog
    empty = DrillReview('empty.svg', 'b' * 64, False, (), (SvgNotice('no-holes', 'No supported openings'),))
    monkeypatch.setattr(module, 'load_drill_review', lambda *args, **kwargs: empty)
    value.path_edit.setText('empty.svg')
    value.analyse()
    assert value.table.rowCount() == 0 and not value.create_button.isEnabled()
    assert 'No supported openings' in value.notices_view.toPlainText()
    assert 'no' in value.status_label.text().lower()


def test_creation_failure_stays_open_without_false_success(dialog, monkeypatch):
    value, _ = dialog
    value.path_edit.setText('board.svg')
    value.analyse()
    value.name_edit.setText('drills')
    check(value, 0)
    def fail(*args):
        raise ValueError('Excellon export failed')
    monkeypatch.setattr(module, 'create_drill_object', fail)
    value.create_selected()
    assert value.result() != QtWidgets.QDialog.DialogCode.Accepted
    assert 'export failed' in value.status_label.text()


@pytest.mark.parametrize('result', [None, 'fail'])
def test_absent_creation_result_is_not_accepted_as_success(dialog, monkeypatch, result):
    value, _ = dialog
    value.path_edit.setText('board.svg')
    value.analyse()
    value.name_edit.setText('drills')
    check(value, 0)
    monkeypatch.setattr(module, 'create_drill_object', lambda *args: result)
    value.create_selected()
    assert value.result() != QtWidgets.QDialog.DialogCode.Accepted
    assert 'failed' in value.status_label.text().lower()


def test_browse_cancel_preserves_review_and_selection(dialog, monkeypatch):
    value, _ = dialog
    value.path_edit.setText('board.svg')
    value.analyse()
    check(value, 0)
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileName', lambda *args, **kwargs: ('', ''))
    value.browse_button.click()
    assert value.path_edit.text() == 'board.svg' and value.table.rowCount() == 3
    assert value.table.item(0, 0).checkState() == QtCore.Qt.CheckState.Checked


def test_transient_entry_parent_lifetime_and_repeated_open(qtbot):
    parent = QtWidgets.QMainWindow()
    qtbot.addWidget(parent)
    app = SimpleNamespace(ui=parent)
    dialogs = []
    for _ in range(3):
        def reject_modal():
            current = QtWidgets.QApplication.activeModalWidget()
            assert isinstance(current, SvgDrillDialog)
            dialogs.append(current)
            current.reject()
        QtCore.QTimer.singleShot(0, reject_modal)
        open_svg_drills(app)
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    assert all(isdeleted(value) for value in dialogs)
