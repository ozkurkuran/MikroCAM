"""Fixed-owner merge review requires explicit creation and exposes all evidence."""
from dataclasses import replace
from types import SimpleNamespace
import pytest
from PyQt6 import QtCore, QtWidgets
from mikrocam.core.excellon_tools import ExcellonTool
from mikrocam.core.excellon_merge_models import (MergeSourceTool, MergeSource, OperationRef,
    MergeToolMap, MergeDuplicate, MergeConflict, ExcellonMergeReview)
from mikrocam.ui.excellon_merge import ExcellonMergeDialog, open_excellon_merge
import mikrocam.ui.excellon_merge as module


def review():
    tool = ExcellonTool(.8, ((1, 2),), (((3, 4), (5, 4)),))
    sources = tuple(MergeSource(name, 'MM', 'a' * 64, (MergeSourceTool('int:1', tool),))
                    for name in ('<b>one</b>', 'two'))
    refs = tuple(OperationRef(name, 'int:1', 'drill', 0) for name in ('<b>one</b>', 'two'))
    return ExcellonMergeReview(sources, (tool,),
        tuple(MergeToolMap(name, 'int:1', 1) for name in ('<b>one</b>', 'two')),
        (MergeDuplicate(*refs),), (), 0)


@pytest.fixture
def dialog(qtbot, monkeypatch):
    parent = QtWidgets.QMainWindow()
    qtbot.addWidget(parent)
    owners = (SimpleNamespace(kind='excellon'), SimpleNamespace(kind='excellon'))
    app = SimpleNamespace(ui=parent)
    calls = []
    monkeypatch.setattr(module, 'load_excellon_merge', lambda values: calls.append(values) or review())
    value = ExcellonMergeDialog(app, owners)
    qtbot.addWidget(value)
    return value, owners, calls


def test_initial_inert_modal_and_complete_plain_review(dialog):
    value, owners, calls = dialog
    assert value.isModal() and value.parent() is value.app.ui
    assert value.owners is owners and value.review is None and not calls
    assert not value.create_button.isEnabled()

    value.analyse()
    assert calls == [owners] and value.tools_table.rowCount() == 1
    assert '0.8' in value.tools_table.item(0, 1).text()
    assert '<b>one</b>' in value.source_label.text()
    assert value.source_label.textFormat() == QtCore.Qt.TextFormat.PlainText
    assert 'two' in value.map_view.toPlainText() and '<b>one</b>' in value.map_view.toPlainText()
    assert 'drill' in value.duplicates_view.toPlainText()
    assert 'defaults' in value.status_label.text().lower()
    assert not value.create_button.isEnabled()


def test_distinct_exact_diameters_remain_distinguishable_in_review(dialog, monkeypatch):
    value, _, _ = dialog
    tools=(ExcellonTool(.3*25.4, ((0,0),), ()), ExcellonTool(7.62, ((10,0),), ()))
    monkeypatch.setattr(module,'load_excellon_merge',lambda owners:replace(review(),tools=tools))
    value.analyse()
    assert value.tools_table.item(0,1).text() != value.tools_table.item(1,1).text()


def test_explicit_create_uses_fixed_original_owners_and_review(dialog, monkeypatch):
    value, owners, _ = dialog
    value.analyse()
    value.name_edit.setText('  merged holes  ')
    assert value.create_button.isEnabled()
    calls = []
    monkeypatch.setattr(module, 'create_excellon_merge', lambda *args: calls.append(args) or object())
    value.create_selected()
    assert calls == [(value.app, owners, value.review, 'merged holes')]
    assert value.result() == QtWidgets.QDialog.DialogCode.Accepted


def test_conflict_count_blocks_creation_with_all_retained_details(dialog, monkeypatch):
    value, _, _ = dialog
    conflict = MergeConflict(OperationRef('<b>one</b>', 'int:1', 'drill', 0),
                             OperationRef('two', 'int:1', 'slot', 0), 'overlap')
    monkeypatch.setattr(module, 'load_excellon_merge', lambda owners: replace(review(), conflicts=(conflict,) * 200,
                                                                          conflict_count=201))
    value.analyse()
    value.name_edit.setText('merged')
    assert not value.create_button.isEnabled()
    assert '201' in value.conflicts_view.toPlainText() and 'overlap' in value.conflicts_view.toPlainText()
    monkeypatch.setattr(module, 'create_excellon_merge', lambda *args: pytest.fail('conflict cannot publish'))
    value.create_selected()
    assert value.result() != QtWidgets.QDialog.DialogCode.Accepted


