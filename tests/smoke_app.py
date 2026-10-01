"""Desktop CAM and normal shutdown smoke, adapted from the 8.994 reference.

Run with the checkout's Python: .venv/Scripts/python.exe tests/smoke_app.py
Requires a real desktop/OpenGL context; never connects to manufacturing hardware.
"""
import multiprocessing
import json
import lzma
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import traceback
import uuid


ROOT = Path(__file__).resolve().parents[1]


def pump_until(qapp, predicate, errors, stage, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        assert not errors, f'Asynchronous exception during {stage}'
        if predicate():
            return
        time.sleep(0.02)
    raise TimeoutError(f'Timed out during {stage}')


def assert_object(app, name, kind):
    obj = app.collection.get_by_name(name)
    assert obj is not None, f'Missing {name}'
    assert obj.kind == kind, (name, obj.kind)
    assert obj.obj_options['name'] == name
    if kind == 'cncjob':
        assert obj.gcode_parsed, f'Empty toolpath for {name}'
        assert any(not path['geom'].is_empty for path in obj.gcode_parsed)
    else:
        assert obj.solid_geometry, f'Empty geometry for {name}'
    return obj


def assert_product_title(app):
    from mikrocam.core.identity import NAME, VERSION
    title = app.ui.windowTitle()
    assert NAME in title and VERSION in title, title
    assert app.version == 'Unstable', 'Branding changed the host compatibility version'


def inspect_about(app, qapp, errors):
    from PyQt6 import QtCore, QtWidgets
    from mikrocam.core.identity import NAME, VERSION, REPOSITORY_URL
    checked = []
    def inspect_dialog():
        dialog = qapp.activeModalWidget()
        try:
            assert isinstance(dialog, QtWidgets.QDialog), 'About dialog did not open'
            text = '\n'.join(label.text() for label in dialog.findChildren(QtWidgets.QLabel))
            for expected in (NAME, VERSION, REPOSITORY_URL, 'Juan Pablo Caram', 'Marius Stanciu', 'GPL'):
                assert expected in text, f'Missing About attribution/identity: {expected}'
            screenshot = ROOT / '.venv/about-smoke.png'
            assert dialog.grab().save(str(screenshot)), 'About screenshot could not be saved'
            checked.append(True)
            print('ABOUT_OK', screenshot, flush=True)
        except BaseException as error:
            errors.append(error)
        finally:
            if dialog is not None:
                dialog.reject()
    QtCore.QTimer.singleShot(500, inspect_dialog)
    app.on_about()
    assert checked and not errors, f'About check failed: {errors}'


def cam_journey(app, qapp, sandbox, errors):
    from PyQt6 import QtCore, QtWidgets
    fixtures = ROOT / 'assets/examples/files'
    app.f_handlers.open_gerber(str(fixtures / 'test.gbr'), outname='smoke_gerber')
    app.f_handlers.open_excellon(str(fixtures / 'test.txt'), outname='smoke_drill')
    pump_until(qapp, lambda: len(app.collection.get_names()) == 2, errors, 'file import')
    gerber = assert_object(app, 'smoke_gerber', 'gerber')
    assert_object(app, 'smoke_drill', 'excellon')
    print('GERBER_OK', gerber.bounds(), flush=True)
    print('EXCELLON_OK', flush=True)
    gerber.isolate(dia=0.2, passes=1, combine=True, outname='smoke_iso', plot=True)
    pump_until(qapp, lambda: app.collection.get_by_name('smoke_iso') is not None,
               errors, 'isolation')
    geometry = assert_object(app, 'smoke_iso', 'geometry')
    print('ISOLATE_OK', flush=True)
    geometry.generatecncjob(outname='smoke_cnc', dia=0.2, z_cut=-0.1, z_move=2.0,
                            feedrate=120, use_thread=False)
    pump_until(qapp, lambda: app.collection.get_by_name('smoke_cnc') is not None,
               errors, 'CNC generation')
    cnc = assert_object(app, 'smoke_cnc', 'cncjob')
    assert cnc.gcode and cnc.gcode_parsed
    gcode = cnc.gcode
    print('CNC_OK', len(gcode), flush=True)
    pump_until(qapp, lambda: app.workers._pending_count == 0, errors, 'plot completion')
    expected = {obj.obj_options['name']: obj.kind for obj in app.collection.get_list()}
    assert expected == {'smoke_gerber': 'gerber', 'smoke_drill': 'excellon',
                        'smoke_iso': 'geometry', 'smoke_cnc': 'cncjob'}
    project = sandbox / 'smoke.FlatPrj'
    app.f_handlers.save_project(str(project), silent=True)
    assert project.is_file() and project.stat().st_size > 0
    saved = project.read_bytes()
    if saved.startswith(b'\xfd7zXZ\x00'):
        saved = lzma.decompress(saved)
    assert json.loads(saved)['version'] == app.version == 'Unstable'
    print('PROJECT_SAVE_OK', flush=True)
    app.should_we_save = False
    accepted = []
    def accept_project_settings():
        for dialog in qapp.topLevelWidgets():
            if not isinstance(dialog, QtWidgets.QMessageBox) or not dialog.isVisible():
                continue
            if dialog.windowTitle() != 'Import Settings':
                errors.append(RuntimeError(f'Unexpected dialog: {dialog.windowTitle()}'))
                dialog.reject()
                continue
            for button in dialog.buttons():
                if dialog.buttonRole(button) == QtWidgets.QMessageBox.ButtonRole.YesRole:
                    accepted.append(dialog.windowTitle())
                    button.click()
                    break
    dialog_timer = QtCore.QTimer()
    dialog_timer.timeout.connect(accept_project_settings)
    dialog_timer.start(50)
    app.f_handlers.open_project(str(project), plot=True)
    try:
        pump_until(qapp, lambda: app.collection.get_by_name('smoke_cnc') is not None
                   and app.collection.get_by_name('smoke_cnc') is not cnc
                   and app.workers._pending_count == 0, errors, 'project reopen')
    finally:
        dialog_timer.stop()
    assert accepted == ['Import Settings'], 'Project settings were not confirmed'
    actual = {obj.obj_options['name']: obj.kind for obj in app.collection.get_list()}
    assert actual == expected
    for name, kind in expected.items():
        assert_object(app, name, kind)
    reopened = app.collection.get_by_name('smoke_cnc')
    assert reopened.gcode == gcode and reopened.gcode_parsed
    assert_product_title(app)
    print('PROJECT_ROUNDTRIP_OK', actual, flush=True)


def laser_journey(app, qapp, sandbox, errors):
    from mikrocam.core.laser_job import LaserPass, LaserRecipe
    from mikrocam.core.laser_json import recipe_from_json, recipe_to_json
    from mikrocam.bridge.gerber import gerber_region
    from mikrocam.ui.laser_cam import open_laser_cam
    source = app.collection.get_by_name('smoke_gerber')
    before = gerber_region(source)
    app.collection.set_all_inactive()
    app.collection.set_active('smoke_gerber')
    action = next(action for action in app.ui.menu_plugins.actions() if action.text() == 'Laser CAM')
    action.trigger()
    panel = open_laser_cam(app)
    assert open_laser_cam(app) is panel
    panel.source_combo.setCurrentIndex(panel.source_combo.findData('smoke_gerber'))
    recipe_file = sandbox / 'laser-recipe.json'
    recipe_file.write_text(recipe_to_json(LaserRecipe('Synthetic smoke only',
                           (LaserPass('Reference', 20, 100, 20, 80),
                            LaserPass('Finish', 10, 150, 30, 60)))), encoding='utf-8')
    panel.set_recipe(recipe_from_json(recipe_file.read_text(encoding='utf-8')))
    panel.hatch_enabled.setChecked(True)
    panel.hatch_spacing.setValue(1)
    panel.hatch_angle.setValue(30)
    panel.cross_hatch.setChecked(True)
    panel.interlace_n.setValue(3)
    panel.translation_x.setValue(5)
    panel.generate()
    pump_until(qapp, lambda: not panel.busy, errors, 'laser preview')
    assert panel.last_plan is not None, panel.status_label.text()
    assert panel.last_plan.options.interlace_n == 3
    passes = panel.last_plan.pass_plans
    assert [value.settings.name for value in passes] == ['Reference', 'Finish']
    assert passes[0].paths is passes[1].paths is panel.last_plan.paths
    assert passes[1].settings.speed_mm_s == 150 and passes[1].settings.pulse_width_ns == 60
    first = app._mikrocam_laser_cam_preview
    assert_object(app, first.obj_options['name'], 'geometry')
    pump_until(qapp, lambda: app.workers._pending_count == 0, errors, 'laser preview plotting')
    assert len(first.solid_geometry) == len(panel.last_plan.paths)
    assert gerber_region(source) == before
    assert app.collection.get_active() is source
    panel.generate()
    pump_until(qapp, lambda: not panel.busy, errors, 'laser preview replacement')
    second = app._mikrocam_laser_cam_preview
    assert second is not first and first not in app.collection.get_list()
    assert len(app.collection.get_list()) == 5
    assert panel.last_plan is not None and gerber_region(source) == before
    pump_until(qapp, lambda: app.workers._pending_count == 0, errors, 'laser replacement plotting')
    panel.close()
    assert open_laser_cam(app) is panel
    qapp.processEvents()
    screenshot = ROOT / '.venv/laser-cam-smoke.png'
    assert app.ui.grab().save(str(screenshot))
    print('LASER_PREVIEW_OK', len(panel.last_plan.paths), second.obj_options['name'], screenshot, flush=True)
    print('LASER_MULTIPASS_OK', len(panel.last_plan.pass_plans), panel.last_plan.options.interlace_n, flush=True)


def machine_journey(app, qapp, errors):
    from unittest.mock import patch
    from mikrocam.bridge.serial_transport import PortInfo
    from mikrocam.machine.controller import MachineController
    from mikrocam.machine.fake import FakeGRBL
    from mikrocam.machine.models import MachineState
    from mikrocam.ui.machine_panel import open_machine_panel
    fake = FakeGRBL()
    fake.machine_position = (3., 4., 5.)
    fake.work_system = 'G55'
    fake.offsets['G54'] = fake.offsets['G55'] = (1., 2., 3.)
    fake.units, fake.distance, fake.spindle, fake.coolant = 'G20', 'G90', 'M3', ('M8',)
    with patch('mikrocam.ui.machine_panel.list_ports', return_value=(PortInfo('FAKE', 'Smoke simulator'),)):
        action = next(action for action in app.ui.menu_plugins.actions() if action.text() == 'Machine')
        action.trigger()
        panel = app._mikrocam_machine_panel
        assert not fake.is_open and not fake.writes
        assert open_machine_panel(app) is panel
        panel.controller_factory = lambda port: MachineController(fake)
        panel.connect_machine()
        pump_until(qapp, lambda: panel.last_snapshot.machine_position_mm == (3., 4., 5.),
                   errors, 'simulated machine connection')
        assert panel.last_snapshot.work_position_mm == (2., 2., 2.)
        assert panel.last_snapshot.state is MachineState.IDLE
        assert tuple(label.text() for label in panel.machine_labels) == ('3.000', '4.000', '5.000')
        worker = panel._worker
        assert worker is not None and worker.isRunning()
        assert panel.close()
        assert not panel.busy and not fake.is_open
        assert open_machine_panel(app) is panel
        panel.connect_machine()
        pump_until(qapp, lambda: panel.last_snapshot.machine_position_mm == (3., 4., 5.),
                   errors, 'simulated machine reconnection')
    assert set(fake.writes) == {b'?', b'$$\n'}
    print('MACHINE_READ_ONLY_OK', flush=True)
    machine_manual_journey(panel, qapp, fake, errors)
    screenshot = ROOT / '.venv/machine-smoke.png'
    assert app.ui.grab().save(str(screenshot))
    print('MACHINE_MANUAL_OK', screenshot, flush=True)
    return fake


def machine_manual_journey(panel, qapp, fake, errors):
    from mikrocam.machine.manual_protocol import validate_command
    from mikrocam.machine.models import ManualPhase
    controls = panel.manual_controls
    pump_until(qapp, lambda: controls.select_g54_button.isEnabled(), errors, 'G54 admission')
    controls.select_g54_button.click()
    pump_until(qapp, lambda: panel.last_snapshot.manual.phase is ManualPhase.COMPLETE
               and panel.last_snapshot.manual.action == 'select_g54', errors, 'G54 selection')
    assert fake.work_system == 'G54' and b'G54\n' in fake.writes
    controls.jog_buttons[('X', 1)].click()
    assert not controls.jog_buttons[('X', 1)].isEnabled()
    pump_until(qapp, lambda: panel.last_snapshot.manual.phase is ManualPhase.COMPLETE
               and panel.last_snapshot.manual.action == 'jog', errors, 'bounded X jog')
    assert abs(panel.last_snapshot.machine_position_mm[0] - 3.1) < 1e-9
    assert fake.units == 'G20' and fake.distance == 'G90'
    assert fake.spindle == 'M5' and fake.coolant == ('M9',)
    controls.zero_buttons['XY'].click()
    pump_until(qapp, lambda: panel.last_snapshot.manual.phase is ManualPhase.COMPLETE
               and panel.last_snapshot.manual.action == 'zero', errors, 'persistent XY zero')
    assert panel.last_snapshot.work_position_mm == (0., 0., 2.)
    assert fake.offsets['G55'] == (1., 2., 3.) and fake.offsets['G54'][2] == 3.
    controls.jog_buttons[('Y', 1)].click()
    pump_until(qapp, lambda: panel.last_snapshot.manual.phase is ManualPhase.MOVING,
               errors, 'owned Y jog')
    controls.cancel_button.click()
    pump_until(qapp, lambda: b'\x85' in fake.writes and panel.last_snapshot.manual.can_jog,
               errors, 'verified jog cancellation')
    assert not panel.last_snapshot.manual.stop_unverified
    assert b'G10 L20 P1 X0 Y0\n' in fake.writes and b'M5 M9\n' in fake.writes
    for command in fake.writes:
        validate_command(command)
    print('MACHINE_JOG_G54_CANCEL_OK', fake.machine_position, flush=True)


def render_and_quit(app, qapp, errors, machine_transport):
    from PyQt6 import QtCore
    import numpy as np
    app.collection.set_active('smoke_gerber')
    app.ui.splitter.setSizes([300, 700])
    app.on_zoom_fit()
    ready_at = time.monotonic() + 2.5
    pump_until(qapp, lambda: time.monotonic() >= ready_at, errors, 'desktop render')
    assert qapp.platformName() not in {'offscreen', 'minimal'}, 'Desktop rendering required'
    assert app.use_3d_engine, 'Smoke requires the real VisPy/OpenGL canvas'
    pixels = app.plotcanvas.render()
    assert pixels.size and np.ptp(pixels[..., :3]) > 0, 'Empty canvas rendering'
    screenshot = ROOT / '.venv/startup-smoke.png'
    image = app.ui.grab()
    assert not image.isNull() and image.save(str(screenshot))
    print('RENDER_OK', screenshot, flush=True)
    app.should_we_save = False
    QtCore.QTimer.singleShot(0, lambda: app.quit_application(silent=True))
    qapp.exec()
    assert not errors, 'Exception during normal shutdown'
    assert not any(thread.isRunning() for thread in app.workers.threads)
    if hasattr(app, 'listen_th'):
        assert not app.listen_th.isRunning()
        assert app.new_launch.thread_exit
    assert not any(process.is_alive() for process in app.pool._pool)
    assert not multiprocessing.active_children(), 'Application child process survived shutdown'
    assert not app._mikrocam_machine_panel.busy and not machine_transport.is_open
    assert not app._mikrocam_preflight_panel.busy
    from mikrocam.machine.job_models import JobPhase
    assert app._mikrocam_machine_panel.last_snapshot.job.phase is JobPhase.ABORTED
    assert app._mikrocam_machine_panel.last_snapshot.job.stop_unverified
    assert b'\x18' in machine_transport.writes
    print('JOB_ACTIVE_SHUTDOWN_OK', flush=True)
    print('PREFLIGHT_SHUTDOWN_OK', flush=True)
    print('MACHINE_SHUTDOWN_OK', flush=True)
    print('SHUTDOWN_OK', flush=True)


def laser_export_journey(app, qapp, sandbox, errors):
    from io import StringIO
    from unittest.mock import patch
    import xml.etree.ElementTree as ET
    import zipfile
    import ezdxf
    from mikrocam.core.laser_json import recipe_from_json
    from mikrocam.core.laser_manifest import manifest_from_json
    panel = app._mikrocam_laser_cam_panel
    plan = panel.last_plan
    assert plan is not None and len(plan.pass_plans) == 2
    controls = panel.export_controls
    for format in ('svg', 'dxf'):
        target = sandbox / f'laser-{format}.zip'
        controls.format_combo.setCurrentIndex(controls.format_combo.findData(format))
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', return_value=(str(target), '')):
            controls.export_zip()
        pump_until(qapp, lambda: not panel.busy, errors, f'laser {format} export')
        assert target.is_file(), panel.status_label.text()
        with zipfile.ZipFile(target) as archive:
            manifest = manifest_from_json(archive.read('manifest.json').decode('utf-8'))
            assert manifest['format'] == format and manifest['interlace_n'] == 3
            assert len(archive.namelist()) == 5
            assert recipe_from_json(archive.read('recipe.json').decode('utf-8')) == plan.job.recipe
            for record in manifest['passes']:
                assert record['path_count'] == len(plan.paths)
                document = archive.read(record['file']).decode('utf-8')
                if format == 'svg':
                    count = len(ET.fromstring(document).findall('{http://www.w3.org/2000/svg}polyline'))
                else:
                    drawing = ezdxf.read(StringIO(document))
                    assert drawing.units == 4 and not drawing.audit().has_errors
                    count = len(drawing.modelspace())
                assert count == len(plan.paths)
        (ROOT / '.venv' / target.name).write_bytes(target.read_bytes())
        print('LASER_EXPORT_OK', format, target.stat().st_size, flush=True)
    panel.input_scroll.verticalScrollBar().setValue(0)
    qapp.processEvents()
    assert app.ui.grab().save(str(ROOT / '.venv/laser-export-smoke.png'))


def run_smoke(sandbox, state):
    from PyQt6 import QtCore, QtWidgets
    from qt_settings_sandbox import install_settings_sandbox
    os.environ['APPDATA'] = str(sandbox / 'appdata')
    settings = sandbox / 'settings'
    install_settings_sandbox(settings)
    from defaults import AppDefaults
    AppDefaults.factory_defaults.update(first_run=False, global_version_check=False,
                                        global_process_number=2, global_worker_number=2)
    from appMain import App, ArgsThread
    from appGUI import VisPyPatches
    VisPyPatches.apply_patches()
    ArgsThread.address = (rf'\\.\pipe\FlatCAM-smoke-{uuid.uuid4().hex}', 'AF_PIPE')
    errors = []
    def exception_hook(exc_type, value, tb):
        errors.append(value)
        traceback.print_exception(exc_type, value, tb)
    sys.excepthook = exception_hook
    qapp = QtWidgets.QApplication([])
    # Retain the standard object's reference even if its constructor raises.
    app = App.__new__(App)
    state['app'] = app
    try:
        app.__init__(qapp=qapp, user_defaults=False)
        assert Path(app.data_path).is_relative_to(sandbox), 'User data sandbox was bypassed'
        assert Path(QtCore.QSettings('Open Source', 'FlatCAM_EVO').fileName()).is_relative_to(settings)
        assert not app.options['first_run'] and not app.options['global_version_check']
        print('STARTUP_OK', flush=True)
        assert_product_title(app)
        inspect_about(app, qapp, errors)
        app.inform.connect(lambda message: print('INFORM:', message, flush=True))
        app.workers.thread_exception.connect(lambda error: errors.append(error))
        pump_until(qapp, lambda: all(worker.receivers(worker.worker_task_signal) > 0
                   for worker in app.workers.workers), errors, 'worker readiness')
        from smoke_svg_drills import svg_drill_journey
        svg_drill_journey(app, qapp, sandbox, errors, pump_until, ROOT)
        from smoke_svg import svg_journey
        svg_journey(app, qapp, sandbox, errors, pump_until, ROOT)
        from smoke_svg_illustrator import svg_illustrator_journey
        svg_illustrator_journey(app, qapp, sandbox, errors, pump_until, ROOT)
        from smoke_cad_source import cad_source_journey
        cad_source_journey(app, qapp, sandbox, errors, pump_until, ROOT)
        from smoke_geometry_drills import geometry_drill_journey
        geometry_drill_journey(app, qapp, sandbox, errors, pump_until, ROOT)
        from smoke_excellon_merge import excellon_merge_journey
        excellon_merge_journey(app, qapp, sandbox, errors, pump_until, ROOT)
        from smoke_pdf_vectors import pdf_vector_journey
        pdf_vector_journey(app, qapp, sandbox, errors, pump_until, ROOT)
        from smoke_manufacturing_import import manufacturing_import_journey
        manufacturing_import_journey(app, qapp, sandbox, errors, pump_until, ROOT)
        cam_journey(app, qapp, sandbox, errors)
        app.ui.showMaximized()
        qapp.processEvents()
        laser_journey(app, qapp, sandbox, errors)
        laser_export_journey(app, qapp, sandbox, errors)
        from smoke_probe import probe_journey
        probe_journey(app, qapp, errors, pump_until, ROOT)
        machine_transport = machine_journey(app, qapp, errors)
        from smoke_console import console_journey
        console_journey(app, qapp, errors, pump_until, ROOT)
        from smoke_preflight import preflight_journey
        preflight_journey(app, qapp, sandbox, errors, pump_until, ROOT)
        from smoke_job import job_journey
        machine_transport = job_journey(app, qapp, errors, pump_until, ROOT)
        from smoke_dry_run import dry_run_journey
        machine_transport = dry_run_journey(app, qapp, errors, pump_until, ROOT)
        render_and_quit(app, qapp, errors, machine_transport)
    except BaseException:
        traceback.print_exc()
        if getattr(app, 'workers', None) is not None:
            try:
                pump_until(qapp, lambda: app.workers._pending_count == 0, [],
                           'failed-run plot cleanup', timeout=5)
            except BaseException:
                traceback.print_exc()
        try:
            app.should_we_save = False
            app.quit_application(silent=True)
        except BaseException:
            traceback.print_exc()
            # Failed construction may lack lifecycle dependencies. This cannot pass.
            if getattr(app, 'pool', None) is not None:
                app.pool.terminate()
                app.pool.join()
            if getattr(app, 'workers', None) is not None:
                app.workers.quit()
        return 1, (app, qapp)
    return 0, (app, qapp)


def main():
    os.chdir(ROOT)
    (ROOT / '.venv').mkdir(exist_ok=True)
    sys.path.insert(0, str(ROOT))
    os.environ['QT_API'] = 'pyqt6'
    state = {}
    print('SMOKE_PID', os.getpid(), flush=True)
    def watchdog():
        print('SMOKE_TIMEOUT: exceeded 85 seconds', file=sys.stderr, flush=True)
        # These are this smoke process's children, never another application tree.
        for process in multiprocessing.active_children():
            print('SMOKE_TIMEOUT_CHILD', process.pid, file=sys.stderr, flush=True)
            process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
        os._exit(1)
    timeout = threading.Timer(85, watchdog)
    timeout.daemon = True
    timeout.start()
    status, keepalive = 1, None
    with tempfile.TemporaryDirectory(prefix='evo-smoke-') as temporary:
        try:
            status, keepalive = run_smoke(Path(temporary), state)
        except BaseException:
            traceback.print_exc()
    timeout.cancel()
    sys.stdout.flush()
    sys.stderr.flush()
    # Production flatcam.py also bypasses native Qt/VisPy GC after normal cleanup.
    # Keep the GUI references alive until this point; success needs all assertions.
    os._exit(status)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
