"""The host must not destroy a still-running machine communication worker."""
from types import SimpleNamespace
from unittest.mock import Mock

from appHandlers.appLifecycle import AppLifecycle


def test_host_shutdown_wait_failure_keeps_application_alive(qapp):
    panel = SimpleNamespace(shutdown=Mock(return_value=False))
    app = SimpleNamespace(log=Mock(), inform=Mock(), defaults=Mock(), options={},
                          _mikrocam_machine_panel=panel, ui=Mock())
    lifecycle = AppLifecycle(app)
    assert lifecycle.quit_application(silent=True) is False
    panel.shutdown.assert_called_once_with()
    app.ui.hide.assert_not_called()
    app.defaults.update.assert_not_called()
