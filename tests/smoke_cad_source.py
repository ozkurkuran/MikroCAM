"""Authored producer declarations exercise desktop persistence, not vendor coverage."""
from copy import deepcopy
from hashlib import sha256
import io
from pathlib import Path


def _sources(sandbox):
    import ezdxf
    svg = ('<svg width="10mm" height="20mm" viewBox="0 0 10 20">\r\n'
           '<!-- Generator: Adobe Illustrator 29.0 -->\r\n'
           '<rect x="2" y="3" width="4" height="2"/>\r\n</svg>\r\n')
    document = ezdxf.new('R2010')
    document.units = 4
    document.modelspace().add_lwpolyline([(2, 3), (6, 3), (6, 5), (2, 5)], close=True)
    output = io.StringIO()
    document.write(output)
    dxf = output.getvalue().replace('\n', '\r\n')
    dxf = dxf.replace('  0\r\nEOF', '999\r\nGenerator: Proteus 8.6\r\n  0\r\nEOF')
    records = {}
    for source_format, text in (('SVG', svg), ('DXF', dxf)):
        data = b'\xef\xbb\xbf' + text.encode('utf-8')
        path = sandbox / ('cad-source-authored.' + source_format.lower())
        path.write_bytes(data)
        records[source_format] = (path, data.decode('utf-8'), sha256(data).hexdigest())
    return records


def _check(app, qapp, name, kind, source_format, text, digest):
    from shapely import union_all
    from mikrocam.bridge.cad_source import read_cad_source
    from mikrocam.bridge.import_report import read_import_report
    obj = app.collection.get_by_name(name)
    assert obj is not None and obj.kind == kind
    assert obj.source_file == text
    record = read_cad_source(obj)
    expected_application = 'Illustrator' if source_format == 'SVG' else 'Proteus'
    assert record.application == expected_application and record.status == 'identified'
    assert record.source_format == source_format and record.source_sha256 == digest
    material = union_all(obj.solid_geometry)
    factor = 1 if obj.units.upper() == 'MM' else 25.4
    bounds = (2, 15, 6, 17) if source_format == 'SVG' else (2, 3, 6, 5)
    assert all(abs(actual * factor - wanted) < 1e-6 for actual, wanted in zip(material.bounds, bounds))
    assert material.is_valid
    if source_format == 'SVG':
        assert abs(material.area * factor ** 2 - 8) < 1e-6
        assert read_import_report(obj).source_sha256 == digest
    else:
        assert abs(material.length * factor - 12) < 1e-6
        assert read_import_report(obj) is None
    app.collection.set_active(name)
    app.ui.notebook.setCurrentWidget(app.ui.properties_tab)
    obj.build_ui()
    qapp.processEvents()
    section = obj.ui.mikrocam_cad_source
    assert not section.isHidden()
    section.toggle.setChecked(True)
    qapp.processEvents()
    app.ui.properties_scroll_area.ensureWidgetVisible(section, 0, 10)
    qapp.processEvents()
    details = section.details.toPlainText()
    assert digest in details and expected_application in details
    return deepcopy(obj.cad_source)


def _reopen(app, qapp, project, previous, errors, pump_until):
    from PyQt6 import QtCore, QtWidgets
    accepted = []

    def accept_settings():
        for dialog in qapp.topLevelWidgets():
            if not isinstance(dialog, QtWidgets.QMessageBox) or not dialog.isVisible():
                continue
            if dialog.windowTitle() != 'Import Settings':
                errors.append(RuntimeError(f'Unexpected CAD source reopen dialog: {dialog.windowTitle()}'))
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
        pump_until(qapp, lambda: app.collection.get_by_name('smoke_cad_svg_geometry') is not None
                   and app.collection.get_by_name('smoke_cad_svg_geometry') is not previous
                   and app.workers._pending_count == 0, errors, 'CAD source project reopen')
    finally:
        timer.stop()
    assert accepted == ['Import Settings']


def cad_source_journey(app, qapp, sandbox, errors, pump_until, root):
    assert not app.collection.get_names(), 'CAD source journey requires an empty collection'
    sources = _sources(sandbox)
    tracked_defaults = ('tools_mill_feedrate', 'tools_mill_cutz', 'units')
    defaults = {key: deepcopy(app.options[key]) for key in tracked_defaults}
    records = {}
    for source_format, (path, text, digest) in sources.items():
        method = app.f_handlers.import_svg if source_format == 'SVG' else app.f_handlers.import_dxf
        for kind in ('geometry', 'gerber'):
            name = f'smoke_cad_{source_format.lower()}_{kind}'
            assert method(str(path), geo_type=kind, outname=name, plot=True) != 'fail'
            pump_until(qapp, lambda: app.collection.get_by_name(name) is not None
                       and app.workers._pending_count == 0, errors, f'CAD source {source_format}/{kind} import')
            records[name] = _check(app, qapp, name, kind, source_format, text, digest)
            obj = app.collection.get_by_name(name)
            assert obj.obj_options['tools_mill_feedrate'] == defaults['tools_mill_feedrate']
            assert obj.obj_options['tools_mill_cutz'] == defaults['tools_mill_cutz']
    assert {key: app.options[key] for key in tracked_defaults} == defaults
    previous = app.collection.get_by_name('smoke_cad_svg_geometry')
    project = sandbox / 'cad-source-smoke.FlatPrj'
    app.f_handlers.save_project(str(project), silent=True)
    assert project.is_file() and project.stat().st_size > 0
    for path, _, _ in sources.values():
        path.unlink()
    _reopen(app, qapp, project, previous, errors, pump_until)
    for source_format, (_, text, digest) in sources.items():
        for kind in ('geometry', 'gerber'):
            name = f'smoke_cad_{source_format.lower()}_{kind}'
            assert _check(app, qapp, name, kind, source_format, text, digest) == records[name]
    app.ui.showMaximized()
    app.on_zoom_fit()
    qapp.processEvents()
    screenshot = Path(root) / '.venv/cad-source-smoke.png'
    assert app.ui.grab().save(str(screenshot))
    print('CAD_SOURCE_AUTHORED_SVG_DXF_GEOMETRY_GERBER_ROUNDTRIP_OK', len(records), screenshot, flush=True)
    app.collection.delete_all()
    pump_until(qapp, lambda: not app.collection.get_names() and app.workers._pending_count == 0,
               errors, 'CAD source owned object cleanup')
    app.should_we_save = False
