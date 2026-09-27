"""Desktop current Geometry review with explicit selection and Excellon persistence."""
from copy import deepcopy
from pathlib import Path


def _snapshot(owner):
    from shapely import to_wkb
    return (owner.units, owner.multigeo, deepcopy(owner.obj_options), deepcopy(owner.tools),
            tuple(to_wkb(value) for value in owner.solid_geometry), owner.source_file)


def _prepare_source(app):
    from shapely.geometry import Point
    from shapely.affinity import scale
    def initialize(obj, _app):
        factor = 1 if obj.units == 'MM' else 1 / 25.4
        obj.multigeo = False
        obj.solid_geometry = [scale(Point(x, 37).buffer(d / 2, quad_segs=32),
            xfact=factor, yfact=factor, origin=(0, 0)) for x, d in ((15, .8), (25, 1), (35, 1.2))]
        obj.source_file = 'Original in-memory Geometry; no source reparse.'
        for tool in obj.tools.values():
            tool['solid_geometry'] = list(obj.solid_geometry)
    assert app.app_obj.new_object('geometry', 'smoke_geometry_source', initialize) != 'fail'


def _reopen(app, qapp, project, previous, errors, pump_until):
    from PyQt6 import QtCore, QtWidgets
    accepted = []
    def accept_settings():
        for dialog in qapp.topLevelWidgets():
            if not isinstance(dialog, QtWidgets.QMessageBox) or not dialog.isVisible():
                continue
            if dialog.windowTitle() != 'Import Settings':
                errors.append(RuntimeError(f'Unexpected Geometry drill reopen dialog: {dialog.windowTitle()}'))
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
        pump_until(qapp, lambda: app.collection.get_by_name('smoke_geometry_drills') is not None
                   and app.collection.get_by_name('smoke_geometry_drills') is not previous
                   and app.workers._pending_count == 0, errors, 'Geometry drill project reopen')
    finally:
        timer.stop()
    assert accepted == ['Import Settings']


def geometry_drill_journey(app, qapp, sandbox, errors, pump_until, root):
    from PyQt6 import QtCore, QtWidgets
    from mikrocam.ui.geometry_drills import GeometryDrillDialog
    from mikrocam.bridge.geometry_drills import load_geometry_review
    from smoke_svg_drills import _check
    assert not app.collection.get_names()
    default_keys = ('units', 'tools_mill_feedrate', 'tools_mill_cutz')
    defaults = {key: deepcopy(app.options[key]) for key in default_keys}
    _prepare_source(app)
    pump_until(qapp, lambda: app.collection.get_by_name('smoke_geometry_source') is not None
               and app.workers._pending_count == 0, errors, 'Geometry drill source creation')
    owner = app.collection.get_by_name('smoke_geometry_source')
    app.collection.set_active('smoke_geometry_source')
    original = _snapshot(owner)
    dialog = GeometryDrillDialog(app, owner)
    dialog.analyse()
    assert dialog.review is not None and len(dialog.review.candidates) == 3, dialog.status_label.text()
    review = dialog.review
    assert not dialog.create_button.isEnabled()
    dialog.name_edit.setText('smoke_geometry_drills')
    for row in (0, 2):
        dialog.table.item(row, 0).setCheckState(QtCore.Qt.CheckState.Checked)
    assert dialog.create_button.isEnabled()
    dialog.show()
    qapp.processEvents()
    screenshot = Path(root) / '.venv/geometry-drill-smoke.png'
    assert dialog.grab().save(str(screenshot))
    dialog.create_selected()
    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted, dialog.status_label.text()
    dialog.deleteLater()
    pump_until(qapp, lambda: app.collection.get_by_name('smoke_geometry_drills') is not None
               and app.workers._pending_count == 0, errors, 'Geometry selected drill creation')
    previous = _check(app, 'smoke_geometry_drills')
    assert _snapshot(owner) == original and load_geometry_review(owner) == review
    assert {key: app.options[key] for key in default_keys} == defaults
    exported = sandbox / 'geometry-drills.drl'
    assert app.f_handlers.export_excellon('smoke_geometry_drills', str(exported), use_thread=False) != 'fail'
    app.f_handlers.open_excellon(str(exported), outname='smoke_geometry_reparsed')
    pump_until(qapp, lambda: app.collection.get_by_name('smoke_geometry_reparsed') is not None
               and app.workers._pending_count == 0, errors, 'Geometry drill export reparse')
    unit_mm = 25.4 if app.options['excellon_exp_units'] == 'INCH' else 1
    tool_decimals = 4 if unit_mm == 25.4 else 2
    tolerance = max(10 ** -app.options['excellon_exp_decimals'], 10 ** -tool_decimals) * unit_mm + .0001
    _check(app, 'smoke_geometry_reparsed', tolerance)
    project = sandbox / 'geometry-drills.FlatPrj'
    app.f_handlers.save_project(str(project), silent=True)
    assert project.is_file() and project.stat().st_size > 0
    _reopen(app, qapp, project, previous, errors, pump_until)
    _check(app, 'smoke_geometry_drills')
    _check(app, 'smoke_geometry_reparsed', tolerance)
    restored = app.collection.get_by_name('smoke_geometry_source')
    assert _snapshot(restored) == original and load_geometry_review(restored) == review
    assert {key: app.options[key] for key in default_keys} == defaults
    print('GEOMETRY_DRILL_SELECTED_EXCELLON_ROUNDTRIP_OK', review.geometry_sha256, screenshot, flush=True)
    app.collection.delete_all()
    pump_until(qapp, lambda: not app.collection.get_names() and app.workers._pending_count == 0,
               errors, 'Geometry drill owned object cleanup')
    app.should_we_save = False
