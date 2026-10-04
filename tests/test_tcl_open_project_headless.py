"""Tcl/CLI project opening must not block on the interactive "Import Settings" dialog.

The restore handler documents "Load by default new options when not using GUI", but its
condition showed the modal for every Tcl ``open_project`` (run_from_arg is False there).
Headless and startup-script runs then waited forever on an invisible dialog.
"""
from unittest.mock import Mock

import pytest

from appHandlers import appIO as io_module


def _handler():
    app = Mock()
    app.options = {'units': 'MM'}
    app.resource_location = 'assets/resources'
    handler = io_module.appIO.__new__(io_module.appIO)
    handler.app = app
    handler.log = Mock()
    handler.on_file_new_project = Mock()
    return handler, app


@pytest.fixture
def no_dialog(monkeypatch):
    created = []

    def refuse(*args, **kwargs):
        created.append(args)
        raise AssertionError('Import Settings dialog opened for a Tcl/CLI project')

    monkeypatch.setattr(io_module, 'FCMessageBox', refuse)
    return created


def test_tcl_open_project_loads_options_without_dialog(qapp, no_dialog):
    handler, app = _handler()
    project = {'options': {'units': 'IN'}, 'objs': []}
    handler.restore_project_handler(project, 'p.FlatPrj', False, True, True, False)
    assert not no_dialog
    assert app.options['units'] == 'IN'
    app.restore_project_objects_sig.emit.assert_called_once_with(project, 'p.FlatPrj', True, False)


def test_interactive_open_still_asks(qapp, monkeypatch):
    handler, app = _handler()
    asked = []

    class Box:
        def __init__(self, *args, **kwargs):
            asked.append(True)

        def __getattr__(self, name):
            return Mock()

        def clickedButton(self):
            return None

    monkeypatch.setattr(io_module, 'FCMessageBox', Box)
    handler.restore_project_handler({'options': {'units': 'IN'}, 'objs': []}, 'p.FlatPrj', False, False, False, True)
    assert asked == [True]
    assert app.options['units'] == 'MM'
