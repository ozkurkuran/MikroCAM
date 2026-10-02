"""Thin optional KiCad export/direct-import UI over the existing manufacturing owner."""
import builtins
import gettext
from pathlib import Path
import tempfile
from typing import Any
from PyQt6 import QtCore,QtWidgets
from mikrocam.core.kicad_transfer import json_object
from mikrocam.kicad.export import export_board
from mikrocam.kicad.package import read_package
from mikrocam.bridge.kicad_transfer import prepare_transfer,attach_transfer_metadata
from mikrocam.ui.manufacturing_import import ManufacturingImportDialog,_plain

_=getattr(builtins,'_',gettext.gettext)


class KiCadExportWorker(QtCore.QObject):
    finished=QtCore.pyqtSignal(object)

    def __init__(self,board: Path,output: Path,parent: QtCore.QObject) -> None:
        super().__init__(parent);self.board=board;self.output=output

    def run(self) -> None:
        try:
            export_board(self.board,self.output);result=(self.output,'')
        except Exception as error:result=(None,str(error)[:500])
        self.finished.emit(result)


class KiCadTransferDialog(ManufacturingImportDialog):
    def __init__(self,app: Any) -> None:
        super().__init__(app)
        self.setWindowTitle(_('KiCad → MikroCAM'))
        self._temporary=tempfile.TemporaryDirectory(prefix='mikrocam-transfer-')
        temporary=self._temporary
        self.finished.connect(lambda _result:temporary.cleanup())
        self.destroyed.connect(lambda:temporary.cleanup())
        self.package=None;self._export_worker=None
        self.summary=QtWidgets.QLabel(self)
        self.summary.setTextFormat(QtCore.Qt.TextFormat.PlainText);self.summary.setWordWrap(True)
        self.layout().insertWidget(0,self.summary)
        self.acknowledge=QtWidgets.QCheckBox(_('I reviewed the DRC errors and want to import for CAM inspection.'),self)
        self.layout().insertWidget(1,self.acknowledge);self.acknowledge.hide()
        self.acknowledge.toggled.connect(lambda _checked:self.review_selected())
        self.report_button=QtWidgets.QPushButton(_('View DRC report'),self)
        self.layout().insertWidget(2,self.report_button)
        self.report_button.setEnabled(False);self.report_button.clicked.connect(self.show_drc_report)
        self.add_button.hide();self.inspect_button.hide()
        self.setAcceptDrops(False)

    def load_path(self,path: Path) -> None:
        if self.busy:return
        source=Path(path)
        if source.suffix.lower()=='.kicad_pcb':
            self._set_busy(True)
            self.summary.setText(_('KiCad is checking and exporting a private board copy…'))
            out=Path(self._temporary.name)/'production.mcam-transfer'
            self._export_worker=KiCadExportWorker(source,out,self)
            self._export_worker.finished.connect(self._export_finished,QtCore.Qt.ConnectionType.QueuedConnection)
            try:self.app.worker_task.emit({'fcn':self._export_worker.run,'params':[]})
            except Exception as error:self._export_finished((None,str(error)))
            return
        try:
            package=read_package(source)
            review=prepare_transfer(package,Path(self._temporary.name)/'files')
            self.package=package;self.files=review.files;self.report_button.setEnabled(True)
            self._paths=tuple(f.path for f in self.files);self._inspected_paths=self._paths
            self._show_files()
            for i,row in enumerate(package.manifest.files):
                self.table.cellWidget(i,2).setCurrentText(row.kind)
                self.table.cellWidget(i,3).setCurrentText(row.role)
                self.table.cellWidget(i,2).setEnabled(False);self.table.cellWidget(i,3).setEnabled(False)
            m=package.manifest
            self.summary.setText(_('Board: {board} · KiCad {version}\nDRC: {errors} errors, {warnings} warnings, {unconnected} unconnected items. Skipped empty files: {empty}. Common origin; no mirror.').format(board=_plain(m.board_name),version=m.kicad_version,errors=m.drc_errors,warnings=m.drc_warnings,unconnected=m.drc_unconnected,empty=len(m.skipped_empty)))
            self.acknowledge.setVisible(m.needs_acknowledgement)
            self.review_selected()
            if not m.needs_acknowledgement:self.import_selected()
        except Exception as error:
            self.review=None;self.import_button.setEnabled(False)
            self.status_label.setText(_('KiCad transfer failed: ')+_plain(str(error)[:500]))

    def show_drc_report(self) -> None:
        if self.package is None:return
        import json
        dialog=QtWidgets.QDialog(self);dialog.setWindowTitle(_('KiCad DRC report'));dialog.resize(900,650)
        layout=QtWidgets.QVBoxLayout(dialog)
        text=QtWidgets.QPlainTextEdit(dialog);text.setReadOnly(True)
        text.setPlainText(json.dumps(json_object(self.package.drc_bytes),ensure_ascii=False,indent=2))
        layout.addWidget(text);close=QtWidgets.QPushButton(_('Close'),dialog);close.clicked.connect(dialog.accept);layout.addWidget(close)
        dialog.exec();dialog.deleteLater()

    @QtCore.pyqtSlot(object)
    def _export_finished(self,result: tuple) -> None:
        self._set_busy(False)
        if self._export_worker is not None:self._export_worker.deleteLater();self._export_worker=None
        path,error=result
        if error:self.status_label.setText(_('KiCad export failed: ')+_plain(error));return
        self.load_path(path)

    def review_selected(self) -> None:
        if self.busy or self.package is None:return
        super().review_selected()
        if self.package.manifest.needs_acknowledgement and not self.acknowledge.isChecked():
            self.import_button.setEnabled(False)
            self.status_label.setText(_('Review the DRC report before acknowledging errors.'))

    def import_selected(self) -> None:
        if self.package is None or self.package.manifest.needs_acknowledgement and not self.acknowledge.isChecked():return
        self.acknowledge.setEnabled(False)
        super().import_selected()

    def _progress(self,receipt: object) -> None:
        if receipt.owner is not None and self.package is not None:
            attach_transfer_metadata(receipt.owner,self.package.manifest)
        super()._progress(receipt)

    def _finished(self,result: tuple) -> None:
        super()._finished(result)
        self.acknowledge.setEnabled(True)
        if not result[1] and len(self.imported_indices)==len(self.files):
            self.app.inform.emit('[success] '+_('KiCad production files imported into MikroCAM.'))


def open_kicad_transfer(app: Any,path: str | None = None) -> None:
    active=getattr(app,'_kicad_transfer_dialog',None)
    if active is not None:
        active.show();active.raise_();active.activateWindow()
        app.inform.emit('[WARNING] '+_('A KiCad transfer is already open. Close it before another transfer.'))
        return
    if path is None:
        path,_filter=QtWidgets.QFileDialog.getOpenFileName(app.ui,_('Open KiCad board or transfer'),'',_('KiCad PCB or transfer (*.kicad_pcb *.mcam-transfer)'))
    if not path:return
    dialog=KiCadTransferDialog(app);app._kicad_transfer_dialog=dialog
    dialog.finished.connect(lambda _result:setattr(app,'_kicad_transfer_dialog',None))
    dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
    dialog.show()
    QtCore.QTimer.singleShot(0,lambda:dialog.load_path(Path(path)))
