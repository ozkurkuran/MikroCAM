"""Device-aware recipe drafts and atomic versioned recipe file replacement."""
import builtins
import gettext
import os
from pathlib import Path
import tempfile

from PyQt6 import QtCore, QtWidgets

from mikrocam.core.laser_job import LaserPass, LaserRecipe
from mikrocam.core.laser_json import recipe_to_json
from .laser_device import LaserDeviceEditor


_ = getattr(builtins, '_', gettext.gettext)
FIELDS = ('name', 'power_percent', 'speed_mm_s', 'frequency_khz', 'pulse_width_ns', 'min_power_percent', 'pwm_frequency_khz')
HEADERS = ('Geçiş adı', 'Güç (%)', 'Hız (mm/s)', 'Frekans (kHz)', 'Atım süresi (ns)', 'Min. güç (%) — isteğe bağlı', 'PWM (kHz) — isteğe bağlı')


class LaserRecipeEditor(QtWidgets.QWidget):
    """Keep incomplete drafts as text; validate only through the existing core values."""
    changed = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        name_form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit()
        name_form.addRow(_('Recipe name'), self.name_edit)
        layout.addLayout(name_form)
        self.device_editor = LaserDeviceEditor()
        layout.addWidget(self.device_editor)
        self.table = QtWidgets.QTableWidget(0, len(FIELDS))
        self.table.setHorizontalHeaderLabels([_(text) for text in HEADERS])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.table.setMinimumHeight(150)
        self.table.setMaximumHeight(260)
        layout.addWidget(self.table)
        buttons = QtWidgets.QHBoxLayout()
        for label, callback in (('Add pass', self.add_pass), ('Remove pass', self.remove_pass),
                                ('Move up', lambda: self.move_pass(-1)),
                                ('Move down', lambda: self.move_pass(1))):
            button = QtWidgets.QPushButton(_(label))
            button.clicked.connect(callback)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.name_edit.textChanged.connect(self.changed)
        self.table.cellChanged.connect(self.changed)
        self.device_editor.changed.connect(self._device_changed)
        self._sync_columns()

    def _device_changed(self) -> None:
        self._sync_columns(); self.changed.emit()

    def _sync_columns(self) -> None:
        fields = self.device_editor.active_fields
        for column, field in enumerate(FIELDS):
            self.table.setColumnHidden(column, field != 'name' and field not in fields)

    def set_recipe(self, recipe: LaserRecipe) -> None:
        """Show round-trip-safe float representations without rounding loaded settings."""
        if not isinstance(recipe, LaserRecipe):
            raise ValueError(_('A valid laser recipe is required.'))
        with QtCore.QSignalBlocker(self.name_edit), QtCore.QSignalBlocker(self.table), QtCore.QSignalBlocker(self.device_editor):
            self.device_editor.set_profile(recipe.device)
            self.name_edit.setText(recipe.name)
            self.table.setRowCount(len(recipe.passes))
            for row, settings in enumerate(recipe.passes):
                for column, field in enumerate(FIELDS):
                    value = getattr(settings, field)
                    text = value if column == 0 else ('' if value is None else repr(value))
                    self.table.setItem(row, column, QtWidgets.QTableWidgetItem(text))
            self.table.setCurrentCell(0, 0)
        self._sync_columns(); self.changed.emit()

    def get_recipe(self) -> LaserRecipe:
        """Return a validated immutable snapshot or an actionable field/row error."""
        device = self.device_editor.get_profile()
        passes = []
        for row in range(self.table.rowCount()):
            values = {}
            for column, field in enumerate(FIELDS):
                item = self.table.item(row, column)
                text = item.text() if item is not None else ''
                if column == 0:
                    values[field] = text
                elif field not in self.device_editor.active_fields or (
                    field in ('min_power_percent', 'pwm_frequency_khz') and not text.strip()
                ): values[field] = None
                else:
                    try:
                        values[field] = float(text)
                    except ValueError as error:
                        raise ValueError(_('Pass {row}: {field} requires an explicit number.').format(
                            row=row + 1, field=_(HEADERS[column]))) from error
            try:
                passes.append(LaserPass(**values))
            except ValueError as error:
                raise ValueError(_('Pass {row}: {message}').format(row=row + 1, message=_(str(error)))) from error
        return LaserRecipe(self.name_edit.text(), tuple(passes), device)

    def add_pass(self) -> None:
        """Insert an entirely blank pass; numeric parameters are never invented."""
        row = self.table.rowCount()
        with QtCore.QSignalBlocker(self.table):
            self.table.insertRow(row)
            for column in range(len(FIELDS)):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem(''))
            self.table.setCurrentCell(row, 0)
        self.changed.emit()

    def remove_pass(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        with QtCore.QSignalBlocker(self.table):
            self.table.removeRow(row)
            if self.table.rowCount():
                self.table.setCurrentCell(min(row, self.table.rowCount() - 1), 0)
        self.changed.emit()

    def move_pass(self, offset: int) -> None:
        """Move the selected complete row without changing its draft text."""
        row = self.table.currentRow()
        target = row + offset
        if row < 0 or not 0 <= target < self.table.rowCount() or target == row:
            return
        with QtCore.QSignalBlocker(self.table):
            source_items = [self.table.takeItem(row, column) for column in range(len(FIELDS))]
            self.table.removeRow(row)
            self.table.insertRow(target)
            for column, source in enumerate(source_items):
                self.table.setItem(target, column, source)
            self.table.setCurrentCell(target, 0)
        self.changed.emit()


def save_recipe_file(path: str | Path, recipe: LaserRecipe) -> None:
    """Atomically replace a recipe using a flushed same-directory temporary file."""
    target = Path(path)
    text = recipe_to_json(recipe)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', delete=False,
                                         dir=target.parent, prefix=f'.{target.name}.', suffix='.tmp') as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
