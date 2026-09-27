from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
import threading
import pytest
from PyQt6 import QtCore, QtWidgets
from test_manufacturing_models import file, inspection
from mikrocam.core.manufacturing_models import ManufacturingReview, ManufacturingFile
from mikrocam.ui.manufacturing_import import ManufacturingImportDialog
import mikrocam.ui.manufacturing_import as module


@pytest.fixture
def dialog(qtbot, monkeypatch, tmp_path):
    parent = QtWidgets.QMainWindow()
    qtbot.addWidget(parent)
    dispatch = []
    app = SimpleNamespace(ui=parent, worker_task=SimpleNamespace(emit=dispatch.append))

    def inspect(paths):
        return tuple(
            ManufacturingFile(path, b"data", inspection(source_name=Path(path).name))
            for path in paths
        )

    monkeypatch.setattr(module, "inspect_manufacturing_files", inspect)
    monkeypatch.setattr(
        module,
        "review_manufacturing_files",
        lambda files, assignments: ManufacturingReview(files, assignments),
    )
    value = ManufacturingImportDialog(app)
    qtbot.addWidget(value)
    value.add_paths((str(tmp_path / "one.gbr"), str(tmp_path / "two.gbr")))
    return value, dispatch


def test_collect_no_io_then_inspect_and_explicit_review(dialog):
    value, dispatch = dialog
    assert (
        value.isModal()
        and value.acceptDrops()
        and value.files == ()
        and value.review is None
    )
    assert not dispatch and not value.import_button.isEnabled()
    value.inspect_files()
    assert len(value.files) == 2 and value.table.rowCount() == 2
    value.review_selected()
    assert value.review is not None and value.import_button.isEnabled()
    value.table.item(0, 5).setText("edited")
    assert value.review is None and not value.import_button.isEnabled()


def test_duplicate_paths_and_same_content_keep_rows(dialog):
    value, _ = dialog
    value.add_paths((value._paths[0],))
    assert len(value._paths) == 2 and "duplicate" in value.status_label.text().lower()
    value.inspect_files()
    assert (
        value.table.rowCount() == 2
        and "same content" in value.status_label.text().lower()
    )
    assert value.table.item(0, 1).toolTip() == value.files[0].path


def test_unknown_and_failed_rows_visible_without_silent_assignment(dialog, monkeypatch):
    value, _ = dialog
    paths = value._paths
    monkeypatch.setattr(
        module,
        "inspect_manufacturing_files",
        lambda paths: (
            ManufacturingFile(
                paths[0],
                b"data",
                inspection(format_hint="unknown", role_hint="unknown"),
            ),
            ManufacturingFile(paths[1], b"", None, "cannot read"),
        ),
    )
    value.inspect_files()
    assert value.table.item(0, 0).checkState() == QtCore.Qt.CheckState.Checked
    assert value.table.item(1, 0).checkState() == QtCore.Qt.CheckState.Unchecked
    assert not value.table.cellWidget(1, 2).isEnabled()
    value.review_selected()
    assert value.review is None and not value.import_button.isEnabled()
    value.table.cellWidget(0, 2).setCurrentText("gerber")
    value.table.cellWidget(0, 3).setCurrentText("Other")
    value.review_selected()
    assert value.review.assignments[0].role == "Other"


def test_single_worker_success_failure_pending_retry_no_repeat(
    dialog, monkeypatch, qtbot
):
    value, dispatch = dialog
    value.add_paths((str(Path(value._paths[0]).parent / "three.gbr"),))
    value.inspect_files()
    value.review_selected()
    owner = SimpleNamespace(obj_options={"name": "actual published name"})
    receipt = lambda index, owner=None, error="": SimpleNamespace(
        source_index=index, owner=owner, error=error
    )
    seen = []

    def import_review(app, review):
        seen.append(
            (threading.get_ident(), tuple(a.source_index for a in review.assignments))
        )
        yield receipt(0, owner)
        yield receipt(1, error="parser failed")

    monkeypatch.setattr(module, "import_manufacturing_review", import_review)
    value.import_selected()
    assert len(dispatch) == 1 and value.busy and not value.close_button.isEnabled()
    value.reject()
    assert value.busy
    job = dispatch[0]
    thread = threading.Thread(target=lambda: job["fcn"](*job["params"]))
    thread.start()
    qtbot.waitUntil(lambda: not value.busy, timeout=3000)
    thread.join()
    assert seen[0][0] != threading.get_ident() and seen[0][1] == (0, 1, 2)
    assert value.imported_indices == {0}
    assert value.table.item(0, 0).checkState() == QtCore.Qt.CheckState.Unchecked
    assert "actual published name" in value.table.item(0, 6).text()
    assert (
        "parser failed" in value.table.item(1, 6).text()
        and "pending" in value.table.item(2, 6).text().lower()
    )
    assert value.review is None and not value.import_button.isEnabled()
    value.review_selected()
    assert tuple(a.source_index for a in value.review.assignments) == (1, 2)


def test_worker_exception_clears_review_and_unlocks_without_receipts(
    dialog, monkeypatch, qtbot
):
    value, dispatch = dialog
    value.inspect_files()
    value.review_selected()

    def fail(*args):
        raise ValueError("source changed before import")

    monkeypatch.setattr(module, "import_manufacturing_review", fail)
    value.import_selected()
    job = dispatch[0]
    thread = threading.Thread(target=lambda: job["fcn"](*job["params"]))
    thread.start()
    qtbot.waitUntil(lambda: not value.busy, timeout=3000)
    thread.join()
    assert (
        value.review is None
        and not value.imported_indices
        and value.close_button.isEnabled()
    )
    assert "source changed" in value.status_label.text()


def test_new_paths_require_inspection_before_old_rows_can_review(dialog):
    value, _ = dialog
    value.inspect_files()
    value.review_selected()
    assert value.review is not None
    value.add_paths((str(Path(value._paths[0]).parent / "new.gbr"),))
    value.review_selected()
    assert value.review is None and not value.review_button.isEnabled()


def test_local_drop_collects_without_read_and_remote_urls_rejected(dialog):
    from PyQt6 import QtGui

    value, _ = dialog
    remote = QtCore.QMimeData()
    remote.setUrls([QtCore.QUrl("https://example.invalid/board.gbr")])
    event = QtGui.QDragEnterEvent(
        QtCore.QPoint(0, 0),
        QtCore.Qt.DropAction.CopyAction,
        remote,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    value.dragEnterEvent(event)
    assert not event.isAccepted()
    local = QtCore.QMimeData()
    local.setUrls(
        [QtCore.QUrl.fromLocalFile(str(Path(value._paths[0]).parent / "dropped.gbr"))]
    )
    drop = QtGui.QDropEvent(
        QtCore.QPointF(0, 0),
        QtCore.Qt.DropAction.CopyAction,
        local,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    value.dropEvent(drop)
    assert drop.isAccepted() and len(value._paths) == 3 and value.files == ()


def test_busy_prevents_collection_and_close_event(dialog, monkeypatch):
    from PyQt6 import QtGui

    value, _ = dialog
    value.inspect_files()
    value.review_selected()
    value.import_selected()
    paths = value._paths
    value.add_paths((str(Path(paths[0]).parent / "ignored.gbr"),))
    event = QtGui.QCloseEvent()
    value.closeEvent(event)
    assert not event.isAccepted() and value._paths == paths
    value._finished(((), "test cleanup"))
