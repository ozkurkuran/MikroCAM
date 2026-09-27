"""Actual four-role local drop, sequenced worker import and source/report project journey."""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path


def _sources(sandbox):
    header = b"G04 authored Latin1 \xff*%FSLAX24Y24*%%MOMM*%%ADD10C,1*%D10*"
    rows = (
        (
            "F.Cu",
            "gerber",
            "wizard-F_Cu.gbr",
            b"%TF.FileFunction,Copper,L1,Top*%" + header + b"X100000Y200000D03*M02*",
            (9.5, 19.5, 10.5, 20.5),
        ),
        (
            "B.Cu",
            "gerber",
            "wizard-B_Cu.gbr",
            b"%TF.FileFunction,Copper,L2,Bot*%" + header + b"X300000Y200000D03*M02*",
            (29.5, 19.5, 30.5, 20.5),
        ),
        (
            "PTH",
            "excellon",
            "wizard-PTH.drl",
            b"M48\r\n; authored Latin1 \xff\r\nMETRIC,TZ\r\nT1C1.0\r\n%\r\nT1\r\nX20.0Y10.0\r\nM30\r\n",
            (19.5, 9.5, 20.5, 10.5),
        ),
        (
            "Edge.Cuts",
            "gerber",
            "wizard-Edge_Cuts.gbr",
            b"%TF.FileFunction,Profile,P*%"
            + header
            + b"G36*X0Y0D02*X400000Y0D01*X400000Y300000D01*X0Y300000D01*X0Y0D01*G37*M02*",
            (0.0, 0.0, 40.0, 30.0),
        ),
    )
    result = []
    for role, kind, filename, data, bounds in rows:
        path = sandbox / filename
        path.write_bytes(data)
        result.append((role, kind, path, data, bounds))
    return tuple(result)


def _check(app, qapp, row, name, defaults):
    from shapely import union_all
    from mikrocam.bridge.manufacturing_import import read_manufacturing_report

    role, kind, _path, data, bounds = row
    owner = app.collection.get_by_name(name)
    assert owner is not None and owner.kind == kind
    assert owner.source_file.encode("latin1") == data
    report = read_manufacturing_report(owner)
    assert report.kind == kind and report.role == role and report.parsed_units == "MM"
    assert (
        report.units_origin == "explicit"
        and report.inspection.source_sha256 == sha256(data).hexdigest()
    )
    factor = 1 if owner.units == "MM" else 25.4
    material = union_all(owner.solid_geometry)
    assert material.is_valid and not material.is_empty
    assert all(
        abs(actual * factor - expected) < 1e-6
        for actual, expected in zip(material.bounds, bounds)
    )
    for key in ("tools_mill_feedrate", "tools_drill_feedrate_z"):
        assert owner.obj_options[key] == defaults[key]
    app.collection.set_active(name)
    app.ui.notebook.setCurrentWidget(app.ui.properties_tab)
    owner.build_ui()
    qapp.processEvents()
    section = owner.ui.mikrocam_manufacturing_report
    assert not section.isHidden()
    section.toggle.setChecked(True)
    qapp.processEvents()
    assert report.inspection.source_sha256 in section.details.toPlainText()
    assert role in section.details.toPlainText()
    return owner, deepcopy(owner.manufacturing_source)


def _reopen(app, qapp, project, previous, first_name, errors, pump_until):
    from PyQt6 import QtCore, QtWidgets

    accepted = []

    def accept_settings():
        for dialog in qapp.topLevelWidgets():
            if not isinstance(dialog, QtWidgets.QMessageBox) or not dialog.isVisible():
                continue
            if dialog.windowTitle() != "Import Settings":
                errors.append(
                    RuntimeError(
                        f"Unexpected manufacturing reopen dialog: {dialog.windowTitle()}"
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
                app.collection.get_by_name(first_name) is not None
                and app.collection.get_by_name(first_name) is not previous
                and app.workers._pending_count == 0
            ),
            errors,
            "Manufacturing project reopen",
        )
    finally:
        timer.stop()
    assert accepted == ["Import Settings"]


def _drop(dialog, rows):
    from PyQt6 import QtCore, QtGui

    mime = QtCore.QMimeData()
    mime.setUrls([QtCore.QUrl.fromLocalFile(str(row[2])) for row in rows])
    event = QtGui.QDropEvent(
        QtCore.QPointF(10, 10),
        QtCore.Qt.DropAction.CopyAction,
        mime,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    dialog.dropEvent(event)
    assert event.isAccepted() and len(dialog._paths) == 4 and dialog.files == ()


def manufacturing_import_journey(app, qapp, sandbox, errors, pump_until, root):
    from mikrocam.ui.manufacturing_import import ManufacturingImportDialog

    assert not app.collection.get_names()
    keys = ("units", "tools_mill_feedrate", "tools_drill_feedrate_z")
    defaults = {key: deepcopy(app.options[key]) for key in keys}
    rows = _sources(sandbox)
    names = tuple("smoke_manufacturing_" + row[0].replace(".", "_") for row in rows)
    dialog = ManufacturingImportDialog(app)
    _drop(dialog, rows)
    dialog.inspect_files()
    assert len(dialog.files) == 4 and all(not file.error for file in dialog.files), (
        dialog.status_label.text()
    )
    for index, (row, name) in enumerate(zip(rows, names)):
        assert dialog.files[index].inspection.role_hint == row[0]
        assert dialog.table.cellWidget(index, 2).currentText() == row[1]
        dialog.table.item(index, 5).setText(name)
    dialog.review_selected()
    assert dialog.review is not None and dialog.import_button.isEnabled(), (
        dialog.status_label.text()
    )
    dialog.show()
    qapp.processEvents()
    dialog.import_selected()
    assert dialog.busy
    pump_until(
        qapp,
        lambda: not dialog.busy and app.workers._pending_count == 0,
        errors,
        "Manufacturing four-role worker import",
    )
    assert dialog.imported_indices == {0, 1, 2, 3}, dialog.status_label.text()
    assert len(app.collection.get_names()) == 4
    assert all("Imported:" in dialog.table.item(index, 6).text() for index in range(4))
    screenshot = Path(root) / ".venv/manufacturing-import-smoke.png"
    qapp.processEvents()
    assert dialog.grab().save(str(screenshot))
    dialog.reject()
    dialog.deleteLater()
    reports = []
    for row, name in zip(rows, names):
        owner, report = _check(app, qapp, row, name, defaults)
        reports.append(report)
        assert row[2].read_bytes() == row[3]
    previous = app.collection.get_by_name(names[0])
    project = sandbox / "manufacturing-import.FlatPrj"
    app.f_handlers.save_project(str(project), silent=True)
    assert project.is_file() and project.stat().st_size > 0
    for row in rows:
        row[2].unlink()
    _reopen(app, qapp, project, previous, names[0], errors, pump_until)
    for row, name, report in zip(rows, names, reports):
        assert _check(app, qapp, row, name, defaults)[1] == report
    assert {key: app.options[key] for key in keys} == defaults
    print(
        "MANUFACTURING_DROP_FOUR_ROLES_LATIN1_REPORT_PROJECT_OK",
        names,
        screenshot,
        flush=True,
    )
    app.collection.delete_all()
    pump_until(
        qapp,
        lambda: not app.collection.get_names() and app.workers._pending_count == 0,
        errors,
        "Manufacturing owned object cleanup",
    )
    app.should_we_save = False
