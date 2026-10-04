"""Hardware-free journey executed inside the frozen bundle (MikroCAMSmoke.exe).

Built from the same PyInstaller Analysis and PYZ as MikroCAM.exe, so it exercises exactly the
shipped modules and binaries. It imports no test modules. Usage:

    MikroCAMSmoke.exe --out DIR [--native]

Exit status 0 means: frozen modules only, optional heavy dependencies absent, visual codecs
lazy, bundled Gerber/Excellon → isolation → CNC → project roundtrip, bitmap/SVG/PDF visual
jobs saved and reopened (JSON and project), normal worker/pool shutdown. --native also
requires a real OpenGL canvas render. It never opens a serial port, camera or machine.
"""
import multiprocessing
import os
from pathlib import Path
import sys
import threading
import time
import traceback
import uuid

SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" width="30mm" height="18mm" viewBox="0 0 30 18">
<defs><clipPath id="clip"><rect x="2" y="2" width="5" height="5"/></clipPath></defs>
<rect width="30" height="18" fill="white"/><rect x="1" y="1" width="10" height="10" clip-path="url(#clip)"/>
<path d="M15 2h10v10h-10z M17 4h6v6h-6z" fill-rule="evenodd"/>
<path d="M2 15h20" stroke="black" stroke-width=".1" transform="translate(1 0)"/>
</svg>'''
OPTIONAL_ABSENT = ('rasterio', 'svgtrace', 'playwright', 'ortools', 'pytest')
LAZY_CODECS = ('resvg_py', 'PyQt6.QtPdf')


def log(*parts):
    print(*parts, flush=True)


def pump_until(qapp, predicate, errors, stage, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if errors:
            raise AssertionError(f'Asynchronous exception during {stage}: {errors[0]!r}')
        if predicate():
            return
        time.sleep(0.02)
    raise TimeoutError(f'Timed out during {stage}')


def sandbox_settings(directory):
    """Redirect named QSettings to INI files so the real registry stays untouched."""
    from PyQt6 import QtCore
    original = QtCore.QSettings
    directory.mkdir(parents=True, exist_ok=True)

    class SandboxedSettings(original):
        def __init__(self, *args, **kwargs):
            if args and isinstance(args[0], original.Scope):
                args = args[1:]
            if args and isinstance(args[0], str) and (len(args) == 1 or isinstance(args[1], str)):
                name = '-'.join(args[:2]).replace(' ', '_') + '.ini'
                args = (str(directory / name), original.Format.IniFormat, *args[2:])
            super().__init__(*args, **kwargs)

    QtCore.QSettings = SandboxedSettings


def check_frozen_environment():
    import importlib.util
    assert getattr(sys, 'frozen', False), 'Not running from a frozen bundle'
    bundle = Path(sys._MEIPASS).resolve()
    import appMain
    import mikrocam.core.identity as identity
    for module in (appMain, identity):
        assert Path(module.__file__).resolve().is_relative_to(bundle), module.__file__
    for name in OPTIONAL_ABSENT:
        assert importlib.util.find_spec(name) is None, f'{name} must not be bundled'
    import camlib
    assert camlib.HAS_ORTOOLS is False, 'OR-Tools must be absent from the Windows binary'
    log('FROZEN_ENVIRONMENT_OK', bundle, identity.NAME, identity.VERSION)
    return bundle


def accept_import_settings(qapp, errors, accepted):
    from PyQt6 import QtWidgets
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


def reopen_project(app, qapp, project, errors, ready):
    from PyQt6 import QtCore
    app.should_we_save = False
    accepted = []
    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: accept_import_settings(qapp, errors, accepted))
    timer.start(50)
    try:
        app.f_handlers.open_project(str(project), plot=True)
        pump_until(qapp, lambda: ready() and app.workers._pending_count == 0, errors, 'project reopen', 60)
    finally:
        timer.stop()
    assert accepted == ['Import Settings'], accepted


def cam_journey(app, qapp, bundle, out, errors):
    samples = bundle / 'assets' / 'examples' / 'files'
    app.f_handlers.open_gerber(str(samples / 'test.gbr'), outname='smoke_gerber')
    app.f_handlers.open_excellon(str(samples / 'test.txt'), outname='smoke_drill')
    pump_until(qapp, lambda: {'smoke_gerber', 'smoke_drill'} <= set(app.collection.get_names()), errors, 'import')
    gerber = app.collection.get_by_name('smoke_gerber')
    assert gerber.kind == 'gerber' and gerber.solid_geometry
    gerber.isolate(dia=0.2, passes=1, combine=True, outname='smoke_iso', plot=True)
    pump_until(qapp, lambda: app.collection.get_by_name('smoke_iso') is not None, errors, 'isolation')
    geometry = app.collection.get_by_name('smoke_iso')
    geometry.generatecncjob(outname='smoke_cnc', dia=0.2, z_cut=-0.1, z_move=2.0, feedrate=120, use_thread=False)
    pump_until(qapp, lambda: app.collection.get_by_name('smoke_cnc') is not None, errors, 'CNC generation')
    cnc = app.collection.get_by_name('smoke_cnc')
    assert cnc.kind == 'cncjob' and cnc.gcode and cnc.gcode_parsed
    pump_until(qapp, lambda: app.workers._pending_count == 0, errors, 'plot completion')
    log('CAM_OK', len(cnc.gcode))
    return cnc.gcode


def pdf_bytes():
    from io import BytesIO
    from reportlab.pdfgen.canvas import Canvas
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=(30 / 25.4 * 72, 18 / 25.4 * 72))
    canvas.setFillColorRGB(0, 0, 0)
    canvas.rect(2 / 25.4 * 72, 11 / 25.4 * 72, 5 / 25.4 * 72, 5 / 25.4 * 72, fill=1, stroke=0)
    canvas.save()
    return stream.getvalue()


def visual_sources(out):
    from PIL import Image
    image = Image.new('1', (600, 360), 1)
    for row in range(360):
        image.putpixel((row % 600, row), 0)
    bitmap = out / 'visual.png'
    image.save(bitmap)
    (out / 'visual.svg').write_bytes(SVG)
    (out / 'visual.pdf').write_bytes(pdf_bytes())
    return (bitmap, out / 'visual.svg', out / 'visual.pdf')


def visual_journey(app, qapp, out, errors):
    from mikrocam.ui.visual_interlace_panel import open_visual_interlace
    from mikrocam.bridge.visual_project import read_visual_job
    lazy_before = {name: name in sys.modules for name in LAZY_CODECS}
    assert not any(lazy_before.values()), f'Visual codecs imported at startup: {lazy_before}'
    action = next(a for a in app.ui.menu_plugins.actions() if a.text() == 'Görsel satır serpiştirme')
    action.trigger()
    panel = open_visual_interlace(app)
    kinds = []
    for path in visual_sources(out):
        panel.open_source(path)
        pump_until(qapp, lambda: panel.worker is None, errors, 'visual source ' + path.suffix)
        assert panel.source is not None, panel.status.text()
        panel.width.setValue(30)
        panel.height.setValue(18)
        panel.prepare()
        pump_until(qapp, lambda: panel.worker is None, errors, 'visual prepare ' + path.suffix)
        assert panel.job is not None and panel.job.mask.black_pixel_count > 0, panel.status.text()
        destination = out / (path.stem + path.suffix.replace('.', '-') + '.json')
        expected = panel.job.mask.sha256
        panel.save_job(destination)
        pump_until(qapp, lambda: panel.worker is None, errors, 'visual JSON save')
        panel.load_job(destination)
        pump_until(qapp, lambda: panel.worker is None, errors, 'visual JSON load')
        assert panel.job.mask.sha256 == expected
        kinds.append(panel.job.source.info.kind)
    assert {name for name in LAZY_CODECS if name in sys.modules} == set(LAZY_CODECS), 'codecs never loaded'
    before = set(app.collection.get_names())
    panel.save_to_project()
    pump_until(qapp, lambda: panel.worker is None and bool(set(app.collection.get_names()) - before),
               errors, 'visual project carrier')
    carrier = (set(app.collection.get_names()) - before).pop()
    expected = read_visual_job(app.collection.get_by_name(carrier)).mask.sha256
    log('VISUAL_BITMAP_SVG_PDF_JSON_OK', kinds)
    return panel, carrier, expected


def project_roundtrip(app, qapp, out, errors, gcode, carrier, visual_sha):
    import json
    import lzma
    from mikrocam.bridge.visual_project import read_visual_job
    project = out / 'frozen-smoke.FlatPrj'
    names = set(app.collection.get_names())
    app.f_handlers.save_project(str(project), silent=True)
    pump_until(qapp, lambda: project.is_file() and project.stat().st_size > 0, errors, 'project save')
    data = project.read_bytes()
    if data.startswith(b'\xfd7zXZ\x00'):
        data = lzma.decompress(data)
    assert json.loads(data)['version'] == app.version
    previous = app.collection.get_by_name('smoke_cnc')
    reopen_project(app, qapp, project, errors,
                   lambda: app.collection.get_by_name('smoke_cnc') not in (None, previous)
                   and set(app.collection.get_names()) == names)
    assert app.collection.get_by_name('smoke_cnc').gcode == gcode
    assert read_visual_job(app.collection.get_by_name(carrier)).mask.sha256 == visual_sha
    log('PROJECT_CAM_AND_VISUAL_ROUNDTRIP_OK', sorted(names))


def render_check(app, qapp, errors):
    import numpy as np
    app.ui.showMaximized()
    app.collection.set_active('smoke_gerber')
    app.on_zoom_fit()
    ready = time.monotonic() + 2.5
    pump_until(qapp, lambda: time.monotonic() >= ready, errors, 'native rendering')
    assert qapp.platformName() not in {'offscreen', 'minimal'} and app.use_3d_engine
    pixels = app.plotcanvas.render()
    assert pixels.size and np.ptp(pixels[..., :3]) > 0, 'Empty canvas rendering'
    log('NATIVE_RENDER_OK', qapp.platformName())


def shutdown(app, qapp, errors):
    from PyQt6 import QtCore
    app.should_we_save = False
    QtCore.QTimer.singleShot(0, lambda: app.quit_application(silent=True))
    qapp.exec()
    assert not errors, errors
    assert not any(thread.isRunning() for thread in app.workers.threads)
    assert not app.listen_th.isRunning() and app.new_launch.thread_exit
    assert not any(process.is_alive() for process in app.pool._pool)
    assert not multiprocessing.active_children(), 'child process survived shutdown'
    log('NORMAL_SHUTDOWN_OK')


def journey(out, native):
    from PyQt6 import QtWidgets
    bundle = check_frozen_environment()
    sandbox_settings(out / 'settings')
    from defaults import AppDefaults
    AppDefaults.factory_defaults.update(first_run=False, global_version_check=False,
                                        global_process_number=2, global_worker_number=2)
    from appMain import App, ArgsThread
    from appGUI import VisPyPatches
    VisPyPatches.apply_patches()
    ArgsThread.address = (rf'\\.\pipe\MikroCAM-frozen-smoke-{uuid.uuid4().hex}', 'AF_PIPE')
    errors = []
    sys.excepthook = lambda kind, value, tb: (errors.append(value), traceback.print_exception(kind, value, tb))
    qapp = QtWidgets.QApplication([sys.argv[0]])
    app = App.__new__(App)
    app.__init__(qapp=qapp, user_defaults=False)
    data = Path(app.data_path).resolve()
    assert data.is_relative_to(out) or data == Path(sys.executable).resolve().parent / 'config', data
    app.workers.thread_exception.connect(errors.append)
    pump_until(qapp, lambda: all(w.receivers(w.worker_task_signal) > 0 for w in app.workers.workers),
               errors, 'workers')
    log('FROZEN_STARTUP_OK', app.ui.windowTitle())
    gcode = cam_journey(app, qapp, bundle, out, errors)
    panel, carrier, visual_sha = visual_journey(app, qapp, out, errors)
    project_roundtrip(app, qapp, out, errors, gcode, carrier, visual_sha)
    panel.shutdown()
    panel.close()
    if native:
        render_check(app, qapp, errors)
    shutdown(app, qapp, errors)
    return app, qapp


def main(argv):
    out = Path(argv[argv.index('--out') + 1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    os.environ['APPDATA'] = str(out / 'appdata')
    os.environ['QT_API'] = 'pyqt6'
    timer = threading.Timer(240, lambda: (log('FROZEN_SMOKE_TIMEOUT'), os._exit(3)))
    timer.daemon = True
    timer.start()
    status, keep = 1, None
    try:
        keep = journey(out, '--native' in argv)
        status = 0
        log('FROZEN_SMOKE_PASS')
    except BaseException:
        traceback.print_exc()
        log('FROZEN_SMOKE_FAIL')
    timer.cancel()
    sys.stdout.flush()
    sys.stderr.flush()
    assert keep is not None or status  # Qt/VisPy objects stay referenced until os._exit, like flatcam.py.
    os._exit(status)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main(sys.argv)
