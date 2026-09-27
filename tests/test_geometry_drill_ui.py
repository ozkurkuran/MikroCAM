from types import SimpleNamespace
import pytest
from PyQt6 import QtCore, QtWidgets
from mikrocam.core.geometry_drill_models import GeometryDrillCandidate as Candidate, GeometryDrillReview as Review
from mikrocam.ui.geometry_drills import GeometryDrillDialog, open_geometry_drills
import mikrocam.ui.geometry_drills as module


def review():
    return Review('<b>board</b>', 'MM', 'a' * 64, (
        Candidate((1, 2), .8, 'solid:0:exterior', 'exterior', 2),
        Candidate((3, 4), .805, 'solid:1:interior', 'interior'),
        Candidate((5, 6), 1.2, 'tool:2:line', 'closed-line')), ('Review <b>hole intent</b>.',))


@pytest.fixture
def dialog(qtbot, monkeypatch):
    parent = QtWidgets.QMainWindow()
    qtbot.addWidget(parent)
    app = SimpleNamespace(ui=parent)
    owner = SimpleNamespace(kind='geometry')
    calls = []
    monkeypatch.setattr(module, 'load_geometry_review', lambda obj: calls.append(obj) or review())
    value = GeometryDrillDialog(app, owner)
    qtbot.addWidget(value)
    return value, owner, calls


def select(value, row=0):
    value.table.item(row, 0).setCheckState(QtCore.Qt.CheckState.Checked)


def test_inert_fixed_source_unchecked_and_plain_evidence(dialog):
    value, owner, calls = dialog
    assert value.isModal() and value.parent() is value.app.ui
    assert value.review is None and not calls and not value.create_button.isEnabled()
    value.analyse()
    assert calls == [owner] and value.table.rowCount() == 3
    assert all(value.table.item(i, 0).checkState() == QtCore.Qt.CheckState.Unchecked for i in range(3))
    assert not value.create_button.isEnabled()
    assert value.source_label.textFormat() == QtCore.Qt.TextFormat.PlainText
    assert '<b>board</b>' in value.source_label.text() and 'a' * 64 in value.source_label.text()
    assert 'interior' in value.table.item(1, 4).text()
    assert '2' in value.table.item(0, 4).text()
    assert '<b>hole intent</b>' in value.notices_view.toPlainText()


def test_grouping_and_explicit_subset_creation(dialog, monkeypatch):
    value, owner, _ = dialog
    value.analyse()
    value.name_edit.setText('  reviewed holes  ')
    select(value, 0)
    select(value, 1)
    assert '0.8025' in value.grouping_label.text() and value.create_button.isEnabled()
    calls = []
    monkeypatch.setattr(module, 'create_geometry_drills', lambda *args: calls.append(args) or object())
    value.create_selected()
    assert calls == [(value.app, owner, value.review, (0, 1), 'reviewed holes')]
    assert value.result() == QtWidgets.QDialog.DialogCode.Accepted


@pytest.mark.parametrize('failure', [ValueError('source changed; analyse again'), OSError('export failed'), TypeError('bad tools')])
def test_failure_keeps_dialog_open_and_reanalysis_clears_selection(dialog, monkeypatch, failure):
    value, _, _ = dialog
    value.analyse()
    value.name_edit.setText('holes')
    select(value)
    def fail(*args):
        raise failure
    monkeypatch.setattr(module, 'create_geometry_drills', fail)
    value.create_selected()
    assert value.result() != QtWidgets.QDialog.DialogCode.Accepted
    assert str(failure) in value.status_label.text()
    value.analyse()
    assert not value.create_button.isEnabled()
    assert value.table.item(0, 0).checkState() == QtCore.Qt.CheckState.Unchecked


@pytest.mark.parametrize('result', [None, 'fail', False])
def test_creation_requires_actual_object(dialog, monkeypatch, result):
    value, _, _ = dialog
    value.analyse()
    value.name_edit.setText('holes')
    select(value)
    monkeypatch.setattr(module, 'create_geometry_drills', lambda *args: result)
    value.create_selected()
    assert value.result() != QtWidgets.QDialog.DialogCode.Accepted


def test_analysis_failure_drops_previous_review(dialog, monkeypatch):
    value, _, _ = dialog
    value.analyse()
    select(value)
    monkeypatch.setattr(module, 'load_geometry_review', lambda obj: (_ for _ in ()).throw(ValueError('missing geometry')))
    value.analyse()
    assert value.review is None and value.table.rowCount() == 0
    assert 'missing geometry' in value.status_label.text()


def test_invalid_grouping_and_name_disable_creation(dialog, monkeypatch):
    value, _, _ = dialog
    value.analyse()
    value.name_edit.setText('é' * 129)
    select(value)
    assert not value.create_button.isEnabled()
    value.name_edit.setText('holes')
    monkeypatch.setattr(module, 'group_geometry_selection', lambda *args: (_ for _ in ()).throw(ValueError('overlap')))
    value._selection_changed()
    assert not value.create_button.isEnabled() and 'overlap' in value.grouping_label.text()


@pytest.mark.parametrize('owner', [None, SimpleNamespace(kind='gerber')])
def test_open_requires_active_geometry(qtbot, monkeypatch, owner):
    parent = QtWidgets.QMainWindow()
    qtbot.addWidget(parent)
    messages = []
    app = SimpleNamespace(ui=parent, collection=SimpleNamespace(get_active=lambda: owner),
                          inform=SimpleNamespace(emit=messages.append))
    open_geometry_drills(app)
    assert messages and 'Geometry' in messages[0]


def test_empty_review_never_enables_create(dialog, monkeypatch):
    value, _, _ = dialog
    monkeypatch.setattr(module, 'load_geometry_review', lambda obj: Review('empty', 'MM', 'a' * 64, (), ('No circles.',)))
    value.analyse()
    value.name_edit.setText('holes')
    assert value.table.rowCount() == 0 and not value.create_button.isEnabled()
    assert 'No circles.' in value.notices_view.toPlainText()


def test_modal_open_uses_original_owner_and_releases_dialog(qtbot, monkeypatch):
    parent = QtWidgets.QMainWindow()
    qtbot.addWidget(parent)
    owner = SimpleNamespace(kind='geometry')
    app = SimpleNamespace(ui=parent, collection=SimpleNamespace(get_active=lambda: owner))
    calls = []
    class Dialog:
        def __init__(self, *args):
            calls.append(('new', args))
        def exec(self):
            calls.append(('exec',))
            raise RuntimeError('dialog error')
        def deleteLater(self):
            calls.append(('release',))
    monkeypatch.setattr(module, 'GeometryDrillDialog', Dialog)
    with pytest.raises(RuntimeError, match='dialog error'):
        open_geometry_drills(app)
    assert calls == [('new', (app, owner, parent)), ('exec',), ('release',)]