@pytest.mark.parametrize('result', [None, 'fail', False])
def test_nonobject_result_keeps_open(dialog, monkeypatch, result):
    value, _, _ = dialog
    value.analyse()
    value.name_edit.setText('merged')
    monkeypatch.setattr(module, 'create_excellon_merge', lambda *args: result)
    value.create_selected()
    assert value.result() != QtWidgets.QDialog.DialogCode.Accepted


def test_stale_error_visible_then_analysis_failure_clears_all_evidence(dialog, monkeypatch):
    value, _, _ = dialog
    value.analyse()
    value.name_edit.setText('merged')
    def fail(*args):
        raise ValueError('Analyse again: source changed')
    monkeypatch.setattr(module, 'create_excellon_merge', fail)
    value.create_selected()
    assert 'source changed' in value.status_label.text()
    assert value.result() != QtWidgets.QDialog.DialogCode.Accepted
    monkeypatch.setattr(module, 'load_excellon_merge', fail)
    value.analyse()
    assert value.review is None and value.tools_table.rowCount() == 0
    assert not value.map_view.toPlainText() and not value.duplicates_view.toPlainText()
    assert not value.conflicts_view.toPlainText() and not value.create_button.isEnabled()


@pytest.mark.parametrize('owners', [(), (object(),), (object(),) * 65, [object(), object()]])
def test_constructor_requires_bounded_distinct_tuple(qtbot, owners):
    with pytest.raises(ValueError):
        ExcellonMergeDialog(SimpleNamespace(), owners)


def test_constructor_rejects_duplicate_identity(qtbot):
    owner = object()
    with pytest.raises(ValueError):
        ExcellonMergeDialog(SimpleNamespace(), (owner, owner))


@pytest.mark.parametrize('selection', [[], [SimpleNamespace(kind='excellon')],
    [SimpleNamespace(kind='excellon'), SimpleNamespace(kind='geometry')]])
def test_open_never_silently_filters_selected_owners(qtbot, selection):
    parent = QtWidgets.QMainWindow()
    qtbot.addWidget(parent)
    messages = []
    app = SimpleNamespace(ui=parent, collection=SimpleNamespace(get_selected=lambda: selection),
                          inform=SimpleNamespace(emit=messages.append))
    open_excellon_merge(app)
    assert messages and 'Excellon' in messages[0]


def test_open_preserves_selection_order_and_releases_on_error(qtbot, monkeypatch):
    parent = QtWidgets.QMainWindow()
    qtbot.addWidget(parent)
    owners = [SimpleNamespace(kind='excellon'), SimpleNamespace(kind='excellon')]
    app = SimpleNamespace(ui=parent, collection=SimpleNamespace(get_selected=lambda: owners))
    calls = []
    class Dialog:
        def __init__(self, *args):
            calls.append(args)
        def exec(self):
            raise RuntimeError('test')
        def deleteLater(self):
            calls.append('released')
    monkeypatch.setattr(module, 'ExcellonMergeDialog', Dialog)
    with pytest.raises(RuntimeError):
        open_excellon_merge(app)
    assert calls == [(app, tuple(owners), parent), 'released']


@pytest.mark.parametrize('name', ['', ' \n ', 'a\nb', 'é' * 129])
def test_invalid_name_never_reaches_creation(dialog, monkeypatch, name):
    value, _, _ = dialog
    value.analyse()
    value.name_edit.setText(name)
    assert not value.create_button.isEnabled()
    monkeypatch.setattr(module, 'create_excellon_merge', lambda *args: pytest.fail('invalid name cannot create'))
    value.create_selected()
    assert value.result() != QtWidgets.QDialog.DialogCode.Accepted


def test_create_before_review_is_inert(dialog, monkeypatch):
    value, _, _ = dialog
    value.name_edit.setText('merged')
    monkeypatch.setattr(module, 'create_excellon_merge', lambda *args: pytest.fail('review required'))
    value.create_selected()
    assert value.review is None and not value.create_button.isEnabled()
