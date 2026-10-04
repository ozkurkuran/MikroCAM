"""Thin translated Laser CAM dock; planning and host geometry live below the UI."""
import builtins
import gettext
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

from mikrocam.bridge.laser_cam import LaserCamHost
from mikrocam.core.laser_job import LaserJob, LaserRecipe
from mikrocam.core.laser_json import recipe_from_json
from mikrocam.core.laser_paths import CopperFeatures, LaserPlan, PlanOptions
from mikrocam.core.placement import Placement
from .laser_recipe import LaserRecipeEditor, save_recipe_file
from .laser_recipe_db import LaserRecipeLibrary
from .laser_export import LaserExportControls
from .laser_worker import LaserWorker


_ = getattr(builtins, '_', gettext.gettext)


class LaserCamPanel(QtWidgets.QDockWidget):
    def __init__(self, host: LaserCamHost) -> None:
        super().__init__(_('Laser CAM'), host.parent_widget())
        self.setObjectName('mikrocam_laser_cam')
        self.host = host
        self.last_plan: LaserPlan | None = None
        self._worker: LaserWorker | None = None
        self._inputs: list[QtWidgets.QWidget] = []
        content = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(content)
        self.input_controls = QtWidgets.QWidget(content)
        inputs = QtWidgets.QVBoxLayout(self.input_controls)
        self._build_source(inputs)
        self._build_placement(inputs)
        self._build_paths(inputs)
        self.input_scroll = QtWidgets.QScrollArea(content)
        self.input_scroll.setWidgetResizable(True)
        self.input_scroll.setWidget(self.input_controls)
        layout.addWidget(self.input_scroll)
        self._build_actions(layout)
        layout.addStretch()
        self.setWidget(content)
        self.refresh_sources()
        self._connect_inputs()
        QtWidgets.QApplication.instance().aboutToQuit.connect(self.shutdown)

    @property
    def busy(self) -> bool:
        return self._worker is not None or self.export_controls.busy

    @property
    def recipe(self) -> LaserRecipe | None:
        """Expose the current valid draft, never a previously loaded recipe fallback."""
        try:
            return self.recipe_editor.get_recipe()
        except ValueError:
            return None

    def _combo(self, form: QtWidgets.QFormLayout, label: str,
               choices: tuple[tuple[str, str], ...]) -> QtWidgets.QComboBox:
        control = QtWidgets.QComboBox()
        for text, value in choices:
            control.addItem(_(text), value)
        form.addRow(_(label), control)
        self._inputs.append(control)
        return control

    def _number(self, form: QtWidgets.QFormLayout, label: str, value: float = 0,
                minimum: float = -1e9, maximum: float = 1e9) -> QtWidgets.QDoubleSpinBox:
        control = QtWidgets.QDoubleSpinBox()
        control.setDecimals(6)
        control.setRange(minimum, maximum)
        control.setValue(value)
        form.addRow(_(label), control)
        self._inputs.append(control)
        return control

    def _check(self, form: QtWidgets.QFormLayout, label: str) -> QtWidgets.QCheckBox:
        control = QtWidgets.QCheckBox(_(label))
        form.addRow(control)
        self._inputs.append(control)
        return control

    def _build_source(self, layout: QtWidgets.QVBoxLayout) -> None:
        group = QtWidgets.QGroupBox(_('Source and recipe'))
        form = QtWidgets.QFormLayout(group)
        self.source_combo = self._combo(form, 'Gerber copper', ())
        self.outline_combo = self._combo(form, 'Board outline', ())
        self.refresh_button = QtWidgets.QPushButton(_('Refresh sources'))
        self.refresh_button.clicked.connect(self.refresh_sources)
        form.addRow(self.refresh_button)
        self.recipe_button = QtWidgets.QPushButton(_('Load recipe JSON'))
        self.recipe_button.clicked.connect(self._load_recipe)
        self.recipe_label = QtWidgets.QLabel(_('No recipe loaded'))
        self.recipe_label.setWordWrap(True)
        form.addRow(self.recipe_button)
        self.save_recipe_button = QtWidgets.QPushButton(_('Save recipe JSON'))
        self.save_recipe_button.clicked.connect(self._save_recipe)
        form.addRow(self.save_recipe_button)
        form.addRow(self.recipe_label)
        layout.addWidget(group)
        self.recipe_editor = LaserRecipeEditor()
        self.recipe_editor.changed.connect(self._recipe_changed)
        layout.addWidget(self.recipe_editor)
        self.recipe_library = LaserRecipeLibrary(self.recipe_editor, self.host.recipe_database_path())
        layout.addWidget(self.recipe_library)

    def _build_placement(self, layout: QtWidgets.QVBoxLayout) -> None:
        group = QtWidgets.QGroupBox(_('Placement (mm)'))
        form = QtWidgets.QFormLayout(group)
        self.origin_x = self._number(form, 'Origin X')
        self.origin_y = self._number(form, 'Origin Y')
        self.translation_x = self._number(form, 'Translation X')
        self.translation_y = self._number(form, 'Translation Y')
        self.rotation = self._number(form, 'Rotation (degrees)', maximum=360000, minimum=-360000)
        self.mirror_x = self._check(form, 'Mirror local X')
        layout.addWidget(group)

    def _build_paths(self, layout: QtWidgets.QVBoxLayout) -> None:
        group = QtWidgets.QGroupBox(_('Paths'))
        form = QtWidgets.QFormLayout(group)
        self.contour_combo = self._combo(form, 'Contour', (
            ('Outer copper', 'outer'), ('Inner copper holes', 'inner'), ('Trace', 'trace'),
            ('Pad', 'pad'), ('Board edge', 'board'), ('None', 'none')))
        self.region_combo = self._combo(form, 'Fill area', (
            ('Copper', 'copper'), ('Board minus copper', 'clearance')))
        self.hatch_enabled = self._check(form, 'Hatch')
        self.hatch_spacing = self._number(form, 'Hatch spacing (mm)', 0.1, 0.000001, 1e6)
        self.hatch_angle = self._number(form, 'Hatch angle (degrees)', maximum=360000, minimum=-360000)
        self.cross_hatch = self._check(form, 'Cross hatch')
        self.interlace_n = QtWidgets.QSpinBox()
        self.interlace_n.setRange(1, 1_000_000)
        self.interlace_n.setValue(1)
        form.addRow(_('Interlace N'), self.interlace_n)
        self._inputs.append(self.interlace_n)
        layout.addWidget(group)

    def _build_actions(self, layout: QtWidgets.QVBoxLayout) -> None:
        buttons = QtWidgets.QHBoxLayout()
        self.generate_button = QtWidgets.QPushButton(_('Generate preview'))
        self.generate_button.clicked.connect(self.generate)
        self.cancel_button = QtWidgets.QPushButton(_('Cancel'))
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        buttons.addWidget(self.generate_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)
        self.status_label = QtWidgets.QLabel(_('Load an explicit recipe to generate paths.'))
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.export_controls = LaserExportControls()
        self.export_controls.status_changed.connect(self.status_label.setText)
        self.export_controls.busy_changed.connect(self._sync_busy_controls)
        layout.addWidget(self.export_controls)

    def _sync_busy_controls(self) -> None:
        self.input_controls.setEnabled(not self.busy)
        self.generate_button.setEnabled(not self.busy)
        self.cancel_button.setEnabled(self.busy)
        self.export_controls.setEnabled(self._worker is None)

    def _connect_inputs(self) -> None:
        for control in self._inputs:
            if isinstance(control, QtWidgets.QComboBox):
                control.currentIndexChanged.connect(self._input_changed)
            elif isinstance(control, QtWidgets.QCheckBox):
                control.toggled.connect(self._input_changed)
            else:
                control.valueChanged.connect(self._input_changed)

    def _input_changed(self) -> None:
        self.last_plan = None
        self.export_controls.set_plan(None)
        if self.busy:
            self.cancel()
        else:
            self.status_label.setText(_('Inputs changed; generate a new preview.'))

    def _recipe_changed(self) -> None:
        self.recipe_label.setText(self.recipe_editor.name_edit.text() or _('No recipe loaded'))
        self._input_changed()

    def refresh_sources(self) -> None:
        """Read current GUI-host names, preserving explicit selections where possible."""
        self._input_changed()
        source = self.source_combo.currentData() or self.host.active_name()
        outline = self.outline_combo.currentData()
        names = self.host.source_names()
        for combo, selection in ((self.source_combo, source), (self.outline_combo, outline)):
            combo.blockSignals(True)
            combo.clear()
            if combo is self.outline_combo:
                combo.addItem(_('No outline selected'), None)
            for name in names:
                combo.addItem(name, name)
            index = combo.findData(selection)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

    def set_recipe(self, recipe: LaserRecipe) -> None:
        """Use only an explicit validated recipe; never substitute host defaults."""
        if not isinstance(recipe, LaserRecipe):
            raise ValueError(_('A valid laser recipe is required.'))
        self.recipe_editor.set_recipe(recipe)

    def _load_recipe(self) -> None:
        filename, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, _('Load laser recipe'), '', _('JSON files (*.json)'))
        if not filename:
            return
        self._input_changed()
        try:
            self.set_recipe(recipe_from_json(Path(filename).read_text(encoding='utf-8')))
        except (OSError, ValueError) as error:
            self.recipe_editor.name_edit.clear()
            self.recipe_editor.table.setRowCount(0)
            self.recipe_label.setText(_('No recipe loaded'))
            self._error(str(error))

    def _save_recipe(self) -> None:
        filename, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, _('Save laser recipe'), '', _('JSON files (*.json)'))
        if not filename:
            return
        try:
            save_recipe_file(filename, self.recipe_editor.get_recipe())
        except (OSError, ValueError) as error:
            self._error(str(error))
            return
        self.status_label.setText(_('Recipe saved: {name}').format(name=Path(filename).name))

    def _request(self) -> tuple[LaserJob, PlanOptions, CopperFeatures]:
        recipe = self.recipe_editor.get_recipe()
        source = self.source_combo.currentData()
        if not source:
            raise ValueError(_('Select a Gerber copper source.'))
        placement = Placement(origin=(self.origin_x.value(), self.origin_y.value()),
                              translation=(self.translation_x.value(), self.translation_y.value()),
                              rotation_deg=self.rotation.value(), mirror_x=self.mirror_x.isChecked())
        options = PlanOptions(contour_mode=self.contour_combo.currentData(),
                              region_mode=self.region_combo.currentData(), hatch=self.hatch_enabled.isChecked(),
                              spacing_mm=self.hatch_spacing.value(), angle_deg=self.hatch_angle.value(),
                              cross_hatch=self.cross_hatch.isChecked(), interlace_n=self.interlace_n.value())
        features = self.host.snapshot(source, self.outline_combo.currentData())
        return LaserJob(source, features.copper, recipe, placement), options, features

    def generate(self) -> None:
        """Snapshot on the GUI thread and admit at most one detached planning request."""
        if self.busy:
            return
        self.last_plan = None
        self.export_controls.set_plan(None)
        try:
            job, options, features = self._request()
        except (TypeError, ValueError) as error:
            self._error(str(error))
            return
        worker = LaserWorker(job, options, features, self)
        self._worker = worker
        worker.completed.connect(self._completed, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.failed.connect(self._worker_error, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.cancelled.connect(self._cancelled, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(self._finished, QtCore.Qt.ConnectionType.QueuedConnection)
        self._sync_busy_controls()
        self.status_label.setText(_('Generating preview…'))
        worker.start()

    def cancel(self) -> None:
        """Keep the worker alive until finished while invalidating every pending result."""
        self.export_controls.cancel()
        if self._worker is not None:
            self._worker.cancel()
            self.last_plan = None
            self.status_label.setText(_('Cancelling…'))

    def _completed(self, plan: LaserPlan) -> None:
        if self.sender() is not self._worker or self._worker is None or self._worker.is_cancelled():
            return
        try:
            name = self.host.publish_preview(plan)
        except Exception as error:
            self._error(str(error))
            return
        self.last_plan = plan
        self.export_controls.set_plan(plan)
        self.status_label.setText(_('Preview ready: {name} ({count} passes)').format(
            name=name, count=len(plan.pass_plans)))

    def _error(self, message: str) -> None:
        self.status_label.setText(_('Error: {message}').format(message=_(message)))

    def _worker_error(self, message: str) -> None:
        if self._worker is not None and self.sender() is self._worker and not self._worker.is_cancelled():
            self._error(message)

    def _cancelled(self) -> None:
        if self._worker is not None and self.sender() is self._worker:
            self.status_label.setText(_('Cancelled.'))

    def _finished(self) -> None:
        self._release_worker(self.sender())

    def _release_worker(self, expected: QtCore.QObject) -> None:
        if expected is not self._worker:
            return
        worker, self._worker = self._worker, None
        if worker is not None:
            if worker.is_cancelled():
                self.status_label.setText(_('Cancelled.'))
            worker.deleteLater()
        self._sync_busy_controls()

    def shutdown(self) -> None:
        """Cancel and join the bounded worker before Qt destroys its parent widgets."""
        self.export_controls.shutdown()
        if self._worker is not None:
            self.cancel()
            self._worker.wait()
            self._release_worker(self._worker)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.cancel()
        super().closeEvent(event)

    def hideEvent(self, event: QtGui.QHideEvent) -> None:
        self.cancel()
        super().hideEvent(event)


def open_laser_cam(app: object) -> LaserCamPanel:
    """Lazily create or show the one host-owned dock without legacy UI dependencies."""
    host = LaserCamHost(app)
    panel = host.existing_panel()
    if panel is None:
        panel = LaserCamPanel(host)
        host.parent_widget().addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, panel)
        host.remember_panel(panel)
    panel.show()
    panel.raise_()
    return panel
