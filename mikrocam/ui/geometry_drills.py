"""Explicit review of current Geometry contours; no inferred drill intent."""
import builtins
import gettext
from typing import Any
from PyQt6 import QtCore, QtWidgets
from mikrocam.bridge.geometry_drills import create_geometry_drills, load_geometry_review
from mikrocam.core.geometry_drills import group_geometry_selection
from mikrocam.core.geometry_drill_models import GeometryDrillReview

_ = getattr(builtins, '_', gettext.gettext)


def _plain(text: str) -> str:
    return ''.join(c if c.isprintable() else c.encode('unicode_escape').decode('ascii') for c in text)


def _measure(value: float) -> str:
    return f'{value:.6f}'.rstrip('0').rstrip('.') if abs(value) >= 1e-6 else f'{value:.6g}'


class GeometryDrillDialog(QtWidgets.QDialog):
    def __init__(self, app: Any, owner: object, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent if parent is not None else getattr(app, 'ui', None))
        self.app = app
        self.owner = owner
        self.review: GeometryDrillReview | None = None
        self.setWindowTitle(_('Geometry drill candidates'))
        self.setModal(True)
        self.resize(760, 600)
        layout = QtWidgets.QVBoxLayout(self)
        warning = self._label(layout)
        warning.setText(_('Circular contours are evidence, not a drill specification. '
                          'Verify hole intent and physical dimensions before creating Excellon.'))
        self.source_label = self._label(layout)
        self.analyse_button = QtWidgets.QPushButton(_('Analyse current Geometry'), self)
        layout.addWidget(self.analyse_button)
        self.table = QtWidgets.QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels([_('Select'), _('X mm'), _('Y mm'), _('Diameter mm'), _('Evidence')])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self._group_summary(layout)
        self.notices_view = QtWidgets.QPlainTextEdit(self)
        self.notices_view.setReadOnly(True)
        self.notices_view.setMaximumHeight(100)
        layout.addWidget(self.notices_view)
        form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit(self)
        form.addRow(_('New Excellon name'), self.name_edit)
        layout.addLayout(form)
        self.status_label = self._label(layout)
        buttons = QtWidgets.QHBoxLayout()
        self.create_button = QtWidgets.QPushButton(_('Create selected drills'), self)
        cancel_button = QtWidgets.QPushButton(_('Cancel'), self)
        buttons.addStretch(1)
        buttons.addWidget(self.create_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
        self.analyse_button.clicked.connect(self.analyse)
        self.create_button.clicked.connect(self.create_selected)
        cancel_button.clicked.connect(self.reject)
        self.table.itemChanged.connect(self._selection_changed)
        self.name_edit.textChanged.connect(self._selection_changed)
        self._invalidate()

    def _label(self, layout: QtWidgets.QVBoxLayout) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(self)
        label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        layout.addWidget(label)
        return label

    def _group_summary(self, layout: QtWidgets.QVBoxLayout) -> None:
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(45)
        scroll.setMaximumHeight(100)
        self.grouping_label = QtWidgets.QLabel(scroll)
        self.grouping_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.grouping_label.setWordWrap(True)
        scroll.setWidget(self.grouping_label)
        layout.addWidget(scroll)

    def _invalidate(self) -> None:
        self.review = None
        blocker = QtCore.QSignalBlocker(self.table)
        self.table.setRowCount(0)
        del blocker
        self.source_label.setText(_('No current Geometry review.'))
        self.grouping_label.setText(_('No candidates selected.'))
        self.notices_view.clear()
        self.status_label.setText(_('Analyse the fixed source, then explicitly select holes.'))
        self.create_button.setEnabled(False)

    @QtCore.pyqtSlot()
    def analyse(self) -> None:
        self._invalidate()
        try:
            self.review = load_geometry_review(self.owner)
        except (OSError, ValueError, TypeError, UnicodeError) as error:
            self.status_label.setText(_('Analysis failed: ') + _plain(str(error)[:512]))
            return
        self._show_review()

    def _show_review(self) -> None:
        review = self.review
        self.source_label.setText(_('Source: {name}\nCurrent units: {units}\nGeometry SHA-256: {sha}\n'
            'Circle fit: radial/chord min(0.01 mm, radius × 2%); duplicate centres 0.02 mm; '
            'diameter grouping 0.01 mm.').format(name=_plain(review.source_name),
            units=review.source_units, sha=review.geometry_sha256))
        blocker = QtCore.QSignalBlocker(self.table)
        self.table.setRowCount(len(review.candidates))
        for row, candidate in enumerate(review.candidates):
            checkbox = QtWidgets.QTableWidgetItem()
            checkbox.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            checkbox.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, checkbox)
            evidence = _('{source} / {role}; duplicates: {count}').format(
                source=_plain(candidate.source_id), role=candidate.role, count=candidate.duplicate_count)
            for column, value in enumerate((_measure(candidate.center_mm[0]), _measure(candidate.center_mm[1]),
                                            _measure(candidate.diameter_mm), evidence), 1):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem(value))
        del blocker
        self.notices_view.setPlainText('\n'.join(_plain(notice) for notice in review.notices))
        self.status_label.setText(_('Review candidates and explicitly select holes to create.') if review.candidates
                                  else _('No supported drill candidates. Review the source and notices.'))
        self._selection_changed()

    def _indices(self) -> tuple[int, ...]:
        return tuple(row for row in range(self.table.rowCount())
                     if self.table.item(row, 0).checkState() == QtCore.Qt.CheckState.Checked)

    def _selection_changed(self) -> None:
        indices = self._indices()
        self.create_button.setEnabled(False)
        if self.review is None or not indices:
            self.grouping_label.setText(_('No candidates selected.'))
            return
        try:
            tools = group_geometry_selection(self.review, indices)
        except ValueError as error:
            self.grouping_label.setText(_('Selection invalid: ') + _plain(str(error)[:512]))
            return
        lines = [_('Selected holes: {holes}; proposed tools: {tools}.').format(holes=len(indices), tools=len(tools))]
        for index, tool in enumerate(tools[:20], 1):
            lines.append(_('T{tool}: {diameter} mm; {count} holes').format(
                tool=index, diameter=_measure(tool.diameter_mm), count=len(tool.centers_mm)))
        if len(tools) > 20:
            lines.append(_('{count} additional tool groups omitted from this summary.').format(count=len(tools) - 20))
        self.grouping_label.setText('\n'.join(lines))
        name = self.name_edit.text().strip()
        try:
            valid_name = bool(name) and name.isprintable() and len(name.encode('utf-8')) <= 256
        except UnicodeEncodeError:
            valid_name = False
        self.create_button.setEnabled(valid_name)

    @QtCore.pyqtSlot()
    def create_selected(self) -> None:
        self._selection_changed()
        if not self.create_button.isEnabled() or self.review is None:
            self.status_label.setText(_('Select reviewed candidates and enter a printable output name.'))
            return
        try:
            created = create_geometry_drills(self.app, self.owner, self.review, self._indices(),
                                             self.name_edit.text().strip())
            if created is None or isinstance(created, (str, bool, int, float)):
                raise ValueError(_('Excellon creation did not return a completed object.'))
        except (ValueError, OSError, TypeError, UnicodeError) as error:
            self.status_label.setText(_('Creation failed: ') + _plain(str(error)[:512]))
            return
        self.accept()


def open_geometry_drills(app: Any) -> None:
    """Review only the selected Geometry, with ownership limited to one modal dialog."""
    owner = app.collection.get_active()
    if owner is None or getattr(owner, 'kind', None) != 'geometry':
        app.inform.emit('[ERROR] ' + _('Select a Geometry object before reviewing drill candidates.'))
        return
    dialog = GeometryDrillDialog(app, owner, getattr(app, 'ui', None))
    try:
        dialog.exec()
    finally:
        dialog.deleteLater()
