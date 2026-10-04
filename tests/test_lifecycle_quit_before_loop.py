"""A quit requested before Qt's event loop starts must still end that loop.

Startup scripts (``--shellfile`` with ``quit_app``) and the ``quit`` startup argument run
inside ``App.__init__``, before ``app.exec()``. Qt ignores ``QApplication.quit()`` while no
loop is running, which left a hidden application process alive.
"""
import time
from unittest.mock import Mock

from PyQt6 import QtCore

from appHandlers.appLifecycle import AppLifecycle


def _host():
    app = Mock()
    app.tools_db_tab = None
    app._mikrocam_machine_panel = None
    app._mikrocam_preflight_panel = None
    app.geo_editor = app.exc_editor = app.grb_editor = app.gcode_editor = None
    app.cmd_line_headless = 1
    app.use_3d_engine = True
    app.new_launch.address = ('\\\\.\\pipe\\mikrocam-test-unused-quit', 'AF_PIPE')
    app.listen_th.isRunning.return_value = False
    app.options = {}
    return app


def test_quit_requested_before_event_loop_ends_loop_when_it_starts(qapp):
    app = _host()
    assert AppLifecycle(app).quit_application(silent=True) is True
    guard = {'fired': False}

    def guard_quit():
        guard['fired'] = True
        qapp.quit()

    QtCore.QTimer.singleShot(5000, guard_quit)
    started = time.monotonic()
    qapp.exec()
    assert not guard['fired'], 'quit requested before the event loop was lost'
    assert time.monotonic() - started < 4
    app.pool.terminate.assert_called_once_with()
    app.workers.quit.assert_called_once_with()
