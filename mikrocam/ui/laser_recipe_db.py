"""Thin recipe-library controls: catalog choices, search, load/save and JSON migration."""
import builtins
from collections.abc import Callable
import gettext
from pathlib import Path

from PyQt6 import QtCore, QtWidgets

from mikrocam.core import laser_recipe_db as db
from mikrocam.core.laser_recipe_db_json import import_recipe_texts
from mikrocam.laser.recipe_db_store import StaleDatabaseError, load_database, new_id, save_database
from .laser_recipe import LaserRecipeEditor, save_recipe_file

_ = getattr(builtins, '_', gettext.gettext)
HEADERS = ('Reçete', 'Malzeme', 'Makine', 'Lens', 'Geçiş')
# table attribute, model class, optional number field, put, remove, combo title, number label
CATALOGS = {
    'material': ('materials', db.Material, 'thickness_mm', db.put_material, db.remove_material,
                 'Malzeme', 'Kalınlık mm (isteğe bağlı)'),
    'lens': ('lenses', db.Lens, 'focal_length_mm', db.put_lens, db.remove_lens,
             'Lens', 'Odak uzaklığı mm (isteğe bağlı)'),
}


class CatalogDialog(QtWidgets.QDialog):
    """Name, one optional user-supplied millimetre value and notes; nothing is prefilled."""

    def __init__(self, title: str, number_label: str, current: tuple | None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        form = QtWidgets.QFormLayout(self)
        self.name = QtWidgets.QLineEdit()
        self.number = QtWidgets.QLineEdit()
        self.notes = QtWidgets.QPlainTextEdit()
        if current is not None:
            self.name.setText(current[0])
            self.number.setText('' if current[1] is None else repr(current[1]))
            self.notes.setPlainText(current[2])
        form.addRow(_('Ad'), self.name)
        form.addRow(number_label, self.number)
        form.addRow(_('Not'), self.notes)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok
                                             | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self) -> tuple[str, float | None, str]:
        text = self.number.text().strip()
        try:
            number = float(text) if text else None
        except ValueError as error:
            raise ValueError(_('Sayısal alan boş bırakılmalı veya sayı olmalı.')) from error
        return self.name.text(), number, self.notes.toPlainText()


