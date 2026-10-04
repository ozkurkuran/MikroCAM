"""Explicit declared preflight setup inputs; no inferred or authorizing defaults."""
import builtins
import gettext

from PyQt6 import QtCore, QtWidgets

from mikrocam.core.gcode_models import PreflightSetup
from mikrocam.core.placement import Placement


_ = getattr(builtins, '_', gettext.gettext)


class PreflightSetupWidget(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.fields: dict[str, QtWidgets.QLineEdit] = {}
        self._labels: dict[str, str] = {}
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        initial = self._group(_('Initial program position (mm)'), layout)
        self._axis_row(initial, 0, 'initial', _('Initial'), 'XYZ')
        envelope = self._group(_('Machine travel envelope (mm)'), layout)
        self._axis_row(envelope, 0, 'min', _('Minimum'), 'XYZ')
        self._axis_row(envelope, 1, 'max', _('Maximum'), 'XYZ')
        vertical = self._group(_('Z setup (mm)'), layout)
        self._field(vertical, 0, 0, 'safe_z', _('Safe rapid Z'))
        self._field(vertical, 0, 1, 'z_offset', _('Z translation'))
        placement = self._group(_('XY placement (mm); rotation (degrees)'), layout)
        self._axis_row(placement, 0, 'origin', _('Origin'), 'XY')
        self._axis_row(placement, 1, 'translation', _('Translation'), 'XY')
        self._field(placement, 2, 0, 'rotation', _('Rotation'))
        self.mirror_checkbox = QtWidgets.QCheckBox(_('Mirror local X'), self)
        self.mirror_checkbox.toggled.connect(lambda checked: self.changed.emit())
        placement.addWidget(self.mirror_checkbox, 5, 1)
        self._alignment: Placement | None = None
        self.alignment_label = QtWidgets.QLabel(_('Fiducial alignment: not used'), self)
        self.alignment_label.setWordWrap(True)
        self.clear_alignment_button = QtWidgets.QPushButton(_('Clear fiducial alignment'), self)
        self.clear_alignment_button.clicked.connect(self.clear_alignment)
        self.clear_alignment_button.setEnabled(False)
        placement.addWidget(self.alignment_label, 6, 0, 1, 2)
        placement.addWidget(self.clear_alignment_button, 7, 0, 1, 2)
        rapid = self._group(_('Optional rapid rates (mm/min): all axes or none'), layout)
        self._axis_row(rapid, 0, 'rapid', _('Rapid'), 'XYZ', optional=True)
        layout.addStretch(1)

    def _group(self, title: str, layout: QtWidgets.QVBoxLayout) -> QtWidgets.QGridLayout:
        box = QtWidgets.QGroupBox(title, self)
        grid = QtWidgets.QGridLayout(box)
        layout.addWidget(box)
        return grid

    def _field(self, grid: QtWidgets.QGridLayout, row: int, column: int, key: str,
               label: str, optional: bool = False) -> None:
        edit = QtWidgets.QLineEdit(self)
        edit.setPlaceholderText(_('Optional') if optional else _('Required'))
        edit.textChanged.connect(lambda text: self.changed.emit())
        self.fields[key], self._labels[key] = edit, label
        grid.addWidget(QtWidgets.QLabel(label), row * 2, column)
        grid.addWidget(edit, row * 2 + 1, column)
        grid.setColumnStretch(column, 1)

    def _axis_row(self, grid: QtWidgets.QGridLayout, row: int, prefix: str,
                  label: str, axes: str, optional: bool = False) -> None:
        for column, axis in enumerate(axes):
            self._field(grid, row, column, f'{prefix}_{axis.lower()}',
                        f'{label} {axis}', optional)

    def set_alignment(self, placement: Placement, summary: str) -> None:
        """Use an accepted fiducial Placement instead of the rigid placement fields."""
        if not isinstance(placement, Placement):
            raise ValueError(_('An accepted fiducial Placement is required'))
        self._alignment = placement
        self.alignment_label.setText(_('Fiducial alignment active (machine MPos frame): ') + summary)
        self._sync_alignment()

    def clear_alignment(self) -> None:
        self._alignment = None
        self.alignment_label.setText(_('Fiducial alignment: not used'))
        self._sync_alignment()

    def _sync_alignment(self) -> None:
        rigid = self._alignment is None
        for key in ('origin_x', 'origin_y', 'translation_x', 'translation_y', 'rotation'):
            self.fields[key].setEnabled(rigid)
        self.mirror_checkbox.setEnabled(rigid)
        self.clear_alignment_button.setEnabled(not rigid)
        self.changed.emit()

    def _number(self, key: str) -> float:
        text = self.fields[key].text().strip()
        if not text:
            raise ValueError(_('Enter ') + self._labels[key])
        try:
            return float(text)
        except ValueError as error:
            raise ValueError(self._labels[key] + _(' must be a number')) from error

    def _human_error(self, error: ValueError) -> str:
        message = str(error)
        for name, prefix in (('initial_position_mm', 'initial'), ('machine_min_mm', 'min'),
                             ('machine_max_mm', 'max'), ('rapid_rates_mm_min', 'rapid')):
            for index, axis in enumerate('xyz'):
                message = message.replace(f'{name}[{index}]', self._labels[f'{prefix}_{axis}'])
        for prefix in ('origin', 'translation'):
            for axis in 'xy':
                message = message.replace(f'{prefix}.{axis}', self._labels[f'{prefix}_{axis}'])
        for name, label in (('rotation_deg', _('Rotation')), ('placement.origin', _('Placement origin')),
                            ('placement.translation', _('Placement translation')),
                            ('safe_z_mm', _('Safe rapid Z')), ('z_offset_mm', _('Z translation'))):
            message = message.replace(name, label)
        return message

    def value(self) -> PreflightSetup:
        """Gather explicit inputs and let the existing core authorities validate them."""
        rigid_keys = ('origin_x', 'origin_y', 'translation_x', 'translation_y', 'rotation')
        numbers = {key: self._number(key) for key in self.fields if not key.startswith('rapid_')
                   and (self._alignment is None or key not in rigid_keys)}
        rapid_keys = ('rapid_x', 'rapid_y', 'rapid_z')
        present = tuple(bool(self.fields[key].text().strip()) for key in rapid_keys)
        if any(present) and not all(present):
            raise ValueError(_('Enter all three rapid rates or leave all three empty'))
        rapid = tuple(self._number(key) for key in rapid_keys) if all(present) else None
        try:
            placement = self._alignment or Placement(
                origin=(numbers['origin_x'], numbers['origin_y']),
                translation=(numbers['translation_x'], numbers['translation_y']),
                rotation_deg=numbers['rotation'], mirror_x=self.mirror_checkbox.isChecked())
            return PreflightSetup(
                initial_position_mm=tuple(numbers[f'initial_{axis}'] for axis in 'xyz'),
                placement=placement, z_offset_mm=numbers['z_offset'],
                machine_min_mm=tuple(numbers[f'min_{axis}'] for axis in 'xyz'),
                machine_max_mm=tuple(numbers[f'max_{axis}'] for axis in 'xyz'),
                safe_z_mm=numbers['safe_z'], rapid_rates_mm_min=rapid)
        except ValueError as error:
            raise ValueError(self._human_error(error)) from error
