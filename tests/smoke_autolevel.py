"""Actual desktop mapped arc compensation and current Fake handoff; never hardware."""
from pathlib import Path


def autolevel_journey(app,qapp,errors,pump_until,root):
    from mikrocam.core.gcode_models import SourceSnapshot
    from mikrocam.core.probe_map import ProbeMap,uniform_grid
    from mikrocam.bridge.probe_files import save_probe_map
    from mikrocam.machine.job_models import JobPhase
    from smoke_job import _connect_fake
    preflight,machine=app._mikrocam_preflight_panel,app._mikrocam_machine_panel
    fake=_connect_fake(machine,qapp,errors,pump_until)
    preflight.cancel()
    pump_until(qapp,lambda:not preflight.busy,errors,'auto-level prior review join')
    text='G21G90G17G94\nM3S500\nG1Z-.1F60\nG2X2Y0I1J0\nG1X2Y2\nG0Z5\nM5M30\n'
    source=SourceSnapshot('autolevel-arc-smoke.nc',text)
    input_path=Path(root)/'.venv/autolevel-original-smoke.nc'
    input_path.write_text(text,encoding='ascii')
    input_bytes=input_path.read_bytes()
    preflight.load_file(input_path)
    source=preflight.source
    for field in preflight.setup_widget.fields.values():field.setText('0')
    values=dict(initial_z='5',safe_z='5',min_x='-10',min_y='-10',min_z='-10',
                max_x='10',max_y='10',max_z='10',rapid_x='600',rapid_y='600',rapid_z='600')
    for key,value in values.items():preflight.setup_widget.fields[key].setText(value)
    preflight.analyze_button.click()
    pump_until(qapp,lambda:not preflight.busy and preflight.report is not None,errors,'auto-level original review')
    assert preflight.report.allowed,preflight.report.findings
    grid=uniform_grid(0.,2.,3,0.,2.,3)
    heightmap=ProbeMap(grid,tuple(.01*x+.02*y for x,y in grid.points),(0.,0.,0.),'complete','simulated')
    path=Path(root)/'.venv/autolevel-map-smoke.json'
    save_probe_map(path,heightmap)
    before=tuple(fake.writes)
    preflight.autolevel_button.click();panel=preflight._autolevel_panel
    assert panel is not None and panel.isVisible()
    panel.load_map(path)
    for key,value in dict(reference_z_mm='0',max_segment_mm='1',chord_error_mm='.02',surface_error_mm='.001').items():
        panel.fields[key].setText(value)
    panel.prepare_button.click()
    pump_until(qapp,lambda:not panel.busy and panel.result is not None,errors,'auto-level mapped arc preparation')
    result=panel.result
    assert preflight.source is source and source.text==input_bytes.decode('ascii')
    assert result.prepared_job.report.allowed and result.prepared_job.report.arc_count==0
    # Only periodic status/setup queries occur; offline preparation emits no job or probe moves.
    assert not fake.job_writes and not any(b'G38.2' in data for data in fake.writes[len(before):])
    assert not panel.save_button.isEnabled() and not panel.transfer_button.isEnabled()
    panel.confirm_checkbox.setChecked(True)
    output=Path(root)/'.venv/autolevel-smoke.nc';panel.save_path(output)
    assert output.read_text(encoding='ascii')==result.prepared_job.source.text
    panel.transfer_button.click()
    pump_until(qapp,lambda:machine.job_controls.prepared_job is not None and machine._prepare_worker is None,
               errors,'auto-level reviewed Machine transfer')
    assert machine.job_controls.prepared_job.source==result.prepared_job.source
    machine.job_controls.confirm_checkbox.setChecked(True)
    pump_until(qapp,lambda:machine.job_controls.start_button.isEnabled(),errors,'auto-level explicit Start')
    machine.job_controls.start_button.click()
    pump_until(qapp,lambda:machine.last_snapshot.job.phase is JobPhase.COMPLETE,
               errors,'auto-level Fake completion',timeout=25)
    assert fake.machine_position==(2.,2.,5.)
    assert fake.job_writes==[block.wire for block in result.prepared_job.blocks]
    panel.setFloating(True);panel.resize(1100,850);panel.show();qapp.processEvents()
    screenshot=Path(root)/'.venv/autolevel-smoke.png'
    assert panel.grab().save(str(screenshot))
    print('AUTOLEVEL_MAP_ARC_SAVE_FAKE_COMPLETE_OK',len(fake.job_writes),screenshot,flush=True)
    map_bytes=path.read_bytes()
    panel.save_path(input_path);assert input_path.read_bytes()==input_bytes
    panel.save_path(path);assert path.read_bytes()==map_bytes
    print('AUTOLEVEL_INPUT_FILES_PROTECTED_OK',flush=True)
    panel.fields['reference_z_mm'].setText('.01')
    assert panel.result is None and panel.reviewed_binding() is None
    assert not panel.save_button.isEnabled() and not panel.transfer_button.isEnabled()
    print('AUTOLEVEL_CHANGED_INPUT_INVALIDATED_OK',flush=True)
    assert panel.close()
    machine.disconnect_machine()
    pump_until(qapp,lambda:not machine.busy,errors,'auto-level worker disconnect join')
