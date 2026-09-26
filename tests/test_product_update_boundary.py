"""The product cannot offer or install a different upstream application."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def fake_app():
    return SimpleNamespace(options={'global_version_check': True, 'global_update_url': 'https://example.invalid/evo'},
                           defaults={'global_version_check': True}, beta=False,
                           inform=SimpleNamespace(emit=MagicMock()), log=MagicMock(),
                           worker_task=SimpleNamespace(emit=MagicMock()),
                           lifecycle=SimpleNamespace(version_check=MagicMock()),
                           _queue_version_check=MagicMock(), _check_queued=False, _check_in_progress=False,
                           quit_application=MagicMock())


@pytest.mark.parametrize('entry', ['on_check_for_updates', 'version_check', '_queue_version_check'])
@pytest.mark.parametrize('forced', [False, True])
def test_checks_cannot_reach_upstream_even_with_inherited_preferences(entry, forced, monkeypatch):
    from appMain import App
    from services.updater.checker import UpdateChecker
    network = MagicMock(side_effect=AssertionError('Product reached upstream channel'))
    monkeypatch.setattr(UpdateChecker, 'run_check', network)
    app = fake_app()
    getattr(App, entry)(app, **({'forced': forced} if entry != 'on_check_for_updates' else {}))
    app.lifecycle.version_check.assert_not_called()
    app.worker_task.emit.assert_not_called()
    app._queue_version_check.assert_not_called()
    network.assert_not_called()
    assert 'not available' in app.inform.emit.call_args.args[0]
    assert app.options['global_version_check'] is True


@pytest.mark.parametrize('entry,args', [('on_update_available', ({},)),
                                      ('_start_update_download', ({},)),
                                      ('on_update_staged', ({},)),
                                      ('on_revert_update', ()), ('prepare_update_files', ())])
def test_product_download_install_and_revert_entry_points_are_unavailable(entry, args, monkeypatch):
    from appMain import App
    launch = MagicMock(side_effect=AssertionError('Product launched upstream updater'))
    monkeypatch.setattr('appMain.launch_update', launch)
    monkeypatch.setattr('appMain.launch_rollback', launch)
    app = fake_app()
    getattr(App, entry)(app, *args)
    launch.assert_not_called()
    app.worker_task.emit.assert_not_called()
    app.quit_application.assert_not_called()
    assert 'not available' in app.inform.emit.call_args.args[0]


def test_update_controls_cannot_be_reenabled_by_restore_point():
    from appMain import App
    app = fake_app()
    control = MagicMock()
    app.ui = SimpleNamespace(menuhelp_check_updates=control, menuhelp_revert_update=control)
    app._load_rollback_restore_point = MagicMock(return_value=('restore', {'previous_version': '1.0'}))
    App.refresh_rollback_action(app)
    assert all(call.args == (False,) for call in control.setEnabled.call_args_list)
    assert 'not available' in control.setToolTip.call_args.args[0]
    app._load_rollback_restore_point.assert_not_called()


def test_preferences_update_controls_are_disabled_with_explanation(qapp):
    from appGUI.preferences.general.GeneralAppPrefGroupUI import GeneralAppPrefGroupUI
    from appGUI.preferences.OptionsGroupUI import OptionsGroupUI
    app = SimpleNamespace(decimals=4, options={'global_languages': ['English']})
    previous = OptionsGroupUI.app
    OptionsGroupUI.app = app
    try:
        group = GeneralAppPrefGroupUI(app)
    finally:
        OptionsGroupUI.app = previous
    for control in (group.version_check_cb, group.prepare_update_files_btn):
        assert not control.isEnabled()
        assert 'MikroCAM updates are not available' in control.toolTip()
    assert group.send_stats_cb.isEnabled()


def test_host_compatibility_versions_and_storage_names_are_preserved(tmp_path):
    from appMain import App
    assert App.version == 'Unstable' and App.version_date == '2026/5/01'
    app = SimpleNamespace(data_path=str(tmp_path), version=App.version)
    assert App.tools_database_path(app).endswith('tools_db_Unstable.FlatDB')
    assert App.defaults_path(app).endswith('current_defaults.FlatConfig')
