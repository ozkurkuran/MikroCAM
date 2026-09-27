"""Transient explicit review of SVG artwork-derived drill candidates."""
import builtins
import gettext
from typing import Any

from PyQt6 import QtCore, QtWidgets

from mikrocam.bridge.svg_drills import create_drill_object, load_drill_review, verify_drill_source
from mikrocam.core.drill_groups import group_drill_selection
from mikrocam.core.svg_drills import DrillReview


_ = getattr(builtins, '_', gettext.gettext)


def _plain(text: str) -> str:
    return ''.join(char if char.isprintable() else char.encode('unicode_escape').decode('ascii') for char in text)


class SvgDrillDialog(QtWidgets.QDialog):
    def __init__(self, app: Any, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent if parent is not None else getattr(app, 'ui', None))
        self.app = app
        self.review: DrillReview | None = None
        self.setWindowTitle(_('SVG drill candidates'))
        self.setModal(True)
        self.resize(760, 600)
        layout = QtWidgets.QVBoxLayout(self)
        warning = QtWidgets.QLabel(_('Heuristic artwork evidence, not a drill specification. '
                                     'Verify hole intent and physical dimensions before creating Excellon.'))
        warning.setWordWrap(True)
        layout.addWidget(warning)
        file_row = QtWidgets.QHBoxLayout()
        self.path_edit = QtWidgets.QLineEdit(self)
        self.path_edit.setPlaceholderText(_('SVG source file'))
        self.browse_button = QtWidgets.QPushButton(_('Browse…'), self)
        file_row.addWidget(self.path_edit, 1)
        file_row.addWidget(self.browse_button)
        layout.addLayout(file_row)
        actions = QtWidgets.QHBoxLayout()
        self.flip_check = QtWidgets.QCheckBox(_('Flip vertically about viewport height'), self)
        self.flip_check.setChecked(True)
        self.analyse_button = QtWidgets.QPushButton(_('Analyse'), self)
        actions.addWidget(self.flip_check)
        actions.addStretch(1)
        actions.addWidget(self.analyse_button)
        layout.addLayout(actions)
        self.source_label = self._label(layout)
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
        self.browse_button.clicked.connect(self._browse)
        self.analyse_button.clicked.connect(self.analyse)
        self.create_button.clicked.connect(self.create_selected)
        cancel_button.clicked.connect(self.reject)
        self.path_edit.textChanged.connect(self._invalidate)
        self.flip_check.toggled.connect(self._invalidate)
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
        self.source_label.setText(_('No current source review.'))
        self.grouping_label.setText(_('No candidates selected.'))
        self.notices_view.clear()
        self.status_label.setText(_('Choose a source and analyse; file or flip changes require a new review.'))
        self.create_button.setEnabled(False)
        self.analyse_button.setEnabled(bool(self.path_edit.text().strip()))

    def _browse(self) -> None:
        filename, _filter = QtWidgets.QFileDialog.getOpenFileName(self, _('Select SVG source'), '', _('SVG files (*.svg)'))
        if filename:
            self.path_edit.setText(filename)

    @QtCore.pyqtSlot()
    def analyse(self) -> None:
        self._invalidate()
        path = self.path_edit.text().strip()
        if not path:
            self.status_label.setText(_('Select an SVG source file first.'))
            return
        try:
            self.review = load_drill_review(path, flip=self.flip_check.isChecked())
        except (OSError, ValueError, TypeError, UnicodeError) as error:
            self.status_label.setText(_('Analysis failed: ') + _plain(str(error)[:512]))
            return
        self._show_review()

    def _show_review(self) -> None:
        review = self.review
        self.source_label.setText(_('Source: {name}\nSHA-256: {sha}\nFlipped: {flip}\n'
            'Heuristic tolerances: radial/chord min(0.01 mm, radius × 2%); centres 0.02 mm; '
            'containment margin 0.01 mm; diameter grouping 0.01 mm.').format(
            name=_plain(review.source_name), sha=review.source_sha256,
            flip=_('Yes') if review.flipped else _('No')))
        blocker = QtCore.QSignalBlocker(self.table)
        self.table.setRowCount(len(review.candidates))
        for row, candidate in enumerate(review.candidates):
            checkbox = QtWidgets.QTableWidgetItem()
            checkbox.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            checkbox.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, checkbox)
            values = (repr(candidate.center_mm[0]), repr(candidate.center_mm[1]), repr(candidate.diameter_mm),
                      _plain(candidate.opening_id) + ' / ' + _plain(candidate.pad_id))
            for column, value in enumerate(values, 1):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem(value))
        del blocker
        self.notices_view.setPlainText('\n'.join(
            f'{_plain(notice.code)} [{_plain(notice.element_id)}]: {_plain(notice.message)}'
            for notice in review.notices))
        self.status_label.setText(_('Review candidates and explicitly select holes to create.') if review.candidates
                                  else _('No supported drill candidates. Review notices or correct the source.'))
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
            tools = group_drill_selection(self.review, indices)
        except ValueError as error:
            self.grouping_label.setText(_('Selection invalid: ') + _plain(str(error)[:512]))
            return
        lines = [_('Selected holes: {holes}; proposed tools: {tools}.').format(holes=len(indices), tools=len(tools))]
        for index, tool in enumerate(tools[:20], 1):
            lines.append(_('T{tool}: {diameter} mm; {count} holes').format(
                tool=index, diameter=repr(tool.diameter_mm), count=len(tool.centers_mm)))
        if len(tools) > 20:
            lines.append(_('{count} additional tool groups omitted from this summary.').format(count=len(tools)-20))
        self.grouping_label.setText('\n'.join(lines))
        name = self.name_edit.text().strip()
        self.create_button.setEnabled(0 < len(name) <= 256 and name.isprintable())

    @QtCore.pyqtSlot()
    def create_selected(self) -> None:
        self._selection_changed()
        if not self.create_button.isEnabled() or self.review is None:
            self.status_label.setText(_('Select reviewed candidates and enter a printable output name.'))
            return
        try:
            verify_drill_source(self.path_edit.text().strip(), self.review)
        except (ValueError, OSError, TypeError) as error:
            self._invalidate()
            self.status_label.setText(_('Source changed or unavailable: ') + _plain(str(error)[:512])
                                      + '\n' + _('Reanalyse the SVG before creating drills.'))
            return
        try:
            created = create_drill_object(self.app, self.review, self._indices(), self.name_edit.text().strip())
            if created is None or created == 'fail':
                raise ValueError(_('Excellon creation did not return a completed object.'))
        except (ValueError, OSError, TypeError) as error:
            self.status_label.setText(_('Creation failed: ') + _plain(str(error)[:512]))
            return
        self.accept()


def open_svg_drills(app: Any) -> None:
    """Run one parent-owned modal review; closing never retains a global dialog."""
    dialog = SvgDrillDialog(app, getattr(app, 'ui', None))
    try:
        dialog.exec()
    finally:
        dialog.deleteLater()
