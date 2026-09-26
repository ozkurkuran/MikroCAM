"""Force real QSettings storage into a test directory, including named overloads."""

from pathlib import Path
import re

from PyQt6 import QtCore


def install_settings_sandbox(directory):
    original = QtCore.QSettings
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    class SandboxedSettings(original):
        def __init__(self, *args, **kwargs):
            # Use the filename overload without changing Qt's global format/paths.
            if args and isinstance(args[0], original.Scope):
                args = args[1:]
            if not args:
                args = (QtCore.QCoreApplication.organizationName() or 'tests',
                        QtCore.QCoreApplication.applicationName() or 'application')
            if isinstance(args[0], str) and (len(args) == 1 or isinstance(args[1], str)):
                organization, application = args[0], args[1] if len(args) > 1 else 'application'
                filename = re.sub(r'[^A-Za-z0-9_.-]', '_', f'{organization}-{application}') + '.ini'
                args = (str(directory / filename), original.Format.IniFormat, *args[2:])
            super().__init__(*args, **kwargs)
            assert self.format() == original.Format.IniFormat, 'Native settings forbidden in tests'
            self.setFallbacksEnabled(False)

    QtCore.QSettings = SandboxedSettings
    probe = SandboxedSettings('Open Source', 'FlatCAM_EVO')
    assert probe.format() == original.Format.IniFormat
    return original