class LaserRecipeLibrary(QtWidgets.QGroupBox):
    """Edit the on-disk recipe database through core operations; never invent values."""

    def __init__(self, editor: LaserRecipeEditor, path: str | Path,
                 parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(_('Reçete veritabanı'), parent)
        self.editor = editor
        self.path = Path(path)
        self.database = db.LaserRecipeDatabase()
        self.revision: str | None = None
        self.writable = False
        self._write_controls: list[QtWidgets.QWidget] = []
        layout = QtWidgets.QVBoxLayout(self)
        self.path_label = QtWidgets.QLabel(_('Dosya: {path}').format(path=self.path))
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)
        grid = QtWidgets.QGridLayout()
        self.material_combo = self._row(grid, 0, _('Malzeme'), (
            (_('Yeni…'), self.add_material), (_('Düzenle…'), self.edit_material), (_('Sil'), self.delete_material)))
        self.lens_combo = self._row(grid, 1, _('Lens'), (
            (_('Yeni…'), self.add_lens), (_('Düzenle…'), self.edit_lens), (_('Sil'), self.delete_lens)))
        self.machine_combo = self._row(grid, 2, _('Makine'), (
            (_('Editör profilini kaydet'), self.save_machine), (_('Sil'), self.delete_machine)))
        layout.addLayout(grid)
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText(_('Ara: reçete, malzeme, makine veya lens'))
        self.search_edit.textChanged.connect(self._refresh_table)
        layout.addWidget(self.search_edit)
        self._build_table(layout)
        self._build_actions(layout)
        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.reload()

    def _button(self, layout: QtWidgets.QLayout, text: str, callback: Callable, writes: bool) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        button.clicked.connect(lambda checked=False: callback())
        layout.addWidget(button)
        if writes:
            self._write_controls.append(button)
        return button

    def _row(self, grid: QtWidgets.QGridLayout, row: int, label: str, actions: tuple) -> QtWidgets.QComboBox:
        combo = QtWidgets.QComboBox()
        grid.addWidget(QtWidgets.QLabel(label), row, 0)
        grid.addWidget(combo, row, 1)
        buttons = QtWidgets.QHBoxLayout()
        for text, callback in actions:
            self._button(buttons, text, callback, True)
        grid.addLayout(buttons, row, 2)
        return combo

    def _build_table(self, layout: QtWidgets.QVBoxLayout) -> None:
        self.table = QtWidgets.QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels([_(text) for text in HEADERS])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(110)
        self.table.setMaximumHeight(220)
        self.table.doubleClicked.connect(lambda index: self.load_selected())
        layout.addWidget(self.table)

    def _build_actions(self, layout: QtWidgets.QVBoxLayout) -> None:
        first, second = QtWidgets.QHBoxLayout(), QtWidgets.QHBoxLayout()
        self.load_button = self._button(first, _('Editöre yükle'), self.load_selected, False)
        self.save_button = self._button(first, _('Editördekini kaydet'), self.save_current, True)
        self.delete_button = self._button(first, _('Reçeteyi sil'), self.delete_selected, True)
        self.import_button = self._button(second, _('JSON içe aktar…'), self.import_files, True)
        self.export_button = self._button(second, _('JSON dışa aktar…'), self.export_selected, False)
        self.reload_button = self._button(second, _('Yeniden yükle'), self.reload, False)
        layout.addLayout(first)
        layout.addLayout(second)

    # Persistence -----------------------------------------------------------------------
    def reload(self) -> None:
        """Read the file again; an unreadable file leaves the library read-only and untouched."""
        try:
            self.database, self.revision = load_database(self.path)
            self.writable = True
            self._status(_('{count} reçete kayıtlı.').format(count=len(self.database.recipes)))
        except (OSError, ValueError) as error:
            self.database, self.revision, self.writable = db.LaserRecipeDatabase(), None, False
            self._status(_('Veritabanı açılamadı; salt okunur, dosyaya yazılmayacak: {message}').format(message=error))
        for control in self._write_controls:
            control.setEnabled(self.writable)
        self._refresh()

    def _commit(self, database: db.LaserRecipeDatabase, message: str) -> bool:
        if not self.writable:
            self._status(_('Veritabanı salt okunur; değişiklik kaydedilmedi.'))
            return False
        try:
            self.revision = save_database(self.path, database, self.revision)
        except StaleDatabaseError:
            self._status(_("Veritabanı dosyası başka bir yerde değişti; 'Yeniden yükle' ile güncelleyin."))
            return False
        except (OSError, ValueError) as error:
            self._error(error)
            return False
        self.database = database
        self._refresh()
        self._status(message)
        return True

    # Display ---------------------------------------------------------------------------
    def _status(self, text: str) -> None:
        self.status_label.setText(text)

    def _error(self, error: Exception) -> None:
        self._status(_('Hata: {message}').format(message=_(str(error))))

    @staticmethod
    def _fill(combo: QtWidgets.QComboBox, items: tuple, unspecified: bool, selected: object = ...) -> None:
        current = combo.currentData() if selected is ... else selected
        with QtCore.QSignalBlocker(combo):
            combo.clear()
            if unspecified:
                combo.addItem(_('Belirtilmemiş'), None)
            for item in items:
                combo.addItem(item.name, item.id)
            index = combo.findData(current)
            combo.setCurrentIndex(max(index, 0))

    def _refresh(self) -> None:
        self._fill(self.material_combo, self.database.materials, True)
        self._fill(self.lens_combo, self.database.lenses, True)
        self._fill(self.machine_combo, self.database.machines, False)
        self._refresh_table()

    def _refresh_table(self) -> None:
        selected = self.selected_entry()
        entries = db.matching_recipes(self.database, self.search_edit.text())
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            labels = (entry.recipe.name, *db.entry_labels(self.database, entry), str(len(entry.recipe.passes)))
            for column, text in enumerate(labels):
                item = QtWidgets.QTableWidgetItem('' if text is None else text)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, entry.id)
                self.table.setItem(row, column, item)
        self._select(None if selected is None else selected.id)

    def _select(self, entry_id: str | None) -> None:
        self.table.clearSelection()
        for row in range(self.table.rowCount()):
            if entry_id is not None and self.table.item(row, 0).data(QtCore.Qt.ItemDataRole.UserRole) == entry_id:
                self.table.selectRow(row)

    def selected_entry(self) -> db.RecipeEntry | None:
        """The entry of the selected table row, if any."""
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        entry_id = self.table.item(rows[0].row(), 0).data(QtCore.Qt.ItemDataRole.UserRole)
        return next((entry for entry in self.database.recipes if entry.id == entry_id), None)

    # Dialog hooks (replaced in tests) ----------------------------------------------------
    def _ask_catalog(self, title: str, number_label: str, current: tuple | None) -> tuple | None:
        dialog = CatalogDialog(title, number_label, current, self)
        return dialog.values() if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted else None

    def _confirm(self, text: str) -> bool:
        answer = QtWidgets.QMessageBox.question(self, _('Reçete veritabanı'), text)
        return answer == QtWidgets.QMessageBox.StandardButton.Yes

    # Catalog actions ----------------------------------------------------------------------
    def _edit_catalog(self, kind: str, existing: bool) -> None:
        table, model, field, put, _remove, title, number_label = CATALOGS[kind]
        combo = self.material_combo if kind == 'material' else self.lens_combo
        current = next((item for item in getattr(self.database, table) if item.id == combo.currentData()), None)
        if existing and current is None:
            self._status(_('Önce düzenlenecek {title} kaydını seçin.').format(title=_(title).lower()))
            return
        try:
            answer = self._ask_catalog(_(title), _(number_label), None if current is None or not existing else
                                       (current.name, getattr(current, field), current.notes))
            if answer is None:
                return
            value = model(current.id if existing else new_id(), *answer)
            database = put(self.database, value)
        except ValueError as error:
            self._error(error)
            return
        if self._commit(database, _('{title} kaydedildi: {name}').format(title=_(title), name=value.name)):
            self._fill(combo, getattr(self.database, table), True, value.id)

    def add_material(self) -> None:
        self._edit_catalog('material', False)

    def edit_material(self) -> None:
        self._edit_catalog('material', True)

    def add_lens(self) -> None:
        self._edit_catalog('lens', False)

    def edit_lens(self) -> None:
        self._edit_catalog('lens', True)

    def _delete(self, combo: QtWidgets.QComboBox, remove: Callable, title: str) -> None:
        key = combo.currentData()
        if key is None:
            self._status(_('Silinecek {title} kaydını seçin.').format(title=_(title).lower()))
            return
        if not self._confirm(_('{title} silinsin mi: {name}?').format(title=_(title), name=combo.currentText())):
            return
        try:
            database = remove(self.database, key)
        except ValueError as error:
            self._error(error)
            return
        self._commit(database, _('{title} silindi.').format(title=_(title)))

    def delete_material(self) -> None:
        self._delete(self.material_combo, db.remove_material, 'Malzeme')

    def delete_lens(self) -> None:
        self._delete(self.lens_combo, db.remove_lens, 'Lens')

    def delete_machine(self) -> None:
        self._delete(self.machine_combo, db.remove_machine, 'Makine')

    def save_machine(self) -> None:
        """Store the editor's device profile; replacing a named one revalidates its recipes."""
        try:
            profile = self.editor.device_editor.get_profile()
            if profile is None:
                raise ValueError(_('Eski reçetenin cihaz türü belirtilmemiş; önce lazer türünü seçin.'))
            existing = db.machine_named(self.database, profile.name)
            if existing is not None and existing.device == profile:
                self._status(_('Makine profili zaten aynı değerlerle kayıtlı.'))
                return
            if existing is not None and not self._confirm(_(
                    'Makine profili güncellensin mi? Bağlı reçeteler yeni profille yeniden doğrulanır.')):
                return
            machine = db.Machine(new_id() if existing is None else existing.id, profile,
                                 '' if existing is None else existing.notes)
            database = db.put_machine(self.database, machine)
        except ValueError as error:
            self._error(error)
            return
        if self._commit(database, _('Makine kaydedildi: {name}').format(name=profile.name)):
            self._fill(self.machine_combo, self.database.machines, False, machine.id)

    # Recipe actions -----------------------------------------------------------------------
    def save_current(self) -> None:
        """Save the editor recipe under the chosen material/lens and its device's machine."""
        material, lens = self.material_combo.currentData(), self.lens_combo.currentData()
        try:
            recipe = self.editor.get_recipe()
            try:
                database, entry, changed = db.store_recipe(self.database, recipe, material, lens, new_id)
            except db.RecipeExistsError:
                if not self._confirm(_('Aynı malzeme/makine/lens için “{name}” farklı değerlerle kayıtlı. '
                                       'Üzerine yazılsın mı?').format(name=recipe.name)):
                    return
                database, entry, changed = db.store_recipe(self.database, recipe, material, lens, new_id, replace=True)
        except ValueError as error:
            self._error(error)
            return
        if not changed:
            self._status(_('Reçete zaten aynı değerlerle kayıtlı.'))
        elif self._commit(database, _('Reçete veritabanına kaydedildi: {name}').format(name=recipe.name)):
            self._select(entry.id)

    def load_selected(self) -> None:
        """Copy the selected snapshot into the editor; later edits do not change the database."""
        entry = self.selected_entry()
        if entry is None:
            self._status(_('Tablodan bir reçete seçin.'))
            return
        self.editor.set_recipe(entry.recipe)
        self._fill(self.material_combo, self.database.materials, True, entry.material_id)
        self._fill(self.lens_combo, self.database.lenses, True, entry.lens_id)
        if entry.machine_id is not None:
            self._fill(self.machine_combo, self.database.machines, False, entry.machine_id)
        self._status(_('Reçete editöre yüklendi: {name}').format(name=entry.recipe.name))

    def delete_selected(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            self._status(_('Tablodan bir reçete seçin.'))
            return
        if self._confirm(_('Reçete silinsin mi: {name}?').format(name=entry.recipe.name)):
            self._commit(db.remove_recipe(self.database, entry.id), _('Reçete silindi.'))

    def import_files(self) -> None:
        """Import 0.2 recipe JSON files all-or-nothing under the chosen material and lens."""
        names, _filter = QtWidgets.QFileDialog.getOpenFileNames(
            self, _('Reçete JSON içe aktar'), '', _('JSON files (*.json)'))
        if not names:
            return
        database = self.database
        material, lens = self.material_combo.currentData(), self.lens_combo.currentData()
        for name in names:
            try:
                text = Path(name).read_text(encoding='utf-8')
                database = import_recipe_texts(database, (text,), material, lens, new_id)
            except (OSError, ValueError) as error:
                self._status(_('İçe aktarma iptal edildi, hiçbir dosya eklenmedi. {file}: {message}').format(
                    file=Path(name).name, message=error))
                return
        self._commit(database, _('{count} reçete dosyası içe aktarıldı.').format(count=len(names)))

    def export_selected(self) -> None:
        """Write the selected recipe as a standalone versioned recipe JSON file."""
        entry = self.selected_entry()
        if entry is None:
            self._status(_('Tablodan bir reçete seçin.'))
            return
        name, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, _('Reçete JSON dışa aktar'), f'{entry.recipe.name}.json', _('JSON files (*.json)'))
        if not name:
            return
        try:
            save_recipe_file(name, entry.recipe)
        except (OSError, ValueError) as error:
            self._error(error)
            return
        self._status(_('Reçete dışa aktarıldı: {file}').format(file=Path(name).name))
