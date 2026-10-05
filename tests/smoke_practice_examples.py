"""Desktop smoke for the three CAM practice examples in assets/examples.

Run with the checkout's Python: .venv/Scripts/python.exe tests/smoke_practice_examples.py
Requires a real desktop/OpenGL context; never connects to manufacturing hardware.
"""
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import threading
import traceback
import uuid


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

# number, board width, board height, {drill diameter: count}, copper islands, copper holes
CASES = [(1, 36, 22, {0.8: 8}, 2, 0),
         (2, 50, 35, {0.8: 14, 1.0: 8, 3.2: 2}, 16, 0),
         (3, 40, 30, {0.8: 8, 1.6: 4}, 5, 1)]


def practice_journey(app, qapp, errors, pump_until):
    from shapely.geometry import Point
    from shapely.ops import unary_union
    assert app.options['units'] == 'MM'
    for number, width, height, expected_drills, islands, holes in CASES:
        prefix = f'ex{number:02d}'
        script = (ROOT / f'assets/examples/practice_{number:02d}.FlatScript').read_text(encoding='ascii')
        app.shell.exec_command_test(script, no_echo=True)
        names = [f'{prefix}_{suffix}' for suffix in ('copper', 'outline', 'drill', 'iso', 'cutout')]
        pump_until(qapp, lambda: all(app.collection.get_by_name(name) is not None for name in names),
                   errors, f'{prefix} objects')
        copper = unary_union(app.collection.get_by_name(f'{prefix}_copper').solid_geometry)
        polygons = list(copper.geoms) if hasattr(copper, 'geoms') else [copper]
        assert copper.is_valid
        assert len(polygons) == islands, (prefix, len(polygons), islands)
        assert sum(len(polygon.interiors) for polygon in polygons) == holes
        drills = app.collection.get_by_name(f'{prefix}_drill')
        observed = {round(tool['tooldia'], 3): len(tool['drills']) for tool in drills.tools.values()}
        assert observed == expected_drills, (prefix, observed)
        for tool in drills.tools.values():
            for point in tool['drills']:
                assert copper.contains(point.buffer(tool['tooldia'] / 2)), (prefix, point)
        outline = app.collection.get_by_name(f'{prefix}_outline')
        expected = (-0.05, -0.05, width + 0.05, height + 0.05)
        assert all(abs(a - b) < 0.001 for a, b in zip(outline.bounds(), expected)), outline.bounds()
        assert app.collection.get_by_name(f'{prefix}_iso').solid_geometry
        cutout = app.collection.get_by_name(f'{prefix}_cutout')
        pieces = [geom for geom in cutout.flatten(cutout.solid_geometry) if not geom.is_empty]
        assert len(pieces) == 4, (prefix, len(pieces))
        # Zero margin: tool centre 0.5 mm outside the outline stroke's outer edge.
        expected = (-0.55, -0.55, width + 0.55, height + 0.55)
        assert all(abs(a - b) < 0.001 for a, b in zip(cutout.bounds(), expected)), cutout.bounds()
        before = app.collection.get_names()
        try:
            app.shell.exec_command_test(script, no_echo=True)
        except Exception as error:
            assert 'already exist' in str(app.shell.tcl.eval('set errorInfo')), error
        else:
            raise AssertionError('Repeated script must reject duplicate names')
        assert app.collection.get_names() == before
        print(f'{prefix}: OBJECTS, DRILLS {observed}, ISOLATION, 4 CUTOUT BRIDGES OK', flush=True)
    copper = unary_union(app.collection.get_by_name('ex03_copper').solid_geometry)
    assert not copper.contains(Point(20, 15))
    assert copper.contains(Point(3, 15))
    print('PRACTICE_EXAMPLES_OK', flush=True)


def run_smoke(sandbox):
    from PyQt6 import QtWidgets
    from qt_settings_sandbox import install_settings_sandbox
    from smoke_app import pump_until
    os.environ['APPDATA'] = str(sandbox / 'appdata')
    install_settings_sandbox(sandbox / 'settings')
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
    app = App.__new__(App)
    status = 1
    try:
        app.__init__(qapp=qapp, user_defaults=False)
        assert Path(app.data_path).is_relative_to(sandbox), 'User data sandbox was bypassed'
        app.workers.thread_exception.connect(lambda error: errors.append(error))
        pump_until(qapp, lambda: all(worker.receivers(worker.worker_task_signal) > 0
                   for worker in app.workers.workers), errors, 'worker readiness')
        practice_journey(app, qapp, errors, pump_until)
        assert not errors, errors
        status = 0
    except BaseException:
        traceback.print_exc()
    finally:
        try:
            pump_until(qapp, lambda: app.workers._pending_count == 0, [], 'plot cleanup', timeout=10)
        except BaseException:
            traceback.print_exc()
        try:
            app.should_we_save = False
            app.quit_application(silent=True)
        except BaseException:
            traceback.print_exc()
            if getattr(app, 'pool', None) is not None:
                app.pool.terminate()
                app.pool.join()
    return status, (app, qapp)


def main():
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ['QT_API'] = 'pyqt6'
    def watchdog():
        print('SMOKE_TIMEOUT: exceeded 90 seconds', file=sys.stderr, flush=True)
        for process in multiprocessing.active_children():
            process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
        os._exit(1)
    timeout = threading.Timer(90, watchdog)
    timeout.daemon = True
    timeout.start()
    status, keepalive = 1, None
    with tempfile.TemporaryDirectory(prefix='evo-practice-') as temporary:
        try:
            status, keepalive = run_smoke(Path(temporary))
        except BaseException:
            traceback.print_exc()
    timeout.cancel()
    sys.stdout.flush()
    sys.stderr.flush()
    # Same as smoke_app.py: bypass native Qt/VisPy GC after normal cleanup.
    os._exit(status)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
