"""Focused visual workflow in the real Evo desktop under the shared120s watchdog.

Requires desktop/OpenGL, isolates settings, and performs no manufacturing communication.
"""
import multiprocessing
import os
from pathlib import Path
import sys
import time
import traceback
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import smoke_app


def visual_journey(app, qapp, sandbox, errors):
    import json
    import numpy as np
    import zipfile
    from PIL import Image
    from io import BytesIO
    from mikrocam.ui.visual_interlace_panel import open_visual_interlace
    from mikrocam.bridge.visual_project import read_visual_job
    from mikrocam.bridge.visual_png import decode_mask_png
    from smoke_manufacturing_import import _reopen
    from test_visual_svg_pdf import SVG, pdf
    action = next(action for action in app.ui.menu_plugins.actions() if action.text() == 'Görsel satır serpiştirme')
    action.trigger()
    panel = open_visual_interlace(app)
    app.ui.showMaximized()
    image = Image.new('1', (600, 360), 1)
    for row in range(360): image.putpixel((row % 600, row), 0)
    files = ((sandbox / 'visual.png', None), (sandbox / 'visual.svg', SVG), (sandbox / 'visual.pdf', pdf()))
    for path, data in files:
        if data is None: image.save(path)
        else: path.write_bytes(data)
        panel.open_source(path)
        smoke_app.pump_until(qapp, lambda: panel.worker is None, errors, 'source inspection')
        assert panel.source is not None, panel.status.text()
        panel.width.setValue(30); panel.height.setValue(18)
        panel.prepare()
        smoke_app.pump_until(qapp, lambda: panel.worker is None, errors, 'visual prepare')
        assert panel.job is not None and panel.job.mask.black_pixel_count > 0, panel.status.text()
        assert (panel.job.mask.grid.width_px, panel.job.mask.grid.height_px) == (600, 360)
        assert panel.save_button.isEnabled() and not panel.lightburn_button.isEnabled()
        destination = sandbox / (path.stem + '.json')
        panel.save_job(destination)
        smoke_app.pump_until(qapp, lambda: panel.worker is None, errors, 'visual JSON save')
        original = panel.job.mask.sha256
        panel.load_job(destination)
        smoke_app.pump_until(qapp, lambda: panel.worker is None, errors, 'visual JSON load')
        assert panel.job.mask.sha256 == original
    package = sandbox / 'visual-groups.zip'
    panel._start('png', (panel.job, panel.plan, package))
    smoke_app.pump_until(qapp, lambda: panel.worker is None, errors, 'PNG package export')
    total = np.zeros(panel.job.mask.burn.shape, dtype=np.uint16)
    with zipfile.ZipFile(package) as archive:
        for k in range(3): total += decode_mask_png(archive.read(f'group-{k:02d}.png'), panel.job.mask.grid).burn
    assert np.array_equal(total, panel.job.mask.burn)
    original_units = app.options['units']
    original_app_units = app.app_units
    for units in ('MM', 'IN'):
        app.options['units'] = units
        app.app_units = units
        before_names = set(app.collection.get_names())
        panel.save_to_project()
        smoke_app.pump_until(qapp, lambda: panel.worker is None and bool(set(app.collection.get_names()) - before_names),
                             errors, 'visual project carrier ' + units)
        name = (set(app.collection.get_names()) - before_names).pop()
        carrier = app.collection.get_by_name(name)
        assert carrier.units == units, (units, carrier.units)
        assert read_visual_job(carrier).mask.grid == panel.job.mask.grid
        if units == 'MM':
            app.collection.set_active(name); app.collection.delete_active()
            smoke_app.pump_until(qapp, lambda: name not in app.collection.get_names(), errors, 'MM carrier cleanup')
    names = app.collection.get_names()
    assert len(names) == 1, (names, panel.status.text())
    owner = app.collection.get_by_name(names[0]); expected = panel.job.mask.sha256
    assert read_visual_job(owner).mask.sha256 == expected
    assert all(np.isfinite(v) for v in owner.bounds())
    project = sandbox / 'visual.FlatPrj'
    app.f_handlers.save_project(str(project), silent=True)
    assert project.is_file()
    for path, _ in files: path.unlink()
    _reopen(app, qapp, project, owner, names[0], errors, smoke_app.pump_until)
    restored = read_visual_job(app.collection.get_by_name(names[0]))
    assert app.collection.get_by_name(names[0]).units == 'IN'
    assert restored.mask.sha256 == expected and restored.source.info.kind == 'pdf'
    panel.project_sources.clear(); panel.project_sources.addItems(panel.host.source_names())
    panel.load_project_source()
    smoke_app.pump_until(qapp, lambda: panel.worker is None, errors, 'visual project job reopen')
    assert panel.job.mask.sha256 == expected
    panel.widget().ensureWidgetVisible(panel.preview)
    qapp.processEvents()
    assert panel.grab().save(str(smoke_app.ROOT / '.venv/visual-dock-native.png'))
    panel.shutdown(); panel.close()
    app.collection.delete_all()
    app.options['units'] = original_units
    app.app_units = original_app_units
    smoke_app.pump_until(qapp, lambda: not app.collection.get_names() and app.workers._pending_count == 0, errors, 'visual carrier cleanup')
    print('VISUAL_BITMAP_SVG_PDF_PNG_JSON_HOST_PROJECT_ROUNDTRIP_OK', flush=True)
    print('VISUAL_MM_IN_CARRIER_EMBEDDED_MM_ROUNDTRIP_OK', flush=True)


