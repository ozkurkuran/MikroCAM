"""Application teardown must retain an offline analysis thread that has not joined."""
from types import SimpleNamespace
from unittest.mock import Mock

from appHandlers.appLifecycle import AppLifecycle


def test_preflight_join_failure_prevents_host_disposal(qapp):
    panel=SimpleNamespace(shutdown=Mock(return_value=False))
    app=SimpleNamespace(log=Mock(),inform=Mock(),defaults=Mock(),options={},
                        _mikrocam_preflight_panel=panel,ui=Mock())
    lifecycle=AppLifecycle(app)
    assert lifecycle.quit_application(silent=True) is False
    panel.shutdown.assert_called_once_with()
    app.ui.hide.assert_not_called()
    app.defaults.update.assert_not_called()
