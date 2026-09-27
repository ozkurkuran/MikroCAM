"""Actual desktop SVG drill review, selection and Excellon/project round trips."""
from hashlib import sha256
from pathlib import Path


def _check(app, name):
    obj = app.collection.get_by_name(name)
    assert obj is not None and obj.kind == 'excellon'
    factor = 1. if obj.units.upper() == 'MM' else 25.4
    tools = sorted(obj.tools.values(), key=lambda t: t['tooldia'])
    assert len(tools) == 2 and sum(len(t['drills']) for t in tools) == 2
    for tool, diameter, center in zip(tools, (.8, 1.2), ((15., 37.), (35., 37.))):
        assert abs(tool['tooldia'] * factor - diameter) < .001
        assert len(tool['drills']) == 1 and tool['solid_geometry']
        point = tool['drills'][0]
        assert abs(point.x * factor - center[0]) < .001
        assert abs(point.y * factor - center[1]) < .001
    assert obj.source_file and 'M48' in obj.source_file and 'M30' in obj.source_file
    return obj


def _reopen(app, qapp, project, previous, errors, pump_until):
    from PyQt6 import QtCore, QtWidgets
    accepted = []

    def accept_settings():
        for dialog in qapp.topLevelWidgets():
            if not isinstance(dialog, QtWidgets.QMessageBox) or not dialog.isVisible():
                continue
            if dialog.windowTitle() != 'Import Settings':
                errors.append(RuntimeError(f'Unexpected drill reopen dialog: {dialog.windowTitle()}'))
                dialog.reject()
                continue
            for button in dialog.buttons():
                if dialog.buttonRole(button) == QtWidgets.QMessageBox.ButtonRole.YesRole:
                    accepted.append(dialog.windowTitle())
                    button.click()
                    break

    app.should_we_save = False
    timer = QtCore.QTimer()
    timer.timeout.connect(accept_settings)
    timer.start(50)
    try:
        app.f_handlers.open_project(str(project), plot=True)
        pump_until(qapp, lambda: app.collection.get_by_name('smoke_svg_drills') is not None
                   and app.collection.get_by_name('smoke_svg_drills') is not previous
                   and app.workers._pending_count == 0, errors, 'drill project reopen')
    finally:
        timer.stop()
    assert accepted == ['Import Settings']


def svg_drill_journey(app, qapp, sandbox, errors, pump_until, root):
    from PyQt6 import QtCore, QtWidgets
    from mikrocam.ui.svg_drills import SvgDrillDialog
    root = Path(root)
    assert not app.collection.get_names()
    fixture = root / 'tests/reference/svg-drills.svg'
    original = fixture.read_bytes()
    dialog = SvgDrillDialog(app)
    dialog.path_edit.setText(str(fixture))
    dialog.analyse()
    assert dialog.review is not None and len(dialog.review.candidates) == 3, dialog.status_label.text()
    assert not dialog.create_button.isEnabled()
    dialog.name_edit.setText('smoke_svg_drills')
    for row in (0, 2):
        dialog.table.item(row, 0).setCheckState(QtCore.Qt.CheckState.Checked)
    assert dialog.create_button.isEnabled()
    dialog.show()
    qapp.processEvents()
    screenshot = root / '.venv/svg-drill-smoke.png'
    assert dialog.grab().save(str(screenshot))
    dialog.create_selected()
    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted, dialog.status_label.text()
    dialog.deleteLater()
    pump_until(qapp, lambda: app.collection.get_by_name('smoke_svg_drills') is not None
               and app.workers._pending_count == 0, errors, 'SVG drill creation')
    previous = _check(app, 'smoke_svg_drills')
    exported = sandbox / 'svg-drills.drl'
    assert app.f_handlers.export_excellon('smoke_svg_drills', str(exported), use_thread=False) != 'fail'
    assert exported.is_file()
    app.f_handlers.open_excellon(str(exported), outname='smoke_reimported_drills')
    pump_until(qapp, lambda: app.collection.get_by_name('smoke_reimported_drills') is not None
               and app.workers._pending_count == 0, errors, 'SVG drill export reopen')
    _check(app, 'smoke_reimported_drills')
    project = sandbox / 'svg-drills.FlatPrj'
    app.f_handlers.save_project(str(project), silent=True)
    _reopen(app, qapp, project, previous, errors, pump_until)
    _check(app, 'smoke_svg_drills')
    _check(app, 'smoke_reimported_drills')
    assert fixture.read_bytes() == original
    print('SVG_DRILL_REVIEW_EXCELLON_ROUNDTRIP_OK', sha256(original).hexdigest(), screenshot, flush=True)
    app.collection.delete_all()
    pump_until(qapp, lambda: not app.collection.get_names() and app.workers._pending_count == 0,
               errors, 'SVG drill cleanup')
    app.should_we_save = False
