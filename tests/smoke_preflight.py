"""Actual desktop preflight journey; only generated/sandboxed source is analyzed."""
from pathlib import Path


def preflight_journey(app, qapp, sandbox, errors, pump_until, root):
    from PyQt6 import QtCore
    from mikrocam.core.gcode_preflight import analyze_gcode
    geometry = app.collection.get_by_name('smoke_iso')
    geometry.generatecncjob(outname='smoke_grbl', dia=.2, z_cut=-.1, z_move=2., feedrate=120,
                            pp='GRBL_11_no_M6', use_thread=False)
    pump_until(qapp, lambda: app.collection.get_by_name('smoke_grbl') is not None
               and app.workers._pending_count == 0, errors, 'GRBL preflight source')
    cnc = app.collection.get_by_name('smoke_grbl')
    app.collection.set_active('smoke_grbl')
    app._mikrocam_laser_cam_panel.hide()
    app._mikrocam_machine_panel.hide()
    action = next(action for action in app.ui.menu_plugins.actions() if action.text() == 'G-code preflight')
    action.trigger()
    panel = app._mikrocam_preflight_panel
    for key, field in panel.setup_widget.fields.items():
        if not key.startswith('rapid_'):
            field.setText('0')
    values = {'initial_z':'2', 'safe_z':'2', 'min_x':'-100', 'min_y':'-100', 'min_z':'-10',
              'max_x':'300', 'max_y':'300', 'max_z':'100', 'rapid_x':'600',
              'rapid_y':'600', 'rapid_z':'120'}
    for key,value in values.items():
        panel.setup_widget.fields[key].setText(value)
    assert cnc.source_file
    before = cnc.source_file, cnc.gcode
    panel.use_selected()
    assert panel.source is not None, panel.result_label.text()
    direct = analyze_gcode(panel.source, panel.setup_widget.value())
    panel.analyze_button.click()
    pump_until(qapp, lambda: not panel.busy and panel.report is not None, errors, 'selected-job preflight')
    assert panel.report == direct and panel.report.allowed, panel.report.findings
    assert before == (cnc.source_file, cnc.gcode), 'Preflight modified CNC source'
    selected_report = panel.report
    target = Path(sandbox) / 'preflight.nc'
    target.write_text(cnc.source_file, encoding='utf-8')
    original_bytes = target.read_bytes()
    panel.load_file(target)
    panel.analyze_button.click()
    pump_until(qapp, lambda: not panel.busy and panel.report is not None, errors, 'file preflight')
    assert panel.report.allowed and panel.report.bounds_mm == selected_report.bounds_mm
    assert target.read_bytes() == original_bytes
    screenshot = Path(root) / '.venv/preflight-smoke.png'
    qapp.processEvents()
    assert app.ui.grab().save(str(screenshot))
    print('PREFLIGHT_SELECTED_FILE_OK', panel.report.executable_blocks, screenshot, flush=True)
    target.write_text('G21 G90 G17 G94\nG0 X1 Z-1\n', encoding='ascii')
    panel.load_file(target)
    panel.analyze_button.click()
    pump_until(qapp, lambda: not panel.busy and panel.report is not None, errors, 'blocked preflight')
    assert not panel.report.allowed and any(item.code == 'unsafe-rapid' for item in panel.report.findings)
    print('PREFLIGHT_HAZARD_OK', flush=True)
    panel.load_file(target)
    panel.analyze_button.click()  # Leave owned analysis for application shutdown to cancel/join.
    assert panel.busy
