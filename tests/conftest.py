"""Keep the unit-test process away from real application settings."""

import os
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ['QT_API'] = 'pyqt6'


def pytest_configure(config):
    from PyQt6.QtCore import QSettings
    from qt_settings_sandbox import install_settings_sandbox
    config._qsettings_default_format = QSettings.defaultFormat()
    sandbox = tempfile.TemporaryDirectory(prefix='mikrocam-pytest-')
    config._settings_sandbox = sandbox
    config._original_appdata = os.environ.get('APPDATA')
    os.environ['APPDATA'] = sandbox.name
    config._original_qsettings = install_settings_sandbox(sandbox.name)


def pytest_unconfigure(config):
    from PyQt6 import QtCore
    QtCore.QSettings = config._original_qsettings
    original = config._original_appdata
    if original is None:
        os.environ.pop('APPDATA', None)
    else:
        os.environ['APPDATA'] = original
    config._settings_sandbox.cleanup()
