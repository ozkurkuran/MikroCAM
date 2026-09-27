"""Explicit manufacturing file collection, assignment and one existing-worker import."""

import builtins
import gettext
from pathlib import Path
from typing import Any
from PyQt6 import QtCore, QtGui, QtWidgets
from mikrocam.core.manufacturing_models import (
    FORMATS,
    ROLES,
    MAX_MANUFACTURING_FILES,
    ManufacturingFile,
    ManufacturingReview,
    ManufacturingAssignment,
)
from mikrocam.bridge.manufacturing_import import (
    inspect_manufacturing_files,
    review_manufacturing_files,
    import_manufacturing_review,
)

_ = getattr(builtins, "_", gettext.gettext)


def _plain(text: str) -> str:
    return "".join(
        c if c.isprintable() else c.encode("unicode_escape").decode("ascii")
        for c in text
    )


class ManufacturingImportWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(object)
    finished = QtCore.pyqtSignal(object)

    def __init__(
        self,
        app: Any,
        review: ManufacturingReview,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.app, self.review = app, review

    def run(self) -> None:
        receipts = []
        error = ""
        try:
            for receipt in import_manufacturing_review(self.app, self.review):
                receipts.append(receipt)
                self.progress.emit(receipt)
        except Exception as failure:
            error = str(failure)[:512]
        finally:
            self.finished.emit((tuple(receipts), error))


class ManufacturingImportDialog(QtWidgets.QDialog):
    def __init__(self, app: Any, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent if parent is not None else getattr(app, "ui", None))
        self.app = app
        self.files: tuple[ManufacturingFile, ...] = ()
        self.review: ManufacturingReview | None = None
        self.imported_indices: set[int] = set()
        self._paths: tuple[str, ...] = ()
        self._inspected_paths: tuple[str, ...] = ()
        self._worker: ManufacturingImportWorker | None = None
        self.busy = False
        self.setWindowTitle(_("Review production file set"))
        self.setModal(True)
        self.setAcceptDrops(True)
        self.resize(1100, 650)
        layout = QtWidgets.QVBoxLayout(self)
        warning = QtWidgets.QLabel(
            _(
                "Review source format, layer role and unit assumptions. One file creates one object; "
                "Gerber drill artwork remains Gerber. If a file fails, completed imports remain available and later files wait."
            ),
            self,
        )
        warning.setWordWrap(True)
        warning.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        layout.addWidget(warning)
        row = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton(_("Add files…"), self)
        self.inspect_button = QtWidgets.QPushButton(_("Inspect files"), self)
        self.review_button = QtWidgets.QPushButton(_("Review selected"), self)
        self.import_button = QtWidgets.QPushButton(_("Import reviewed"), self)
        for button in (
            self.add_button,
            self.inspect_button,
            self.review_button,
            self.import_button,
        ):
            row.addWidget(button)
        layout.addLayout(row)
        self.table = QtWidgets.QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels(
            [
                _("Select"),
                _("Source"),
                _("Format"),
                _("Role"),
                _("Units / evidence"),
                _("Output name"),
                _("Outcome"),
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.status_label = QtWidgets.QLabel(self)
        self.status_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.close_button = QtWidgets.QPushButton(_("Close"), self)
        layout.addWidget(self.close_button)
        self.add_button.clicked.connect(self._browse)
        self.inspect_button.clicked.connect(self.inspect_files)
        self.review_button.clicked.connect(self.review_selected)
        self.import_button.clicked.connect(self.import_selected)
        self.close_button.clicked.connect(self.reject)
        self.table.itemChanged.connect(self._invalidate)
        self._invalidate()

    def _invalidate(self) -> None:
        if self.busy:
            return
        self.review = None
        self.import_button.setEnabled(False)
        self.inspect_button.setEnabled(bool(self._paths))
        self.review_button.setEnabled(
            bool(self.files) and self._paths == self._inspected_paths
        )
        self.status_label.setText(
            _("Inspect and confirm selected assignments; edits require a new review.")
        )

    def add_paths(self, paths: tuple[str, ...]) -> None:
        if self.busy:
            return
        try:
            values = list(self._paths)
            duplicates = 0
            for path in paths:
                if type(path) is not str or not path:
                    raise ValueError("Local file paths must be nonempty text")
                canonical = str(Path(path).resolve())
                if len(canonical.encode("utf-8")) > 4096:
                    raise ValueError("File path exceeds 4096 UTF8 bytes")
                if canonical in values:
                    duplicates += 1
                else:
                    values.append(canonical)
            if len(values) > MAX_MANUFACTURING_FILES:
                raise ValueError("Select at most 64 files")
        except (ValueError, OSError, UnicodeError) as error:
            self.status_label.setText(
                _("Could not collect files: ") + _plain(str(error))
            )
            return
        self._paths = tuple(values)
        self._invalidate()
        self.status_label.setText(
            _(
                "Collected {count} paths; duplicate paths ignored: {duplicates}. Inspect to read files."
            ).format(count=len(values), duplicates=duplicates)
        )

    def _browse(self) -> None:
        paths, _filter = QtWidgets.QFileDialog.getOpenFileNames(
            self, _("Select production files"), ""
        )
        if paths:
            self.add_paths(tuple(paths))

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if (
            not self.busy
            and event.mimeData().hasUrls()
            and all(url.isLocalFile() for url in event.mimeData().urls())
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        if (
            self.busy
            or not event.mimeData().hasUrls()
            or not all(url.isLocalFile() for url in event.mimeData().urls())
        ):
            event.ignore()
            return
        self.add_paths(tuple(url.toLocalFile() for url in event.mimeData().urls()))
        event.acceptProposedAction()

    @QtCore.pyqtSlot()
    def inspect_files(self) -> None:
        if self.busy:
            return
        self._inspected_paths = ()
        self._invalidate()
        try:
            self.files = inspect_manufacturing_files(self._paths)
        except (ValueError, TypeError, OSError, UnicodeError) as error:
            self.status_label.setText(
                _("Inspection failed: ") + _plain(str(error)[:512])
            )
            return
        self._inspected_paths = self._paths
        self._show_files()

    def _combo(
        self, values: tuple[str, ...], current: str, enabled: bool
    ) -> QtWidgets.QComboBox:
        combo = QtWidgets.QComboBox(self.table)
        combo.addItems(values)
        combo.setCurrentText(current)
        combo.setEnabled(enabled)
        combo.currentIndexChanged.connect(self._invalidate)
        return combo

    def _show_files(self) -> None:
        blocker = QtCore.QSignalBlocker(self.table)
        self.table.setRowCount(len(self.files))
        for row, file in enumerate(self.files):
            self._show_row(row, file)
        del blocker
        self._invalidate()
        names = [v.inspection.source_name for v in self.files if v.inspection]
        hashes = [v.inspection.source_sha256 for v in self.files if v.inspection]
        warnings = []
        if len(names) != len(set(names)):
            warnings.append(
                _(
                    "Repeated basenames retained; distinguish full paths and output names."
                )
            )
        if len(hashes) != len(set(hashes)):
            warnings.append(_("Same content in distinct paths retained."))
        self.status_label.setText(
            _("Files inspected. Resolve unknown proposals explicitly before review.")
            + "\n"
            + "\n".join(warnings)
        )

    def _show_row(self, row: int, file: ManufacturingFile) -> None:
        known = file.inspection
        editable = known is not None and row not in self.imported_indices
        checkbox = QtWidgets.QTableWidgetItem()
        checkbox.setFlags(
            QtCore.Qt.ItemFlag.ItemIsEnabled
            | (
                QtCore.Qt.ItemFlag.ItemIsUserCheckable
                if editable
                else QtCore.Qt.ItemFlag.NoItemFlags
            )
        )
        checkbox.setCheckState(
            QtCore.Qt.CheckState.Checked if editable else QtCore.Qt.CheckState.Unchecked
        )
        self.table.setItem(row, 0, checkbox)
        source = QtWidgets.QTableWidgetItem(
            _plain(known.source_name if known else Path(file.path).name)
        )
        source.setToolTip(file.path)
        source.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(row, 1, source)
        self.table.setCellWidget(
            row,
            2,
            self._combo(
                ("unknown",) + FORMATS,
                known.format_hint if known else "unknown",
                editable,
            ),
        )
        self.table.setCellWidget(
            row,
            3,
            self._combo(
                ("unknown",) + ROLES, known.role_hint if known else "unknown", editable
            ),
        )
        detail = (
            (
                known.units_hint
                + "\n"
                + "\n".join([v.detail for v in known.evidence] + list(known.issues))
            )
            if known
            else file.error
        )
        item = QtWidgets.QTableWidgetItem(_plain(detail))
        item.setToolTip(_plain(detail))
        item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(row, 4, item)
        name = QtWidgets.QTableWidgetItem(Path(known.source_name).stem if known else "")
        name.setFlags(
            QtCore.Qt.ItemFlag.ItemIsEnabled
            | (
                QtCore.Qt.ItemFlag.ItemIsEditable
                if editable
                else QtCore.Qt.ItemFlag.NoItemFlags
            )
        )
        self.table.setItem(row, 5, name)
        self._outcome(
            row,
            _("Imported")
            if row in self.imported_indices
            else (_("Ready for review") if known else file.error),
        )

    def _outcome(self, row: int, text: str) -> None:
        blocker = QtCore.QSignalBlocker(self.table)
        item = QtWidgets.QTableWidgetItem(_plain(text))
        item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(row, 6, item)
        del blocker

    @QtCore.pyqtSlot()
    def review_selected(self) -> None:
        if self.busy:
            return
        self._invalidate()
        if self._paths != self._inspected_paths:
            self.status_label.setText(
                _("Inspect the current collected files before reviewing assignments.")
            )
            return
        try:
            assignments = tuple(
                ManufacturingAssignment(
                    row,
                    self.table.cellWidget(row, 2).currentText(),
                    self.table.cellWidget(row, 3).currentText(),
                    self.table.item(row, 5).text().strip(),
                )
                for row in range(len(self.files))
                if row not in self.imported_indices
                and self.table.item(row, 0).checkState() == QtCore.Qt.CheckState.Checked
            )
            self.review = review_manufacturing_files(self.files, assignments)
        except (ValueError, TypeError, OSError, UnicodeError) as error:
            self.status_label.setText(_("Review failed: ") + _plain(str(error)[:512]))
            return
        self.import_button.setEnabled(True)
        self.status_label.setText(
            _(
                "Reviewed {count} files. Explicit import uses current destination defaults."
            ).format(count=len(self.review.assignments))
        )

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        for widget in (
            self.add_button,
            self.inspect_button,
            self.review_button,
            self.import_button,
            self.close_button,
            self.table,
        ):
            widget.setEnabled(not busy)
        if not busy:
            self.import_button.setEnabled(False)
            self.inspect_button.setEnabled(bool(self._paths))
            self.review_button.setEnabled(
                bool(self.files) and self._paths == self._inspected_paths
            )

    @QtCore.pyqtSlot()
    def import_selected(self) -> None:
        if self.busy or self.review is None:
            return
        review = self.review
        self._set_busy(True)
        for assignment in review.assignments:
            self._outcome(assignment.source_index, _("Pending"))
        self._worker = ManufacturingImportWorker(self.app, review, self)
        self._worker.progress.connect(
            self._progress, QtCore.Qt.ConnectionType.QueuedConnection
        )
        self._worker.finished.connect(
            self._finished, QtCore.Qt.ConnectionType.QueuedConnection
        )
        self.status_label.setText(
            _("Import in progress. Editing and closing are locked.")
        )
        try:
            self.app.worker_task.emit({"fcn": self._worker.run, "params": []})
        except Exception as error:
            self._finished(((), str(error)))

    @QtCore.pyqtSlot(object)
    def _progress(self, receipt: object) -> None:
        index = receipt.source_index
        if receipt.owner is not None:
            self.imported_indices.add(index)
            blocker = QtCore.QSignalBlocker(self.table)
            self.table.item(index, 0).setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.table.item(index, 0).setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.table.item(index, 5).setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            del blocker
            self.table.cellWidget(index, 2).setEnabled(False)
            self.table.cellWidget(index, 3).setEnabled(False)
            self._outcome(
                index, _("Imported: ") + str(receipt.owner.obj_options["name"])
            )
        else:
            self._outcome(index, _("Failed: ") + receipt.error)

    @QtCore.pyqtSlot(object)
    def _finished(self, result: tuple) -> None:
        receipts, error = result
        self.review = None
        self._set_busy(False)
        failure = error or next((r.error for r in receipts if r.error), "")
        self.status_label.setText(
            (
                _("Import stopped: ") + _plain(failure) + "\n"
                if failure
                else _("Import finished. ")
            )
            + _(
                "Successful rows remain imported. Review remaining selected rows again before retry."
            )
        )
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def done(self, result: int) -> None:
        if not self.busy:
            super().done(result)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.busy:
            event.ignore()
        else:
            super().closeEvent(event)


def open_manufacturing_import(app: Any) -> None:
    dialog = ManufacturingImportDialog(app, getattr(app, "ui", None))
    try:
        dialog.exec()
    finally:
        dialog.deleteLater()
