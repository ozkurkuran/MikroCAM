"""Parent-owned explicit review of fixed selected current Excellon objects."""
import builtins
import gettext
from typing import Any
from PyQt6 import QtCore, QtWidgets
from mikrocam.bridge.excellon_merge import load_excellon_merge, create_excellon_merge
from mikrocam.core.excellon_merge_models import ExcellonMergeReview, OperationRef

_ = getattr(builtins, '_', gettext.gettext)


def _plain(text: str) -> str:
    return ''.join(c if c.isprintable() else c.encode('unicode_escape').decode('ascii') for c in text)


def _reference(ref: OperationRef) -> str:
    return f'{_plain(ref.source_name)} / {_plain(ref.tool_id)} / {ref.kind}[{ref.index}]'


def _owners(owners: tuple[object, ...]) -> None:
    if type(owners) is not tuple or not 2 <= len(owners) <= 64 or len({id(v) for v in owners}) != len(owners):
        raise ValueError('Merge requires an immutable tuple of 2..64 distinct source objects')


class ExcellonMergeDialog(QtWidgets.QDialog):
    def __init__(self, app: Any, owners: tuple[object, ...], parent: QtWidgets.QWidget | None = None) -> None:
        _owners(owners)
        super().__init__(parent if parent is not None else getattr(app, 'ui', None))
        self.app = app
        self.owners = owners
        self.review: ExcellonMergeReview | None = None
        self.setWindowTitle(_('Review Excellon merge'))
        self.setModal(True)
        self.resize(800, 720)
        layout = QtWidgets.QVBoxLayout(self)
        self.source_label = self._label(layout)
        self.analyse_button = QtWidgets.QPushButton(_('Analyse selected Excellons'), self)
        layout.addWidget(self.analyse_button)
        self.tools_table = QtWidgets.QTableWidget(0, 4, self)
        self.tools_table.setHorizontalHeaderLabels([_('Tool'), _('Diameter mm'), _('Drills'), _('Slots')])
        self.tools_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tools_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tools_table)
        self.map_view = self._view(layout, _('Complete source tool mapping'))
        self.duplicates_view = self._view(layout, _('Removed exact duplicates'))
        self.conflicts_view = self._view(layout, _('Blocking footprint conflicts'))
        form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit(self)
        form.addRow(_('New Excellon name'), self.name_edit)
        layout.addLayout(form)
        self.status_label = self._label(layout)
        buttons = QtWidgets.QHBoxLayout()
        self.create_button = QtWidgets.QPushButton(_('Create reviewed merge'), self)
        cancel_button = QtWidgets.QPushButton(_('Cancel'), self)
        buttons.addStretch(1)
        buttons.addWidget(self.create_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
        self.analyse_button.clicked.connect(self.analyse)
        self.create_button.clicked.connect(self.create_selected)
        cancel_button.clicked.connect(self.reject)
        self.name_edit.textChanged.connect(self._update_create)
        self._invalidate()

    def _label(self, layout: QtWidgets.QVBoxLayout) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(self)
        label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        layout.addWidget(label)
        return label

    def _view(self, layout: QtWidgets.QVBoxLayout, title: str) -> QtWidgets.QPlainTextEdit:
        label = self._label(layout)
        label.setText(title)
        view = QtWidgets.QPlainTextEdit(self)
        view.setReadOnly(True)
        view.setMinimumHeight(55)
        layout.addWidget(view, 1)
        return view

    def _invalidate(self) -> None:
        self.review = None
        self.tools_table.setRowCount(0)
        self.map_view.clear()
        self.duplicates_view.clear()
        self.conflicts_view.clear()
        self.source_label.setText(_('Fixed selected sources: {count}. No current review.').format(count=len(self.owners)))
        self.status_label.setText(_('Analyse first. The new destination uses current application defaults; '
                                  'source machining settings are not copied.'))
        self.create_button.setEnabled(False)

    @QtCore.pyqtSlot()
    def analyse(self) -> None:
        self._invalidate()
        try:
            self.review = load_excellon_merge(self.owners)
        except (ValueError, TypeError, OSError, UnicodeError) as error:
            self.status_label.setText(_('Analysis failed: ') + _plain(str(error)[:512]))
            return
        self._show_review()

    def _show_review(self) -> None:
        review = self.review
        self.source_label.setText('\n'.join(
            f'{_plain(source.source_name)} [{source.source_units}] SHA-256: {source.source_sha256}'
            for source in review.sources))
        self.tools_table.setRowCount(len(review.tools))
        for row, tool in enumerate(review.tools):
            values = (str(row + 1), repr(float(tool.diameter_mm)), str(len(tool.drills_mm)), str(len(tool.slots_mm)))
            for column, value in enumerate(values):
                self.tools_table.setItem(row, column, QtWidgets.QTableWidgetItem(value))
        self.tools_table.resizeColumnsToContents()
        self.map_view.setPlainText('\n'.join(
            f'{_plain(item.source_name)} / {_plain(item.source_tool)} → T{item.output_tool}' for item in review.tool_map))
        duplicate_lines = [_('Removed duplicate operations: {count}.').format(count=len(review.duplicates))]
        duplicate_lines.extend(f'{_reference(item.removed)} → {_reference(item.retained)}' for item in review.duplicates)
        self.duplicates_view.setPlainText('\n'.join(duplicate_lines))
        conflict_lines = [_('Blocking conflicts: {count}.').format(count=review.conflict_count)]
        conflict_lines.extend(f'{item.reason}: {_reference(item.first)} ↔ {_reference(item.second)}'
                              for item in review.conflicts)
        if review.conflict_count > len(review.conflicts):
            conflict_lines.append(_('{count} additional conflict details omitted.').format(
                count=review.conflict_count - len(review.conflicts)))
        self.conflicts_view.setPlainText('\n'.join(conflict_lines))
        self.status_label.setText(_('Conflicts block creation. Review or correct the sources.') if review.conflict_count
            else _('Review the complete mapping and duplicates. The new destination uses current application defaults; '
                   'source machining settings are not copied.'))
        self._update_create()

    def _update_create(self) -> None:
        name = self.name_edit.text().strip()
        try:
            valid_name = bool(name) and name.isprintable() and len(name.encode('utf-8')) <= 256
        except UnicodeEncodeError:
            valid_name = False
        self.create_button.setEnabled(self.review is not None and not self.review.conflict_count and valid_name)

    @QtCore.pyqtSlot()
    def create_selected(self) -> None:
        self._update_create()
        if not self.create_button.isEnabled():
            self.status_label.setText(_('Analyse nonconflicting sources and enter a printable output name.'))
            return
        try:
            created = create_excellon_merge(self.app, self.owners, self.review, self.name_edit.text().strip())
            if created is None or isinstance(created, (str, bool, int, float)):
                raise ValueError(_('Merge creation did not return a completed object.'))
        except (ValueError, TypeError, OSError, UnicodeError) as error:
            self.status_label.setText(_('Creation failed: ') + _plain(str(error)[:512]))
            return
        self.accept()


def open_excellon_merge(app: Any) -> None:
    """Use the complete current selection; never silently filter unsupported objects."""
    owners = tuple(app.collection.get_selected())
    try:
        _owners(owners)
        if any(getattr(owner, 'kind', None) != 'excellon' for owner in owners):
            raise ValueError('Every selected object must be Excellon')
    except ValueError:
        app.inform.emit('[ERROR] ' + _('Select 2..64 distinct Excellon objects before reviewing a merge.'))
        return
    dialog = ExcellonMergeDialog(app, owners, getattr(app, 'ui', None))
    try:
        dialog.exec()
    finally:
        dialog.deleteLater()
