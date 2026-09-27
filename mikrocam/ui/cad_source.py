"""Collapsed historical producer evidence; source claims never imply authorship."""
import builtins
import gettext
from pathlib import Path

from PyQt6 import QtCore, QtWidgets

from mikrocam.bridge.cad_source import read_cad_source, store_cad_source
from mikrocam.core.cad_source import CadSourceAssessment


_ = getattr(builtins, '_', gettext.gettext)
HISTORICAL = _('Historical source evidence; producer declarations do not prove authorship.')


def _plain(value: str) -> str:
    return ''.join(char if char.isprintable() else char.encode('unicode_escape').decode('ascii')
                   for char in value)


def _details(record: CadSourceAssessment) -> str:
    lines = [HISTORICAL,
             _('Source: {name}').format(name=_plain(record.source_name)),
             _('Format: {format}').format(format=record.source_format),
             _('Application: {application}; status: {status}').format(
                 application=record.application, status=_(record.status)),
             _('Reason: {reason}').format(reason=_plain(record.reason)),
             'SHA-256: ' + (record.source_sha256 or _('Unavailable')),
             _('Evidence:')]
    lines.extend(f'{claim.application} | {_plain(claim.field)}: {_plain(claim.value)}'
                 for claim in record.evidence)
    if not record.evidence:
        lines.append(_('None recorded.'))
    return '\n'.join(lines)


class CadSourceSection(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toggle = QtWidgets.QToolButton(self)
        self.toggle.setText(_('CAD source evidence'))
        self.toggle.setCheckable(True)
        self.toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        layout.addWidget(self.toggle)
        self.summary_label = QtWidgets.QLabel(self)
        self.summary_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        self.details = QtWidgets.QPlainTextEdit(self)
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(120)
        self.details.setMaximumHeight(260)
        layout.addWidget(self.details)
        self.toggle.toggled.connect(self._toggle)
        self.set_assessment(None)

    def _toggle(self, expanded: bool) -> None:
        self.details.setVisible(expanded)
        self.toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow if expanded else QtCore.Qt.ArrowType.RightArrow)

    def set_assessment(self, record: CadSourceAssessment | None, error: str = '') -> None:
        """Replace all displayed facts; errors and absent records cannot retain success."""
        if record is not None and type(record) is not CadSourceAssessment:
            record, error = None, _('Invalid source assessment record.')
        if error:
            record = None
        if record is None:
            self.details.clear()
            self.toggle.setChecked(False)
            self._toggle(False)
            self.toggle.setEnabled(False)
            message = HISTORICAL + '\n' + _('Unavailable.')
            if error:
                message += ' ' + _plain(str(error)[:512])
            self.summary_label.setText(message)
            return
        self.toggle.setEnabled(True)
        self.summary_label.setText(HISTORICAL + '\n' +
            _('Application: {application}; status: {status}. {reason}').format(
                application=record.application, status=_(record.status), reason=_plain(record.reason)))
        self.details.setPlainText(_details(record))


def attach_cad_source(owner: object) -> None:
    """Reuse one child section in the current object's Properties UI, reading stored data only."""
    ui = owner.ui
    section = getattr(ui, 'mikrocam_cad_source', None)
    if section is None:
        section = CadSourceSection(ui)
        ui.custom_box.insertWidget(min(3, ui.custom_box.count()), section)
        ui.mikrocam_cad_source = section
    try:
        record = read_cad_source(owner)
    except ValueError as error:
        section.set_assessment(None, error=str(error))
        section.show()
        return
    section.set_assessment(record)
    section.setVisible(record is not None)


def record_cad_source(owner: object, source: str, filename: str, source_format: str) -> None:
    """Record a completed import without touching widgets, including worker-thread imports."""
    store_cad_source(owner, source, Path(filename).name[:256], source_format)
