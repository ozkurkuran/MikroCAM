"""Product presentation must share one identity without changing host formats."""
import html
from pathlib import Path
import subprocess
import sys
import tomllib
from types import SimpleNamespace
from unittest.mock import MagicMock

from PyQt6 import QtGui, QtWidgets


ROOT = Path(__file__).resolve().parents[1]


def test_core_identity_is_available_without_site_or_desktop_modules():
    code = ('import sys; from mikrocam.core.identity import NAME, VERSION; '
            'assert (NAME, VERSION) == ("MikroCAM", "0.1.0"); '
            'assert not any(n.startswith(("PyQt", "vispy", "appMain", "camlib")) '
            'for n in sys.modules)')
    result = subprocess.run([sys.executable, '-S', '-c', code], cwd=ROOT,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr


def test_metadata_version_points_to_authoritative_identity():
    from mikrocam.core import identity
    metadata = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    assert 'version' not in metadata['project']
    assert metadata['project']['dynamic'] == ['version']
    assert metadata['tool']['setuptools']['dynamic']['version']['attr'] == 'mikrocam.core.identity.VERSION'
    assert identity.VERSION == '0.1.0'


def test_product_help_links_use_authoritative_repository_and_issues():
    from appMain import App
    from mikrocam.core import identity
    assert App.app_url == identity.REPOSITORY_URL
    assert App.bug_report_url == identity.ISSUES_URL


def test_titles_preserve_project_names_as_plain_text():
    from mikrocam.ui.identity import window_title
    project = '<board & "revision">.FlatPrj'
    assert window_title(architecture='64bit').startswith('MikroCAM 0.1.0')
    title = window_title(project, engine='3D', architecture='64bit')
    assert title.startswith('MikroCAM 0.1.0') and title.endswith(project)
    assert '[3D]' in title


def test_reopened_title_uses_product_version_not_host_compatibility_version():
    from appGUI.MainGUI import MainGUI
    ui = SimpleNamespace(app=SimpleNamespace(use_3d_engine=True, version='Unstable', beta=True),
                         setWindowTitle=MagicMock())
    MainGUI.set_ui_title(ui, 'board.FlatPrj')
    title = ui.setWindowTitle.call_args.args[0]
    assert title.startswith('MikroCAM 0.1.0') and title.endswith('board.FlatPrj')
    assert 'Unstable' not in title


def test_about_contains_product_links_license_and_upstream_credits(qapp, monkeypatch):
    from appHandlers.appUIActions import AppUIActions
    from mikrocam.core import identity
    ui = QtWidgets.QWidget()
    ui.app_icon = QtGui.QIcon()
    app = SimpleNamespace(ui=ui, log=MagicMock(), inform=MagicMock(), options={},
                          defaults=SimpleNamespace(report_usage=MagicMock()), version='Unstable',
                          version_date='2026/5/01', beta=True, resource_location=str(ROOT / 'assets/resources'))
    texts = []
    def inspect(dialog):
        texts.extend(label.text() for label in dialog.findChildren(QtWidgets.QLabel))
        return 0
    monkeypatch.setattr(QtWidgets.QDialog, 'exec', inspect)
    AppUIActions(app).on_about()
    text = html.unescape('\n'.join(texts))
    assert identity.NAME in text and identity.VERSION in text
    assert identity.REPOSITORY_URL in text and identity.ISSUES_URL in text and identity.RELEASES_URL in text
    assert 'Juan Pablo Caram' in text and 'Marius Stanciu' in text
    assert all(name.lower() in text.lower() for name in ('Freepik', 'Pixel perfect', 'Anggara', 'Kharisma'))
    assert all(copyright in text for copyright in identity.UPSTREAM_COPYRIGHTS)
    assert 'GPLv3' in text
    assert 'MIT' in text and 'Unstable' not in text


def test_shell_banner_uses_product_identity(qapp):
    from appGUI.GUIElements import _BrowserTextEdit
    browser = _BrowserTextEdit(version='Unstable')
    browser.clear()
    assert 'MikroCAM 0.1.0' in browser.toPlainText()
    assert 'Unstable' not in browser.toPlainText()
