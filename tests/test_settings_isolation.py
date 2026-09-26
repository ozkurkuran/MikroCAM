"""Named Qt settings must use the test sandbox rather than the Windows registry."""

from pathlib import Path

from PyQt6.QtCore import QSettings


def test_named_settings_stay_in_sandbox(pytestconfig):
    settings = QSettings('Open Source', 'FlatCAM_EVO')
    assert settings.format() == QSettings.Format.IniFormat
    assert Path(settings.fileName()).resolve().is_relative_to(
        Path(pytestconfig._settings_sandbox.name).resolve())
    settings.setValue('sandbox-regression-probe', 'isolated')
    settings.sync()
    assert QSettings('Open Source', 'FlatCAM_EVO').value('sandbox-regression-probe') == 'isolated'
    settings.remove('sandbox-regression-probe')


def test_settings_sandbox_does_not_change_global_default_format(pytestconfig):
    assert QSettings.defaultFormat() == pytestconfig._qsettings_default_format
