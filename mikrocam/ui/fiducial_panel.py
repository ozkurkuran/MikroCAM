"""Thin fiducial alignment dock: collect pairs, call the core fit, hand over an accepted Placement."""
import builtins
from collections.abc import Callable
import gettext
from pathlib import Path

from PyQt6 import QtCore, QtWidgets

from mikrocam.core.fiducial import (METHODS, AlignmentFit, AlignmentPolicy, FiducialPair, default_method,
                                    fit_alignment)
from mikrocam.core.fiducial_codec import FiducialSet, dumps_fiducial_set, loads_fiducial_set
from mikrocam.core.placement import Placement, Point2D
from mikrocam.machine.fiducial_capture import capture_machine_xy


_ = getattr(builtins, '_', gettext.gettext)
COLUMNS = ('Name', 'Design X', 'Design Y', 'Machine X (MPos)', 'Machine Y (MPos)', 'Use')
METHOD_LABELS = {'rigid': 'Rigid: translation + rotation',
                 'similarity': 'Similarity: + uniform scale',
                 'affine': 'Affine: least squares (3+ points)'}
Candidates = tuple[tuple[str, Point2D], ...]


def _text(value: float) -> str:
    return format(value, '.10g')


class FiducialPanel(QtWidgets.QDockWidget):
    """No machine command is sent here; capture only reads the Machine panel snapshot."""

    def __init__(self, parent: QtWidgets.QWidget | None = None, *,
                 alignment_receiver: Callable[[Placement, str], None] | None = None,
                 design_points_provider: Callable[[], Candidates] | None = None,
                 snapshot_provider: Callable[[], object] | None = None) -> None:
        super().__init__(_('Fiducial alignment'), parent)
        self.setObjectName('MikroCAMFiducialPanel')
        self.alignment_receiver = alignment_receiver
        self.design_points_provider = design_points_provider
        self.snapshot_provider = snapshot_provider
        self.fit_result: AlignmentFit | None = None
        self._candidates: Candidates = ()
        self._updating = False
        content = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(content)
        caveat = QtWidgets.QLabel(_(
            'Design points are CAM/G-code mm. Measured points are machine coordinates (MPos mm) '
            'for this fixture and homing. Camera capture is not available yet. An accepted fit '
            'is checked only against the entered points; verify with a dry run.'))
        caveat.setWordWrap(True)
        layout.addWidget(caveat)
        self._build_table(layout)
        self._build_sources(layout)
        self._build_policy(layout)
        self._build_actions(layout)
        self.report_label = QtWidgets.QLabel(_('Enter at least two fiducials.'))
        self.report_label.setWordWrap(True)
        self.report_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.report_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.report_label)
        self.setWidget(content)
        self._sync()

    def _build_table(self, layout: QtWidgets.QVBoxLayout) -> None:
        self.table = QtWidgets.QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([_(name) for name in COLUMNS])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(self._edited)
        layout.addWidget(self.table, 1)
        rows = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton(_('Add fiducial'))
        self.remove_button = QtWidgets.QPushButton(_('Remove selected'))
        self.add_button.clicked.connect(lambda: self.add_row())
        self.remove_button.clicked.connect(self.remove_row)
        rows.addWidget(self.add_button)
        rows.addWidget(self.remove_button)
        layout.addLayout(rows)

    def _build_sources(self, layout: QtWidgets.QVBoxLayout) -> None:
        sources = QtWidgets.QHBoxLayout()
        self.load_candidates_button = QtWidgets.QPushButton(_('Points from selected object'))
        self.candidate_combo = QtWidgets.QComboBox()
        self.use_candidate_button = QtWidgets.QPushButton(_('Use as design point'))
        self.capture_button = QtWidgets.QPushButton(_('Capture machine XY'))
        self.load_candidates_button.clicked.connect(self.load_candidates)
        self.use_candidate_button.clicked.connect(self.use_candidate)
        self.capture_button.clicked.connect(self.capture_machine)
        for widget in (self.load_candidates_button, self.candidate_combo, self.use_candidate_button,
                       self.capture_button):
            sources.addWidget(widget)
        layout.addLayout(sources)

    def _build_policy(self, layout: QtWidgets.QVBoxLayout) -> None:
        form = QtWidgets.QFormLayout()
        self.method_combo = QtWidgets.QComboBox()
        for method in METHODS:
            self.method_combo.addItem(_(METHOD_LABELS[method]), method)
        self.method_combo.setCurrentIndex(self.method_combo.findData('rigid'))
        self.method_combo.currentIndexChanged.connect(lambda index: self._invalidate())
        defaults = AlignmentPolicy('rigid')
        self.residual_edit = QtWidgets.QLineEdit(_text(defaults.max_residual_mm))
        self.scale_edit = QtWidgets.QLineEdit(_text(defaults.max_scale_deviation * 100))
        self.separation_edit = QtWidgets.QLineEdit(_text(defaults.min_separation_mm))
        for edit in (self.residual_edit, self.scale_edit, self.separation_edit):
            edit.textChanged.connect(lambda text: self._invalidate())
        form.addRow(_('Method'), self.method_combo)
        form.addRow(_('Maximum residual (mm)'), self.residual_edit)
        form.addRow(_('Maximum scale deviation (%)'), self.scale_edit)
        form.addRow(_('Minimum fiducial separation (mm)'), self.separation_edit)
        layout.addLayout(form)

    def _build_actions(self, layout: QtWidgets.QVBoxLayout) -> None:
        actions = QtWidgets.QHBoxLayout()
        self.fit_button = QtWidgets.QPushButton(_('Calculate alignment'))
        self.accept_button = QtWidgets.QPushButton(_('Use in preflight setup'))
        self.save_button = QtWidgets.QPushButton(_('Save set…'))
        self.load_button = QtWidgets.QPushButton(_('Open set…'))
        self.fit_button.clicked.connect(self.fit)
        self.accept_button.clicked.connect(self.accept)
        self.save_button.clicked.connect(lambda: self.save_to())
        self.load_button.clicked.connect(lambda: self.load_from())
        for button in (self.fit_button, self.accept_button, self.save_button, self.load_button):
            actions.addWidget(button)
        layout.addLayout(actions)

    def _sync(self) -> None:
        accepted = self.fit_result is not None and self.fit_result.accepted
        self.accept_button.setEnabled(accepted and self.alignment_receiver is not None)
        self.load_candidates_button.setEnabled(self.design_points_provider is not None)
        self.use_candidate_button.setEnabled(bool(self._candidates))
        self.capture_button.setEnabled(self.snapshot_provider is not None)

    def _invalidate(self, message: str | None = None) -> None:
        self.fit_result = None
        if message is not None:
            self.report_label.setText(message)
        self._sync()

    def _edited(self, item: QtWidgets.QTableWidgetItem) -> None:
        if not self._updating:
            self._invalidate(_('Fiducials changed. Calculate again.'))

    def add_row(self, pair: FiducialPair | None = None) -> int:
        row = self.table.rowCount()
        self._updating = True
        try:
            self.table.insertRow(row)
            name = pair.name if pair else f'F{row + 1}'
            design = pair.design_mm if pair else None
            machine = pair.machine_mm if pair else None
            values = (name, *(('', '') if design is None else map(_text, design)),
                      *(('', '') if machine is None else map(_text, machine)))
            for column, text in enumerate(values):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem(text))
            use = QtWidgets.QTableWidgetItem()
            use.setFlags(QtCore.Qt.ItemFlag.ItemIsUserCheckable | QtCore.Qt.ItemFlag.ItemIsEnabled
                         | QtCore.Qt.ItemFlag.ItemIsSelectable)
            use.setCheckState(QtCore.Qt.CheckState.Checked if pair is None or pair.enabled
                              else QtCore.Qt.CheckState.Unchecked)
            self.table.setItem(row, 5, use)
        finally:
            self._updating = False
        self._invalidate(_('Fiducials changed. Calculate again.'))
        return row

    def remove_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._invalidate(_('Fiducials changed. Calculate again.'))

    def set_pairs(self, pairs: tuple[FiducialPair, ...]) -> None:
        self.table.setRowCount(0)
        for pair in pairs:
            self.add_row(pair)
        method = default_method(sum(pair.enabled for pair in pairs))
        self.method_combo.setCurrentIndex(self.method_combo.findData(method))

    def _cell(self, row: int, column: int) -> str:
        item = self.table.item(row, column)
        return '' if item is None else item.text().strip()

    def _number(self, row: int, column: int) -> float:
        try:
            return float(self._cell(row, column))
        except ValueError as error:
            raise ValueError(_('Row {row}: {column} must be a number').format(
                row=row + 1, column=_(COLUMNS[column]))) from error

    def pairs(self) -> tuple[FiducialPair, ...]:
        result = []
        for row in range(self.table.rowCount()):
            design = (self._number(row, 1), self._number(row, 2))
            measured = None
            if self._cell(row, 3) or self._cell(row, 4):
                measured = (self._number(row, 3), self._number(row, 4))
            use = self.table.item(row, 5)
            enabled = use is not None and use.checkState() == QtCore.Qt.CheckState.Checked
            result.append(FiducialPair(self._cell(row, 0), design, measured, enabled))
        return tuple(result)

    def policy(self) -> AlignmentPolicy:
        try:
            values = (float(self.residual_edit.text()), round(float(self.scale_edit.text()) / 100, 12),
                      float(self.separation_edit.text()))
        except ValueError as error:
            raise ValueError(_('Thresholds must be numbers')) from error
        return AlignmentPolicy(self.method_combo.currentData(), *values)

    def fit(self) -> AlignmentFit | None:
        self._invalidate()
        try:
            result = fit_alignment(self.pairs(), self.policy())
        except ValueError as error:
            self.report_label.setText(_('Cannot calculate alignment: ') + str(error))
            return None
        self.fit_result = result
        self.report_label.setText(self._report(result))
        self._sync()
        return result

    def _report(self, fit: AlignmentFit) -> str:
        status = _('ACCEPTED') if fit.accepted else _('REJECTED')
        lines = [_('{status}: {method}; rotation {rotation:.5f} deg; observed scale {scale:.6f}; '
                   'axis scales {sx:.6f}/{sy:.6f}; redundancy {redundancy}').format(
                     status=status, method=fit.method, rotation=fit.rotation_deg, scale=fit.observed_scale,
                     sx=fit.axis_scales[0], sy=fit.axis_scales[1], redundancy=fit.redundancy),
                 _('Residual RMS {rms:.4f} mm; max {max:.4f} mm').format(rms=fit.rms_mm, max=fit.max_mm)]
        for item in fit.residuals:
            lines.append(_('{name}: design {design} -> fitted {fitted}; error ({dx:+.4f}, {dy:+.4f}) = '
                           '{mag:.4f} mm').format(
                name=item.name, design=tuple(round(v, 4) for v in item.design_mm),
                fitted=tuple(round(v, 4) for v in item.fitted_mm), dx=item.error_mm[0],
                dy=item.error_mm[1], mag=item.magnitude_mm))
        lines += [_('Reason: ') + reason for reason in fit.reasons]
        lines += [_('Warning: ') + warning for warning in fit.warnings]
        return '\n'.join(lines)

    def accept(self) -> None:
        if self.fit_result is None or not self.fit_result.accepted or self.alignment_receiver is None:
            return
        fit = self.fit_result
        summary = _('{method}, {count} points, max residual {max:.4f} mm').format(
            method=fit.method, count=len(fit.residuals), max=fit.max_mm)
        self.alignment_receiver(fit.require_placement(), summary)
        self.report_label.setText(self.report_label.text() + '\n' + _('Sent to preflight setup. Analyze again.'))

    def load_candidates(self) -> None:
        self._candidates = ()
        self.candidate_combo.clear()
        try:
            if self.design_points_provider is None:
                raise ValueError(_('No object provider is available'))
            self._candidates = tuple(self.design_points_provider())
        except Exception as error:
            self.report_label.setText(_('Design points unavailable: ') + str(error)[:256])
        for label, _point in self._candidates:
            self.candidate_combo.addItem(label)
        self._sync()

    def _target_row(self) -> int:
        row = self.table.currentRow()
        if row < 0:
            row = self.add_row()
            self.table.setCurrentCell(row, 0)
        return row

    def _set_cells(self, row: int, first: int, point: Point2D) -> None:
        for offset, value in enumerate(point):
            self.table.setItem(row, first + offset, QtWidgets.QTableWidgetItem(_text(value)))

    def use_candidate(self) -> None:
        index = self.candidate_combo.currentIndex()
        if 0 <= index < len(self._candidates):
            self._set_cells(self._target_row(), 1, self._candidates[index][1])

    def capture_machine(self) -> None:
        try:
            if self.snapshot_provider is None:
                raise ValueError(_('Open and connect the Machine panel first'))
            point = capture_machine_xy(self.snapshot_provider())
        except ValueError as error:
            self.report_label.setText(_('Capture refused: ') + str(error))
            return
        self._set_cells(self._target_row(), 3, point)

    def save_to(self, path: str | Path | None = None) -> None:
        if path is None:
            path, _filter = QtWidgets.QFileDialog.getSaveFileName(
                self, _('Save fiducial set'), '', _('Fiducial set (*.json)'))
            if not path:
                return
        try:
            text = dumps_fiducial_set(FiducialSet(Path(path).stem or 'fiducials', self.policy(), self.pairs()))
            Path(path).write_text(text, encoding='utf-8')
        except (OSError, ValueError) as error:
            self.report_label.setText(_('Save failed: ') + str(error)[:256])

    def load_from(self, path: str | Path | None = None) -> None:
        if path is None:
            path, _filter = QtWidgets.QFileDialog.getOpenFileName(
                self, _('Open fiducial set'), '', _('Fiducial set (*.json)'))
            if not path:
                return
        try:
            value = loads_fiducial_set(Path(path).read_text(encoding='utf-8'))
        except (OSError, ValueError, UnicodeError) as error:
            self.report_label.setText(_('Open failed: ') + str(error)[:256])
            return
        self.set_pairs(value.pairs)
        policy = value.policy
        self.method_combo.setCurrentIndex(self.method_combo.findData(policy.method))
        self.residual_edit.setText(_text(policy.max_residual_mm))
        self.scale_edit.setText(_text(policy.max_scale_deviation * 100))
        self.separation_edit.setText(_text(policy.min_separation_mm))
        self._invalidate(_('Fiducial set opened. Measured values are valid only for the same fixture '
                           'and homing; re-measure if anything moved.'))
