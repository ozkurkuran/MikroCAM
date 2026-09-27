"""Actual desktop fixed selected Excellons, duplicate slots and guarded persistence."""
from copy import deepcopy
from pathlib import Path


def _snapshot(owner):
    from shapely import to_wkb
    tools = deepcopy(owner.tools)
    for tool in tools.values():
        # Project JSON changes slot tuples to lists; compare the complete operation data.
        tool['slots'] = [tuple(pair) for pair in tool.get('slots', ())]
    return (owner.units, deepcopy(dict(owner.obj_options)), tools,
            tuple(to_wkb(value) for value in owner.solid_geometry), owner.source_file)


def _sources(app, sandbox, qapp, errors, pump_until):
    texts = ('M48\nMETRIC,LZ\nT01C1.0\nT02C1.0\n%\nT01\nX10.0Y10.0\nT02\nX10.0Y20.0G85X20.0Y20.0\nM30\n',
             'M48\nMETRIC,LZ\nT01C1.0\nT02C1.0\nT03C1.2\n%\nT01\nX10.0Y10.0\nT02\nX20.0Y20.0G85X10.0Y20.0\nT03\nX30.0Y10.0\nM30\n')
    owners = []
    for index, text in enumerate(texts):
        path = sandbox / f'merge-source-{index}.drl'
        path.write_bytes(text.encode('utf-8'))
        name = f'smoke_merge_source_{index}'
        app.f_handlers.open_excellon(str(path), outname=name)
        pump_until(qapp, lambda: app.collection.get_by_name(name) is not None
                   and app.workers._pending_count == 0, errors, 'Excellon merge source import')
        owner = app.collection.get_by_name(name)
        for tool in owner.tools.values():
            tool['data']['tools_drill_feedrate'] = 41.25 + index
        owners.append(owner)
    return tuple(owners)


def _check(app, name, tolerance=1e-6):
    owner = app.collection.get_by_name(name)
    assert owner is not None and owner.kind == 'excellon'
    factor = 1 if owner.units == 'MM' else 25.4
    tools = sorted(owner.tools.values(), key=lambda tool: tool['tooldia'])
    assert len(tools) == 2
    for tool, diameter, center in zip(tools, (1, 1.2), ((10, 10), (30, 10))):
        assert abs(tool['tooldia'] * factor - diameter) < tolerance
        assert len(tool['drills']) == 1
        point = tool['drills'][0]
        assert abs(point.x * factor - center[0]) < tolerance and abs(point.y * factor - center[1]) < tolerance
    assert len(tools[0]['slots']) == 1 and not tools[1]['slots']
    for point, center in zip(tools[0]['slots'][0], ((10, 20), (20, 20))):
        assert abs(point.x * factor - center[0]) < tolerance and abs(point.y * factor - center[1]) < tolerance
    assert owner.solid_geometry and owner.source_file and 'M48' in owner.source_file
    return owner


def _reopen(app, qapp, project, previous, errors, pump_until):
    from PyQt6 import QtCore, QtWidgets
    accepted = []
    def accept_settings():
        for dialog in qapp.topLevelWidgets():
            if not isinstance(dialog, QtWidgets.QMessageBox) or not dialog.isVisible():
                continue
            if dialog.windowTitle() != 'Import Settings':
                errors.append(RuntimeError(f'Unexpected merge reopen dialog: {dialog.windowTitle()}'))
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
        pump_until(qapp, lambda: app.collection.get_by_name('smoke_excellon_merge') is not None
                   and app.collection.get_by_name('smoke_excellon_merge') is not previous
                   and app.workers._pending_count == 0, errors, 'Excellon merge project reopen')
    finally:
        timer.stop()
    assert accepted == ['Import Settings']


def excellon_merge_journey(app, qapp, sandbox, errors, pump_until, root):
    from PyQt6 import QtWidgets
    from mikrocam.ui.excellon_merge import ExcellonMergeDialog
    from mikrocam.bridge.excellon_merge import load_excellon_merge
    assert not app.collection.get_names()
    default_keys = ('units', 'tools_drill_feedrate', 'tools_drill_cutz')
    defaults = {key: deepcopy(app.options[key]) for key in default_keys}
    owners = _sources(app, sandbox, qapp, errors, pump_until)
    app.collection.view.selectionModel().clearSelection()
    for owner in owners:
        app.collection.set_active(owner.obj_options['name'])
    selected = tuple(app.collection.get_selected())
    assert selected == owners
    original = tuple(_snapshot(owner) for owner in owners)
    dialog = ExcellonMergeDialog(app, selected)
    assert dialog.review is None and not dialog.create_button.isEnabled()
    dialog.analyse()
    review = dialog.review
    assert review is not None and not review.conflict_count, dialog.status_label.text()
    assert len(review.duplicates) == 2 and len(review.tool_map) == 5
    dialog.name_edit.setText('smoke_excellon_merge')
    assert dialog.create_button.isEnabled()
    dialog.show()
    qapp.processEvents()
    screenshot = Path(root) / '.venv/excellon-merge-smoke.png'
    assert dialog.grab().save(str(screenshot))
    dialog.create_selected()
    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted, dialog.status_label.text()
    dialog.deleteLater()
    pump_until(qapp, lambda: app.collection.get_by_name('smoke_excellon_merge') is not None
               and app.workers._pending_count == 0, errors, 'Reviewed Excellon merge creation')
    previous = _check(app, 'smoke_excellon_merge')
    assert all(tool['data']['tools_drill_feedrate'] == defaults['tools_drill_feedrate']
               for tool in previous.tools.values())
    assert tuple(_snapshot(owner) for owner in owners) == original
    assert load_excellon_merge(owners) == review
    exported = sandbox / 'excellon-merge.drl'
    assert app.f_handlers.export_excellon('smoke_excellon_merge', str(exported), use_thread=False) != 'fail'
    app.f_handlers.open_excellon(str(exported), outname='smoke_merge_reparsed')
    pump_until(qapp, lambda: app.collection.get_by_name('smoke_merge_reparsed') is not None
               and app.workers._pending_count == 0, errors, 'Merged drill-slot export reparse')
    unit_mm = 25.4 if app.options['excellon_exp_units'] == 'INCH' else 1
    tool_decimals = 4 if unit_mm == 25.4 else 2
    tolerance = max(10 ** -app.options['excellon_exp_decimals'], 10 ** -tool_decimals) * unit_mm + .0001
    _check(app, 'smoke_merge_reparsed', tolerance)
    project = sandbox / 'excellon-merge.FlatPrj'
    app.f_handlers.save_project(str(project), silent=True)
    assert project.is_file() and project.stat().st_size > 0
    _reopen(app, qapp, project, previous, errors, pump_until)
    _check(app, 'smoke_excellon_merge')
    _check(app, 'smoke_merge_reparsed', tolerance)
    restored = tuple(app.collection.get_by_name(f'smoke_merge_source_{index}') for index in range(2))
    assert tuple(_snapshot(owner) for owner in restored) == original
    assert load_excellon_merge(restored) == review
    assert {key: app.options[key] for key in default_keys} == defaults
    print('EXCELLON_MERGE_SELECTED_DRILL_SLOT_ROUNDTRIP_OK', len(review.duplicates), screenshot, flush=True)
    app.collection.delete_all()
    pump_until(qapp, lambda: not app.collection.get_names() and app.workers._pending_count == 0,
               errors, 'Excellon merge owned object cleanup')
    app.should_we_save = False
