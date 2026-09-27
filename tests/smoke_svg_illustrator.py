"""Desktop round trip of original analytic artwork, not a vendor-export fixture."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


def _check(app, qapp, name, kind, source, digest):
    from shapely import union_all
    from mikrocam.bridge.import_report import read_import_report
    obj = app.collection.get_by_name(name)
    assert obj is not None and obj.kind == kind
    factor = 1. if obj.units.upper() == 'MM' else 25.4
    material = union_all(obj.solid_geometry)
    expected = (15., 16., 35., 29.)
    assert all(abs(value * factor - wanted) < 1e-6 for value, wanted in zip(material.bounds, expected))
    assert abs(material.area * factor ** 2 - 130) < .001
    assert material.is_valid and obj.source_file == source
    report = read_import_report(obj)
    assert report is not None and report.source_sha256 == digest
    assert report.coordinates.source_width == report.coordinates.source_height == '100%'
    assert report.coordinates.source_units == ('%', '%')
    assert all(abs(value - wanted) < 1e-6 for value, wanted in
               zip(report.coordinates.viewport_mm, (60., 40.)))
    assert all(abs(value - wanted) < 1e-6 for value, wanted in zip(report.quality.bounds_mm, expected))
    assert report.quality.closed_paths == 2 and report.quality.open_paths == 0
    assert report.quality.invalid_count == 0
    assert any('xmp' in notice.message.lower() for notice in report.notices)
    app.collection.set_active(name)
    app.ui.notebook.setCurrentWidget(app.ui.properties_tab)
    obj.build_ui()
    qapp.processEvents()
    section = obj.ui.mikrocam_import_report
    assert not section.isHidden()
    section.toggle.setChecked(True)
    qapp.processEvents()
    app.ui.properties_scroll_area.ensureWidgetVisible(section, 0, 10)
    qapp.processEvents()
    assert digest in section.details.toPlainText() and '100%' in section.details.toPlainText()
    return deepcopy(obj.import_report)


def _reopen(app, qapp, project, previous, errors, pump_until):
    from PyQt6 import QtCore, QtWidgets
    accepted = []

    def accept_settings():
        for dialog in qapp.topLevelWidgets():
            if not isinstance(dialog, QtWidgets.QMessageBox) or not dialog.isVisible():
                continue
            if dialog.windowTitle() != 'Import Settings':
                errors.append(RuntimeError(f'Unexpected Illustrator fixture reopen dialog: {dialog.windowTitle()}'))
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
        pump_until(qapp, lambda: app.collection.get_by_name('smoke_illustrator_geometry') is not None
                   and app.collection.get_by_name('smoke_illustrator_geometry') is not previous
                   and app.workers._pending_count == 0, errors, 'Illustrator fixture project reopen')
    finally:
        timer.stop()
    assert accepted == ['Import Settings']


def svg_illustrator_journey(app, qapp, sandbox, errors, pump_until, root):
    root = Path(root)
    assert not app.collection.get_names(), 'Illustrator fixture requires an empty smoke collection'
    fixture = root / 'tests/reference/svg-illustrator.svg'
    original = fixture.read_bytes()
    source = original.decode('utf-8')
    digest = sha256(original).hexdigest()
    names = {'smoke_illustrator_geometry': 'geometry', 'smoke_illustrator_gerber': 'gerber'}
    reports = {}
    for name, kind in names.items():
        assert app.f_handlers.import_svg(str(fixture), geo_type=kind, outname=name, plot=True) != 'fail'
        pump_until(qapp, lambda: app.collection.get_by_name(name) is not None
                   and app.workers._pending_count == 0, errors, f'Illustrator-style {kind} import')
        reports[name] = _check(app, qapp, name, kind, source, digest)
    previous = app.collection.get_by_name('smoke_illustrator_geometry')
    project = sandbox / 'svg-illustrator-smoke.FlatPrj'
    app.f_handlers.save_project(str(project), silent=True)
    assert project.is_file() and project.stat().st_size > 0
    _reopen(app, qapp, project, previous, errors, pump_until)
    for name, kind in names.items():
        assert reports[name] == _check(app, qapp, name, kind, source, digest)
    assert fixture.read_bytes() == original
    app.ui.showMaximized()
    app.on_zoom_fit()
    qapp.processEvents()
    screenshot = root / '.venv/svg-illustrator-smoke.png'
    assert app.ui.grab().save(str(screenshot))
    print('SVG_ILLUSTRATOR_AUTHORED_SOURCE_REPORT_ROUNDTRIP_OK', digest, screenshot, flush=True)
    app.collection.delete_all()
    pump_until(qapp, lambda: not app.collection.get_names() and app.workers._pending_count == 0,
               errors, 'Illustrator fixture cleanup')
    app.should_we_save = False
