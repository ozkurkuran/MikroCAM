"""Focused native KiCad transfer, CAM and normal shutdown under the shared120s watchdog.

Run with the validated checkout Python: python tests/smoke_kicad_app.py.
Optional MIKROCAM_REAL_KICAD_PACKAGE includes a retained real IPC export.
Requires desktop/OpenGL; uses isolated settings and never accesses physical hardware.
"""
import sys,os,uuid,multiprocessing,traceback,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
import smoke_app

def run_native_smoke(sandbox,state):
    from PyQt6 import QtCore,QtWidgets
    from qt_settings_sandbox import install_settings_sandbox
    os.environ['APPDATA']=str(sandbox/'appdata')
    settings=sandbox/'settings';install_settings_sandbox(settings)
    from defaults import AppDefaults
    AppDefaults.factory_defaults.update(first_run=False,global_version_check=False,global_process_number=2,global_worker_number=2)
    from appMain import App,ArgsThread
    from appGUI import VisPyPatches
    VisPyPatches.apply_patches()
    ArgsThread.address=(rf'\\.\pipe\MikroCAM-kicad-smoke-{uuid.uuid4().hex}','AF_PIPE')
    errors=[]
    def exception_hook(kind,value,tb):
        errors.append(value);traceback.print_exception(kind,value,tb)
    sys.excepthook=exception_hook
    qapp=QtWidgets.QApplication([]);app=App.__new__(App);state['app']=app
    try:
        app.__init__(qapp=qapp,user_defaults=False)
        assert Path(app.data_path).is_relative_to(sandbox)
        assert Path(QtCore.QSettings('Open Source','FlatCAM_EVO').fileName()).is_relative_to(settings)
        app.workers.thread_exception.connect(errors.append)
        smoke_app.assert_product_title(app)
        smoke_app.pump_until(qapp,lambda:all(w.receivers(w.worker_task_signal)>0 for w in app.workers.workers),errors,'workers')
        print('KICAD_FOCUSED_NATIVE_STARTUP_OK',flush=True)
        from smoke_kicad_transfer import kicad_transfer_journey
        kicad_transfer_journey(app,qapp,sandbox,errors,smoke_app.pump_until,smoke_app.ROOT)
        smoke_app.cam_journey(app,qapp,sandbox,errors)
        app.ui.showMaximized();app.collection.set_active('smoke_gerber');app.on_zoom_fit()
        ready=time.monotonic()+2.5
        smoke_app.pump_until(qapp,lambda:time.monotonic()>=ready,errors,'native rendering')
        import numpy as np
        pixels=app.plotcanvas.render()
        assert qapp.platformName() not in {'offscreen','minimal'} and app.use_3d_engine
        assert pixels.size and np.ptp(pixels[...,:3])>0
        assert app.ui.grab().save(str(smoke_app.ROOT/'.venv/kicad-focused-desktop.png'))
        app.should_we_save=False
        QtCore.QTimer.singleShot(0,lambda:app.quit_application(silent=True));qapp.exec()
        assert not errors
        assert not any(t.isRunning() for t in app.workers.threads)
        assert not app.listen_th.isRunning() and app.new_launch.thread_exit
        assert not any(p.is_alive() for p in app.pool._pool) and not multiprocessing.active_children()
        print('KICAD_FOCUSED_NATIVE_RENDER_SHUTDOWN_OK',flush=True)
        return 0,(app,qapp)
    except BaseException:
        traceback.print_exc();app.should_we_save=False;app.quit_application(silent=True)
        return 1,(app,qapp)

if __name__=='__main__':
    multiprocessing.freeze_support()
    smoke_app.run_smoke=run_native_smoke
    smoke_app.main()