def run_native_smoke(sandbox, state):
    from PyQt6 import QtCore, QtWidgets
    from qt_settings_sandbox import install_settings_sandbox
    os.environ['APPDATA'] = str(sandbox / 'appdata')
    settings = sandbox / 'settings'; install_settings_sandbox(settings)
    from defaults import AppDefaults
    AppDefaults.factory_defaults.update(first_run=False, global_version_check=False,
                                        global_process_number=2, global_worker_number=2)
    from appMain import App, ArgsThread
    from appGUI import VisPyPatches
    VisPyPatches.apply_patches()
    ArgsThread.address = (rf'\\.\pipe\MikroCAM-visual-smoke-{uuid.uuid4().hex}', 'AF_PIPE')
    errors = []
    def exception_hook(kind, value, tb):
        errors.append(value); traceback.print_exception(kind, value, tb)
    sys.excepthook = exception_hook
    qapp = QtWidgets.QApplication([]); app = App.__new__(App); state['app'] = app
    try:
        app.__init__(qapp=qapp, user_defaults=False)
        assert Path(app.data_path).is_relative_to(sandbox)
        app.workers.thread_exception.connect(errors.append)
        smoke_app.assert_product_title(app)
        smoke_app.pump_until(qapp, lambda: all(w.receivers(w.worker_task_signal) > 0
            for w in app.workers.workers), errors, 'workers')
        print('VISUAL_FOCUSED_NATIVE_STARTUP_OK', flush=True)
        visual_journey(app, qapp, sandbox, errors)
        smoke_app.cam_journey(app, qapp, sandbox, errors)
        app.ui.showMaximized(); app.collection.set_active('smoke_gerber'); app.on_zoom_fit()
        ready = time.monotonic() + 2.5
        smoke_app.pump_until(qapp, lambda: time.monotonic() >= ready, errors, 'native rendering')
        import numpy as np
        pixels = app.plotcanvas.render()
        assert qapp.platformName() not in {'offscreen', 'minimal'} and app.use_3d_engine
        assert pixels.size and np.ptp(pixels[..., :3]) > 0
        assert app.ui.grab().save(str(smoke_app.ROOT / '.venv/visual-focused-desktop.png'))
        app.should_we_save = False
        QtCore.QTimer.singleShot(0, lambda: app.quit_application(silent=True)); qapp.exec()
        assert not errors and not any(t.isRunning() for t in app.workers.threads)
        assert not app.listen_th.isRunning() and app.new_launch.thread_exit
        assert not any(p.is_alive() for p in app.pool._pool) and not multiprocessing.active_children()
        print('VISUAL_FOCUSED_NATIVE_RENDER_SHUTDOWN_OK', flush=True)
        return 0, (app, qapp)
    except BaseException:
        traceback.print_exc(); app.should_we_save = False; app.quit_application(silent=True)
        return 1, (app, qapp)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    smoke_app.run_smoke = run_native_smoke
    smoke_app.main()
