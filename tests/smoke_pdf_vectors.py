"""Authored two-page PDF selection, physical crop/flip and host persistence journey."""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import io


def _source(sandbox):
    from reportlab.pdfgen.canvas import Canvas

    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=(288, 144), pageCompression=1, invariant=1)
    canvas.rect(1, 1, 4, 4, stroke=0, fill=1)
    canvas.showPage()
    canvas.rect(72, 36, 72, 36, stroke=0, fill=1)
    canvas.showPage()
    canvas.save()
    data = stream.getvalue()
    path = sandbox / "pdf-vector-authored.pdf"
    path.write_bytes(data)
    return path, data


def _check(app, qapp, data, defaults):
    from shapely import union_all
    from mikrocam.bridge.pdf_import import read_pdf_report

    owner = app.collection.get_by_name("smoke_pdf_vectors")
    assert owner is not None and owner.kind == "geometry"
    assert owner.source_file.encode("latin1") == data
    report = read_pdf_report(owner)
    assert report.source_sha256 == sha256(data).hexdigest()
    assert report.page.index == 1 and report.page_count == 2
    assert report.options.crop_mm == (12.7, 0.0, 76.2, 50.8) and report.options.flip
    factor = 1 if owner.units == "MM" else 25.4
    material = union_all(owner.solid_geometry)
    assert all(
        abs(actual * factor - expected) < 1e-6
        for actual, expected in zip(material.bounds, (12.7, 25.4, 38.1, 38.1))
    )
    assert abs(material.area * factor**2 - 322.58) < 1e-6
    for key in ("tools_mill_feedrate", "tools_mill_cutz"):
        assert owner.obj_options[key] == defaults[key]
        assert all(tool["data"][key] == defaults[key] for tool in owner.tools.values())
    app.collection.set_active("smoke_pdf_vectors")
    app.ui.notebook.setCurrentWidget(app.ui.properties_tab)
    owner.build_ui()
    qapp.processEvents()
    section = owner.ui.mikrocam_pdf_report
    assert not section.isHidden()
    section.toggle.setChecked(True)
    qapp.processEvents()
    assert report.source_sha256 in section.details.toPlainText()
    return owner, deepcopy(owner.pdf_import)


def _reopen(app, qapp, project, previous, errors, pump_until):
    from PyQt6 import QtCore, QtWidgets

    accepted = []

    def accept_settings():
        for dialog in qapp.topLevelWidgets():
            if not isinstance(dialog, QtWidgets.QMessageBox) or not dialog.isVisible():
                continue
            if dialog.windowTitle() != "Import Settings":
                errors.append(
                    RuntimeError(
                        f"Unexpected PDF reopen dialog: {dialog.windowTitle()}"
                    )
                )
                dialog.reject()
                continue
            for button in dialog.buttons():
                if (
                    dialog.buttonRole(button)
                    == QtWidgets.QMessageBox.ButtonRole.YesRole
                ):
                    accepted.append(dialog.windowTitle())
                    button.click()
                    break

    app.should_we_save = False
    timer = QtCore.QTimer()
    timer.timeout.connect(accept_settings)
    timer.start(50)
    try:
        app.f_handlers.open_project(str(project), plot=True)
        pump_until(
            qapp,
            lambda: (
                app.collection.get_by_name("smoke_pdf_vectors") is not None
                and app.collection.get_by_name("smoke_pdf_vectors") is not previous
                and app.workers._pending_count == 0
            ),
            errors,
            "PDF Geometry project reopen",
        )
    finally:
        timer.stop()
    assert accepted == ["Import Settings"]


def _export_reparse(app, qapp, sandbox, errors, pump_until):
    from shapely import union_all

    exported = sandbox / "pdf-vector-export.dxf"
    assert (
        app.f_handlers.export_dxf("smoke_pdf_vectors", str(exported), use_thread=False)
        != "fail"
    )
    assert exported.is_file()
    assert (
        app.f_handlers.import_dxf(
            str(exported), outname="smoke_pdf_dxf_reparsed", geo_type="geometry"
        )
        != "fail"
    )
    pump_until(
        qapp,
        lambda: (
            app.collection.get_by_name("smoke_pdf_dxf_reparsed") is not None
            and app.workers._pending_count == 0
        ),
        errors,
        "PDF Geometry DXF export reparse",
    )
    owner = app.collection.get_by_name("smoke_pdf_dxf_reparsed")
    factor = 1 if owner.units == "MM" else 25.4
    contours = union_all(owner.solid_geometry)
    assert all(
        abs(actual * factor - expected) < 1e-6
        for actual, expected in zip(contours.bounds, (12.7, 25.4, 38.1, 38.1))
    )
    assert abs(contours.length * factor - 76.2) < 1e-6


def pdf_vector_journey(app, qapp, sandbox, errors, pump_until, root):
    from PyQt6 import QtWidgets
    from mikrocam.ui.pdf_import import PdfImportDialog

    assert not app.collection.get_names()
    keys = ("units", "tools_mill_feedrate", "tools_mill_cutz")
    defaults = {key: deepcopy(app.options[key]) for key in keys}
    path, data = _source(sandbox)
    dialog = PdfImportDialog(app)
    dialog.path_edit.setText(str(path))
    dialog.inspect_document()
    assert dialog.document is not None and dialog.page_combo.count() == 2, (
        dialog.status_label.text()
    )
    dialog.page_combo.setCurrentIndex(1)
    dialog.crop_check.setChecked(True)
    for name, value in (
        ("xmin", "12.7"),
        ("ymin", "0"),
        ("xmax", "76.2"),
        ("ymax", "50.8"),
    ):
        getattr(dialog, name + "_edit").setText(value)
    dialog.flip_check.setChecked(True)
    dialog.analyse()
    assert dialog.review is not None, dialog.status_label.text()
    assert not dialog.create_button.isEnabled()
    dialog.name_edit.setText("smoke_pdf_vectors")
    assert dialog.create_button.isEnabled()
    dialog.show()
    qapp.processEvents()
    screenshot = Path(root) / ".venv/pdf-vector-smoke.png"
    assert dialog.grab().save(str(screenshot))
    dialog.create_selected()
    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted, (
        dialog.status_label.text()
    )
    dialog.deleteLater()
    pump_until(
        qapp,
        lambda: (
            app.collection.get_by_name("smoke_pdf_vectors") is not None
            and app.workers._pending_count == 0
        ),
        errors,
        "PDF reviewed Geometry creation",
    )
    previous, report = _check(app, qapp, data, defaults)
    _export_reparse(app, qapp, sandbox, errors, pump_until)
    project = sandbox / "pdf-vector.FlatPrj"
    app.f_handlers.save_project(str(project), silent=True)
    assert (
        project.is_file() and project.stat().st_size > 0 and path.read_bytes() == data
    )
    path.unlink()
    _reopen(app, qapp, project, previous, errors, pump_until)
    _, restored_report = _check(app, qapp, data, defaults)
    assert (
        restored_report == report
        and {key: app.options[key] for key in keys} == defaults
    )
    print(
        "PDF_VECTOR_SELECTED_PAGE_CROP_FLIP_DXF_PROJECT_OK",
        sha256(data).hexdigest(),
        screenshot,
        flush=True,
    )
    app.collection.delete_all()
    pump_until(
        qapp,
        lambda: not app.collection.get_names() and app.workers._pending_count == 0,
        errors,
        "PDF vector owned object cleanup",
    )
    app.should_we_save = False
