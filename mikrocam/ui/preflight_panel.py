"""Offline preflight dock with GUI-owned source freshness and worker lifetime."""
import builtins
from collections.abc import Callable
import gettext
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

from mikrocam.bridge.gcode_source import load_gcode_file, snapshot_cncjob
from mikrocam.core.gcode_models import MAX_FINDINGS, PreflightReport, SourceSnapshot
from .preflight_setup import PreflightSetupWidget
from .preflight_worker import PreflightWorker


_ = getattr(builtins, '_', gettext.gettext)
JOIN_TIMEOUT_MS = 2000


class PreflightPanel(QtWidgets.QDockWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None,
                 source_provider: Callable[[], SourceSnapshot] | None = None) -> None:
        super().__init__(_('G-code preflight'), parent)
        self.setObjectName('MikroCAMPreflightPanel')
        self.source_provider = source_provider
        self.source: SourceSnapshot | None = None
        self.report: PreflightReport | None = None
        self._worker: PreflightWorker | None = None
        self._generation = self._worker_generation = 0
        self._cancel_notice_generation: int | None = None
        self._selected = False
        self._request_source = self._request_setup = None
        self._build_ui()
        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.setInterval(500)
        self._refresh_timer.timeout.connect(self._refresh_selected)
        self._refresh_timer.start()

    def _build_ui(self) -> None:
        content = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(content)
        source_actions = QtWidgets.QHBoxLayout()
        self.load_button = QtWidgets.QPushButton(_('Load file'))
        self.selected_button = QtWidgets.QPushButton(_('Use selected CNC job'))
        self.load_button.clicked.connect(lambda: self.load_file())
        self.selected_button.clicked.connect(self.use_selected)
        source_actions.addWidget(self.load_button)
        source_actions.addWidget(self.selected_button)
        layout.addLayout(source_actions)
        self.source_label = QtWidgets.QLabel(_('No source loaded.'))
        self.source_label.setWordWrap(True)
        self.source_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.source_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.source_label)
        self.setup_widget = PreflightSetupWidget()
        self.setup_widget.changed.connect(self._input_changed)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.setup_widget)
        layout.addWidget(scroll, 1)
        actions = QtWidgets.QHBoxLayout()
        self.analyze_button = QtWidgets.QPushButton(_('Analyze'))
        self.cancel_button = QtWidgets.QPushButton(_('Cancel'))
        self.analyze_button.clicked.connect(self.analyze)
        self.cancel_button.clicked.connect(self.cancel)
        actions.addWidget(self.analyze_button)
        actions.addWidget(self.cancel_button)
        layout.addLayout(actions)
        self.result_label = QtWidgets.QLabel(_('Supply explicit setup values before analysis.'))
        self.result_label.setWordWrap(True)
        self.result_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        layout.addWidget(self.result_label)
        self.findings_table = QtWidgets.QTableWidget(0, 4)
        self.findings_table.setHorizontalHeaderLabels([_('Line'), _('Severity'), _('Code'), _('Finding')])
        self.findings_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.findings_table.horizontalHeader().setStretchLastSection(True)
        self.findings_table.setMaximumHeight(180)
        layout.addWidget(self.findings_table)
        self.setWidget(content)
        self._sync_controls()

    @property
    def busy(self) -> bool:
        return self._worker is not None

    def _sync_controls(self) -> None:
        self.analyze_button.setEnabled(self.source is not None and not self.busy)
        self.cancel_button.setEnabled(self.busy)
        self.selected_button.setEnabled(self.source_provider is not None)

    def _invalidate(self, message: str) -> None:
        self._generation += 1
        self._cancel_notice_generation = None
        self.report = None
        self.findings_table.setRowCount(0)
        if self._worker is not None:
            self._worker.cancel()
        self.result_label.setText(message)
        self._sync_controls()

    def _input_changed(self) -> None:
        self._invalidate(_('Setup changed. Previous result is invalid.'))

    def load_source(self, source: SourceSnapshot) -> None:
        if not isinstance(source, SourceSnapshot):
            raise ValueError(_('A complete immutable source snapshot is required.'))
        self._selected = False
        self.source = source
        self._invalidate(_('Source changed. Previous result is invalid.'))
        self._label_source(_('Loaded snapshot'))
        self._sync_controls()

    def _label_source(self, kind: str) -> None:
        if self.source is None:
            self.source_label.setText(_('No source loaded.'))
        else:
            self.source_label.setText(f'{kind}: {self.source.name}\nSHA-256: {self.source.sha256}')

    def load_file(self, path: str | Path | None = None) -> None:
        if path is None:
            path, _filter = QtWidgets.QFileDialog.getOpenFileName(
                self, _('Load G-code snapshot'), '', _('G-code files (*.nc *.gcode *.tap);;All files (*)'))
            if not path:
                return
        try:
            source = load_gcode_file(path)
        except (OSError, ValueError, TypeError) as error:
            message = _('Error loading source: {message}').format(message=str(error))
            if self.source is not None:
                message += '\n' + _('The previous loaded snapshot remains selected; no result is current.')
            self._invalidate(message)
            return
        self.load_source(source)
        self._label_source(_('Loaded file snapshot (not a live file)'))

    def use_selected(self) -> None:
        try:
            if self.source_provider is None:
                raise ValueError(_('No selected CNC job provider is available.'))
            source = self.source_provider()
            self.load_source(source)
        except Exception as error:
            self.source = None
            self._selected = False
            self._invalidate(_('Selected source unavailable: {message}').format(message=str(error)))
            self._label_source('')
            return
        self._selected = True
        self._label_source(_('Selected CNC job snapshot'))

    def _refresh_selected(self) -> None:
        if not self._selected:
            return
        try:
            current = self.source_provider() if self.source_provider is not None else None
            changed = current != self.source
        except Exception:
            changed = True
        if changed:
            self.source = None
            self._selected = False
            self._invalidate(_('Selected CNC job changed or disappeared. Reload the source.'))
            self._label_source('')

    def analyze(self) -> None:
        if self.busy:
            return
        self._refresh_selected()
        try:
            if self.source is None:
                raise ValueError(_('Load a complete source snapshot first.'))
            setup = self.setup_widget.value()
        except (ValueError, TypeError) as error:
            self._invalidate(_('Cannot analyze: {message}').format(message=str(error)))
            return
        self._invalidate(_('Analyzing loaded snapshot…'))
        self._request_source, self._request_setup = self.source, setup
        worker = PreflightWorker(self.source, setup, self)
        self._worker, self._worker_generation = worker, self._generation
        worker.completed.connect(self._completed, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.failed.connect(self._failed, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.cancelled.connect(self._cancelled, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(self._finished, QtCore.Qt.ConnectionType.QueuedConnection)
        self._refresh_timer.start()
        self._sync_controls()
        worker.start()

    def cancel(self) -> None:
        if self._worker is not None:
            self._invalidate(_('Cancelling analysis…'))
            self._cancel_notice_generation = self._generation

    def _current_result(self) -> bool:
        return (self._worker is not None and self.sender() is self._worker
                and self._generation == self._worker_generation and not self._worker.is_cancelled())

    def _completed(self, report: PreflightReport) -> None:
        self._refresh_selected()
        if not self._current_result():
            return
        if (not isinstance(report, PreflightReport) or report.source_name != self._request_source.name
                or report.source_sha256 != self._request_source.sha256 or report.setup != self._request_setup):
            self._invalidate(_('Analysis returned mismatched source or setup evidence.'))
            return
        self.report = report
        self._render_report(report)

    def _render_report(self, report: PreflightReport) -> None:
        status = _('Declared-setup geometry checks passed.') if report.allowed else _('Blocked by findings or incomplete interpretation.')
        label = _('Full interpreted bounds (mm)') if report.complete else _('Partial interpreted bounds (mm)')
        bounds = _('Unavailable') if report.bounds_mm is None else str(report.bounds_mm)
        duration = _('Unknown') if report.duration_seconds is None else f'{report.duration_seconds:.6g} s'
        self.result_label.setText(
            f'{status}\n{label}: {bounds}\n' + _('Nominal duration: {duration}').format(duration=duration)
            + '\n' + _('Blocks: {count}; units: {units}; distance modes: {modes}.').format(
                count=report.executable_blocks, units=', '.join(report.units_seen) or _('None'),
                modes=', '.join(report.distance_modes_seen) or _('None'))
            + '\n' + _('Moves: {rapid} rapid, {linear} linear, {arc} arc; distance {distance:.6g} mm.').format(
                rapid=report.rapid_count, linear=report.linear_count, arc=report.arc_count, distance=report.distance_mm)
            + '\n' + _('Findings: {count} total, {errors} errors; showing at most {limit}.').format(
                count=report.finding_count, errors=report.error_count, limit=MAX_FINDINGS)
            + '\n' + _('Declared setup only: no physical clearance, controller compatibility or permission to run. '
                       'Initial G92 and tool-length offsets are assumed zero, not measured. '
                       'Nominal time excludes acceleration, scheduling, overrides and operator waiting.'))
        self.findings_table.setRowCount(min(len(report.findings), MAX_FINDINGS))
        for row, finding in enumerate(report.findings[:MAX_FINDINGS]):
            for column, text in enumerate((str(finding.line), _(finding.severity), finding.code, _(finding.message))):
                self.findings_table.setItem(row, column, QtWidgets.QTableWidgetItem(text))

    def _failed(self, message: str) -> None:
        if self._current_result():
            self.result_label.setText(_('Analysis failed: {message}').format(message=_(message)))

    def _cancelled(self) -> None:
        if (self._worker is not None and self.sender() is self._worker
                and self._cancel_notice_generation == self._generation):
            self.result_label.setText(_('Analysis cancelled. No current result.'))

    def _finished(self) -> None:
        self._release_worker(self.sender())

    def _release_worker(self, expected: QtCore.QObject) -> bool:
        worker = self._worker
        if worker is None or expected is not worker:
            return worker is None
        if not worker.wait(JOIN_TIMEOUT_MS):
            self.result_label.setText(_('Analysis is still stopping; keep this window open.'))
            return False
        if worker.is_cancelled() and self._cancel_notice_generation == self._generation:
            self.result_label.setText(_('Analysis cancelled. No current result.'))
        self._worker = None
        worker.deleteLater()
        self._sync_controls()
        return True

    def shutdown(self) -> bool:
        self._refresh_timer.stop()
        if self._worker is None:
            return True
        self.cancel()
        return self._release_worker(self._worker)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if not self.shutdown():
            event.ignore()
            return
        super().closeEvent(event)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        self._refresh_timer.start()
        self._refresh_selected()
        super().showEvent(event)


def open_preflight_panel(app: object) -> PreflightPanel:
    """Create one lazy dock; snapshot the currently selected job only on GUI request."""
    panel = getattr(app, '_mikrocam_preflight_panel', None)
    if panel is None:
        provider = lambda: snapshot_cncjob(app.collection.get_active())
        panel = PreflightPanel(app.ui, source_provider=provider)
        app.ui.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, panel)
        app._mikrocam_preflight_panel = panel
    panel.show()
    panel.raise_()
    return panel
