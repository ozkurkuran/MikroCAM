"""Parent-owned, read-only presentation of retained historical import evidence."""
import builtins
import gettext

from PyQt6 import QtCore, QtWidgets

from mikrocam.core.import_report import ImportReport
from mikrocam.bridge.import_report import read_import_report


_ = getattr(builtins, '_', gettext.gettext)
HISTORICAL = _('Historical import evidence; not a current geometry audit or machine readiness check.')


def _plain(value: str) -> str:
    """Keep markup literal and escape control characters into bounded visible text."""
    return ''.join(char if char.isprintable() else char.encode('unicode_escape').decode('ascii')
                   for char in value)


def _format_report(report: ImportReport) -> str:
    coordinates, quality = report.coordinates, report.quality
    absent, unavailable = _('Absent'), _('Unavailable')
    width = absent if coordinates.source_width is None else _plain(coordinates.source_width)
    height = absent if coordinates.source_height is None else _plain(coordinates.source_height)
    lines = [HISTORICAL,
        _('Source: {name}').format(name=_plain(report.source_name)),
        f'SHA-256: {report.source_sha256}',
        _('Original width: {value}; unit: {unit}').format(value=width, unit=coordinates.source_units[0]),
        _('Original height: {value}; unit: {unit}').format(value=height, unit=coordinates.source_units[1]),
        f'viewBox: {coordinates.view_box if coordinates.view_box is not None else unavailable}',
        _('Aspect ratio: {value}').format(value=coordinates.aspect_ratio),
        _('Physical viewport (mm): {value}').format(value=coordinates.viewport_mm),
        _('Root source-to-mm mapping (a,b,d,e,xoff,yoff): {value}').format(value=coordinates.matrix_mm),
        _('Vertically flipped: {value}').format(value=_('Yes') if coordinates.flipped else _('No')),
        _('Material bounds (mm; minX,minY,maxX,maxY): {value}').format(
            value=quality.bounds_mm if quality.bounds_mm is not None else unavailable),
        _('Material components: {count}').format(count=quality.geometry_count),
        _('Valid: {valid}; invalid: {invalid}; empty: {empty}').format(
            valid=quality.valid_count, invalid=quality.invalid_count, empty=quality.empty_count),
        _('Source paths — open: {open}; closed: {closed}').format(open=quality.open_paths, closed=quality.closed_paths),
        _('Declared approximation precision (mm): {value}').format(
            value=quality.precision_mm if quality.precision_mm is not None else unavailable),
        _('Notices:')]
    for notice in report.notices:
        identity = f' [{_plain(notice.element_id)}]' if notice.element_id else ''
        lines.append(f'{_plain(notice.code)}{identity}: {_plain(notice.message)}')
    if not report.notices:
        lines.append(_('None recorded.'))
    return '\n'.join(lines)


class ImportReportSection(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toggle = QtWidgets.QToolButton(self)
        self.toggle.setText(_('Import report'))
        self.toggle.setCheckable(True)
        self.toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(QtCore.Qt.ArrowType.RightArrow)
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
        self.set_report(None)

    def _toggle(self, expanded: bool) -> None:
        self.details.setVisible(expanded)
        self.toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow if expanded else QtCore.Qt.ArrowType.RightArrow)

    def set_report(self, report: ImportReport | None, error: str = '') -> None:
        """Replace the complete presentation; unavailable evidence never retains old facts."""
        if report is not None and type(report) is not ImportReport:
            report, error = None, _('Invalid import report record.')
        if error:
            report = None
        if report is None:
            self.details.clear()
            self.toggle.setChecked(False)
            self.details.hide()
            self.toggle.setEnabled(False)
            message = HISTORICAL + '\n' + _('Unavailable.')
            if error:
                message += ' ' + _plain(str(error)[:512])
            self.summary_label.setText(message)
            return
        self.toggle.setEnabled(True)
        quality = report.quality
        self.summary_label.setText(HISTORICAL + '\n' + _('Material components: {count}; open paths: {open}; '
            'closed paths: {closed}.').format(count=quality.geometry_count, open=quality.open_paths,
                                            closed=quality.closed_paths))
        self.details.setPlainText(_format_report(report))


def attach_import_report(owner: object) -> None:
    """Reuse one section in the owner's current Properties UI; read retained data only."""
    ui = owner.ui
    section = getattr(ui, 'mikrocam_import_report', None)
    if section is None:
        section = ImportReportSection(ui)
        ui.custom_box.insertWidget(2, section)
        ui.mikrocam_import_report = section
    try:
        report = read_import_report(owner)
    except ValueError as error:
        section.set_report(None, error=str(error))
        section.show()
        return
    section.set_report(report)
    section.setVisible(report is not None)
