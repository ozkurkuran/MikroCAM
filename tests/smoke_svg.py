"""Authored SVG physical bounds and source preservation on the actual desktop."""
from hashlib import sha256
from pathlib import Path


def _check_object(app, name, kind, source):
    from shapely import union_all
    obj = app.collection.get_by_name(name)
    assert obj is not None and obj.kind == kind
    geometry = union_all(obj.solid_geometry)
    expected = (10., 30., 30., 40.)
    scale = 1. if obj.units.upper() == 'MM' else 1 / 25.4
    assert all(abs(actual - wanted * scale) < 1e-7 for actual, wanted in zip(geometry.bounds, expected))
    assert abs(geometry.area - 200 * scale ** 2) < 1e-7
    assert obj.source_file == source
    return obj


def _reopen(app, qapp, project, previous, errors, pump_until):
    from PyQt6 import QtCore, QtWidgets
    accepted = []

    def accept_settings():
        for dialog in qapp.topLevelWidgets():
            if not isinstance(dialog, QtWidgets.QMessageBox) or not dialog.isVisible():
                continue
            if dialog.windowTitle() != 'Import Settings':
                errors.append(RuntimeError(f'Unexpected SVG reopen dialog: {dialog.windowTitle()}'))
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
        pump_until(qapp, lambda: app.collection.get_by_name('smoke_svg_geometry') is not None
                   and app.collection.get_by_name('smoke_svg_geometry') is not previous
                   and app.workers._pending_count == 0, errors, 'SVG project reopen')
    finally:
        timer.stop()
    assert accepted == ['Import Settings']


def svg_journey(app, qapp, sandbox, errors, pump_until, root):
    root = Path(root)
    assert not app.collection.get_names(), 'SVG journey must precede the existing CAM flow'
    fixture = root / 'tests/reference/svg-physical-transform.svg'
    original = fixture.read_bytes()
    digest = sha256(original).hexdigest()
    source = original.decode('utf-8')
    names = {'smoke_svg_geometry': 'geometry', 'smoke_svg_gerber': 'gerber'}
    for name, kind in names.items():
        assert app.f_handlers.import_svg(str(fixture), geo_type=kind, outname=name, plot=True) != 'fail'
        pump_until(qapp, lambda: app.collection.get_by_name(name) is not None
                   and app.workers._pending_count == 0, errors, f'SVG {kind} import')
        _check_object(app, name, kind, source)
    previous = app.collection.get_by_name('smoke_svg_geometry')
    project = sandbox / 'svg-smoke.FlatPrj'
    app.f_handlers.save_project(str(project), silent=True)
    assert project.is_file() and project.stat().st_size > 0
    _reopen(app, qapp, project, previous, errors, pump_until)
    for name, kind in names.items():
        _check_object(app, name, kind, source)
    assert fixture.read_bytes() == original and sha256(fixture.read_bytes()).hexdigest() == digest
    app.ui.showMaximized()
    app.on_zoom_fit()
    qapp.processEvents()
    screenshot = root / '.venv/svg-smoke.png'
    assert app.ui.grab().save(str(screenshot))
    print('SVG_PHYSICAL_SOURCE_ROUNDTRIP_OK', digest, screenshot, flush=True)
    app.collection.delete_all()
    pump_until(qapp, lambda: not app.collection.get_names() and app.workers._pending_count == 0,
               errors, 'SVG owned fixture cleanup')
    app.should_we_save = False
