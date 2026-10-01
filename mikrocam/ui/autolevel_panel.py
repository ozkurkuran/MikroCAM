"""Current offline surface compensation review and existing Machine handoff."""
import builtins
from collections.abc import Callable
import gettext
from io import StringIO
from itertools import islice
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets
from mikrocam.bridge.probe_files import load_probe_map
from mikrocam.bridge.autolevel_files import save_autolevel_gcode
from mikrocam.core.autolevel import AutoLevelResult
from mikrocam.core.autolevel_surface import AutoLevelSettings
from mikrocam.core.probe_map import ProbeMap
from mikrocam.core.gcode_models import SourceSnapshot, PreflightReport
from .autolevel_worker import AutoLevelWorker

_=getattr(builtins,'_',gettext.gettext)
Binding=tuple[SourceSnapshot,PreflightReport]
JOIN_TIMEOUT_MS=2000
PREVIEW_LINES=200


class AutoLevelPanel(QtWidgets.QDockWidget):
    reviewed_changed=QtCore.pyqtSignal()

    def __init__(self,parent: QtWidgets.QWidget | None=None,*,source: SourceSnapshot,
                 report: PreflightReport,binding_provider: Callable[[],Binding | None] | None=None,
                 job_receiver: Callable | None=None,
                 protected_paths_provider: Callable[[],tuple[Path,...]] | None=None) -> None:
        super().__init__(_('Auto-level'),parent)
        self.setObjectName('MikroCAMAutoLevelPanel')
        self.job_receiver=job_receiver
        self.source=self.original_report=self.map=self.result=None
        self._worker=None
        self._generation=self._worker_generation=0
        self._cancel_notice_generation=None
        self._alive=self._original_valid=True
        self._binding_provider=self._binding_origin=None
        self._dialogs=[]
        self._map_path=None
        self._protected_paths_provider=protected_paths_provider
        self._build_ui()
        self._timer=QtCore.QTimer(self);self._timer.setInterval(500)
        self._timer.timeout.connect(self._refresh_original)
        self.set_source(source,report,binding_provider,protected_paths_provider=protected_paths_provider)
        self._timer.start()

    def _build_ui(self) -> None:
        content=QtWidgets.QWidget(self);layout=QtWidgets.QVBoxLayout(content)
        self.load_button=QtWidgets.QPushButton(_('Load complete height map'))
        self.load_button.clicked.connect(lambda:self.load_map())
        layout.addWidget(self.load_button)
        self.map_label=QtWidgets.QLabel(_('No map loaded.'))
        self.map_label.setWordWrap(True);self.map_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        layout.addWidget(self.map_label)
        self.fields={};form=QtWidgets.QFormLayout()
        labels={'reference_z_mm':_('Reference surface work Z (mm)'),
                'max_segment_mm':_('Maximum XY segment (mm)'),
                'chord_error_mm':_('Arc chord error (mm)'),
                'surface_error_mm':_('Surface error on emitted chords (mm)')}
        for key,label in labels.items():
            edit=QtWidgets.QLineEdit();edit.setPlaceholderText(_('Required'))
            edit.textChanged.connect(lambda:self._invalidate(_('Parameters changed. Prepare again.')))
            self.fields[key]=edit;form.addRow(label,edit)
        layout.addLayout(form)
        self.confirm_checkbox=QtWidgets.QCheckBox(_("I verified the board placement and this map's G54 frame."))
        self.confirm_checkbox.toggled.connect(self._sync_controls);layout.addWidget(self.confirm_checkbox)
        buttons=QtWidgets.QHBoxLayout()
        self.prepare_button=QtWidgets.QPushButton(_('Prepare compensated job'))
        self.cancel_button=QtWidgets.QPushButton(_('Cancel'))
        self.save_button=QtWidgets.QPushButton(_('Save separate G-code'))
        self.transfer_button=QtWidgets.QPushButton(_('Load reviewed job into Machine'))
        for button in (self.prepare_button,self.cancel_button,self.save_button,self.transfer_button):
            buttons.addWidget(button)
        self.prepare_button.clicked.connect(self.prepare);self.cancel_button.clicked.connect(self.cancel)
        self.save_button.clicked.connect(self.choose_save);self.transfer_button.clicked.connect(self.transfer)
        layout.addLayout(buttons)
        self.summary_label=QtWidgets.QLabel();self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(QtCore.Qt.TextFormat.PlainText);layout.addWidget(self.summary_label)
        self.preview_table=QtWidgets.QTableWidget(0,3)
        self.preview_table.setHorizontalHeaderLabels([_('Derived line'),_('Original line'),_('Preview')])
        self.preview_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.horizontalHeader().setStretchLastSection(True);layout.addWidget(self.preview_table,1)
        self.setWidget(content)

    @property
    def busy(self) -> bool:
        return self._worker is not None

    def _sync_controls(self) -> None:
        usable=self._alive and self._original_valid
        current=usable and self.result is not None and not self.busy and self.confirm_checkbox.isChecked()
        self.prepare_button.setEnabled(usable and not self.busy)
        self.cancel_button.setEnabled(self.busy)
        self.load_button.setEnabled(self._alive and not self.busy)
        self.save_button.setEnabled(current)
        self.transfer_button.setEnabled(current and self.job_receiver is not None)

    def _invalidate(self,message: str) -> None:
        self._generation+=1;self.result=None
        self._cancel_notice_generation=None
        self.confirm_checkbox.setChecked(False);self.preview_table.setRowCount(0)
        if self._worker is not None:self._worker.cancel()
        self.summary_label.setText(message);self._sync_controls();self.reviewed_changed.emit()

    def set_source(self,source: SourceSnapshot,report: PreflightReport,
                   binding_provider: Callable[[],Binding | None] | None=None, *,
                   protected_paths_provider: Callable[[],tuple[Path,...]] | None=None) -> None:
        if (type(source) is not SourceSnapshot or type(report) is not PreflightReport or not report.allowed
                or source.sha256!=report.source_sha256 or source.name!=report.source_name):
            raise ValueError(_('Auto-level requires the exact current successful original review.'))
        if self._binding_origin is not None and hasattr(self._binding_origin,'reviewed_changed'):
            try:self._binding_origin.reviewed_changed.disconnect(self._refresh_original)
            except (TypeError,RuntimeError):pass
        self.source,self.original_report=source,report
        self._protected_paths_provider=protected_paths_provider
        self._binding_provider=binding_provider;self._binding_origin=getattr(binding_provider,'__self__',None)
        if self._binding_origin is not None and hasattr(self._binding_origin,'reviewed_changed'):
            self._binding_origin.reviewed_changed.connect(self._refresh_original)
        self._alive=self._original_valid=True
        self._invalidate(_('Load a complete map and enter reference/tolerances.'))
        self._refresh_original()

    def _refresh_original(self) -> bool:
        try:valid=self._binding_provider is None or self._binding_provider()==(self.source,self.original_report)
        except Exception:valid=False
        if not valid and self._original_valid:
            self._original_valid=False;self._invalidate(_('Original preflight changed or closed. Reopen Auto-level.'))
        return valid and self._original_valid

    def set_map(self,value: ProbeMap) -> None:
        if type(value) is not ProbeMap:raise ValueError(_('A validated height map is required.'))
        self.map=value
        self._map_path=None
        self.map_label.setText(_('Map origin: {origin}; outcome: {outcome}; samples: {done}/{total}; '
            'G54 offset: {offset}. Match the same fixed board setup.').format(origin=value.origin,
            outcome=value.outcome,done=value.completed,total=value.grid.count,offset=value.g54_offset_mm))
        self._invalidate(_('Map changed. Prepare and review again.'))

    def _file_dialog(self,save: bool,callback: Callable) -> None:
        dialog=QtWidgets.QFileDialog(self,_('Save compensated G-code') if save else _('Load height map'))
        dialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog,True)
        dialog.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave if save
                             else QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        dialog.setNameFilter(_('G-code (*.nc)') if save else _('Probe map (*.json)'))
        if save:dialog.setDefaultSuffix('nc')
        else:dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
        dialog.fileSelected.connect(callback)
        self._dialogs.append(dialog)
        def release():
            if dialog in self._dialogs:self._dialogs.remove(dialog)
            dialog.deleteLater()
        dialog.finished.connect(release);dialog.show()

    def load_map(self,path: Path | str | None=None) -> None:
        if path is None:
            if self.load_button.isEnabled():self._file_dialog(False,self.load_map)
            return
        try:
            self.set_map(load_probe_map(path))
            self._map_path=Path(path).resolve()
        except (ValueError,OSError) as error:self._invalidate(_('Map load failed: ')+str(error)[:256])

    def settings(self) -> AutoLevelSettings:
        if self.map is None:raise ValueError(_('Load a complete height map.'))
        try:values={key:float(edit.text().strip()) for key,edit in self.fields.items()}
        except ValueError as error:raise ValueError(_('Enter all reference/tolerance values explicitly.')) from error
        return AutoLevelSettings(self.map,**values)

    def prepare(self) -> None:
        if not self._alive or self.busy or not self._refresh_original():return
        try:settings=self.settings()
        except ValueError as error:self._invalidate(str(error));return
        self._invalidate(_('Preparing a separate compensated snapshot...'))
        worker=AutoLevelWorker(self.source,self.original_report,settings,self)
        self._worker,self._worker_generation=worker,self._generation
        for signal,slot in ((worker.completed,self._completed),(worker.failed,self._failed),
                            (worker.cancelled,self._cancelled),(worker.finished,self._finished)):
            signal.connect(slot,QtCore.Qt.ConnectionType.QueuedConnection)
        self._sync_controls();worker.start()

    def cancel(self) -> None:
        if self._worker is not None:
            self._invalidate(_('Cancelling compensation...'))
            self._cancel_notice_generation=self._generation

    def _current_result(self) -> bool:
        return (self._worker is not None and self.sender() is self._worker and self._alive
                and not self._worker.is_cancelled() and self._worker_generation==self._generation
                and self._refresh_original())

    def _completed(self,result: AutoLevelResult) -> None:
        if not self._current_result():return
        if (type(result) is not AutoLevelResult or result.original_source!=self.source
                or result.original_report!=self.original_report or result.settings!=self.settings()):
            self._invalidate(_('Compensation returned mismatched inputs.'));return
        self.result=result;job=result.prepared_job
        self.summary_label.setText(_('Original: {name}\nOriginal SHA256: {original}\nMap SHA256: {map}\n'
            'Derived SHA256: {derived}\nBounds mm: {bounds}; nominal seconds: {time}\n'
            'Reference work Z: {reference} mm; surface tolerance: {tolerance} mm on emitted chords.\n'
            'Preview: first {limit} of {total} lines. Simulation is not physical validation. '
            'Rapid clearance and board registration must be verified.').format(name=self.source.name,
            original=self.source.sha256,map=result.settings.map_sha256,derived=job.source.sha256,
            bounds=job.report.bounds_mm,time=job.report.duration_seconds,reference=result.settings.reference_z_mm,
            tolerance=result.settings.surface_error_mm,limit=PREVIEW_LINES,total=len(result.lineage)))
        self.preview_table.setRowCount(min(PREVIEW_LINES,len(result.lineage)))
        for row,(text,origin) in enumerate(zip(islice(StringIO(job.source.text),PREVIEW_LINES),result.lineage)):
            for column,value in enumerate((str(row+1),_('Generated') if origin is None else str(origin),text.strip())):
                self.preview_table.setItem(row,column,QtWidgets.QTableWidgetItem(value))
        self._sync_controls()

    def reviewed_binding(self) -> Binding | None:
        if (not self._alive or not self._refresh_original() or self.busy or self.result is None
                or not self.confirm_checkbox.isChecked()):return None
        if self.result.settings!=self.settings():return None
        return self.result.prepared_job.source,self.result.prepared_job.report

    def choose_save(self) -> None:
        if self.reviewed_binding() is not None:self._file_dialog(True,self.save_path)

    def save_path(self,path: Path | str) -> None:
        if self.reviewed_binding() is None:return
        try:
            inputs=() if self._protected_paths_provider is None else self._protected_paths_provider()
            if self._map_path is not None:inputs=(*inputs,self._map_path)
            save_autolevel_gcode(path,self.result,protected_paths=inputs)
        except (ValueError,OSError) as error:self.summary_label.setText(_('Export failed: ')+str(error)[:256])

    def transfer(self) -> None:
        binding=self.reviewed_binding()
        if binding is None or self.job_receiver is None:return
        try:self.job_receiver(*binding,self.reviewed_binding)
        except Exception as error:self.summary_label.setText(_('Transfer failed: ')+str(error)[:256])

    def _failed(self,message: str) -> None:
        if self._current_result():self.summary_label.setText(_('Compensation failed: ')+_(message))

    def _cancelled(self) -> None:
        if self.sender() is self._worker and self._cancel_notice_generation==self._generation:
            self.summary_label.setText(_('Compensation cancelled.'))

    def _finished(self) -> None:
        self._release_worker(self.sender())

    def _release_worker(self,expected: QtCore.QObject,timeout: int=JOIN_TIMEOUT_MS) -> bool:
        worker=self._worker
        if worker is None or worker is not expected:return worker is None
        if not worker.wait(timeout):
            self.summary_label.setText(_('Compensation is still stopping; keep this window open.'));return False
        self._worker=None;worker.deleteLater();self._sync_controls();return True

    def shutdown(self,timeout: int=JOIN_TIMEOUT_MS) -> bool:
        self._alive=False;self._timer.stop();self._invalidate(_('Compensation review closed.'))
        for dialog in tuple(self._dialogs):dialog.close()
        return self._worker is None or self._release_worker(self._worker,timeout)

    def closeEvent(self,event: QtGui.QCloseEvent) -> None:
        if not self.shutdown():event.ignore();return
        super().closeEvent(event)

    def showEvent(self,event: QtGui.QShowEvent) -> None:
        self._alive=True;self._timer.start();self._refresh_original();self._sync_controls()
        super().showEvent(event)
