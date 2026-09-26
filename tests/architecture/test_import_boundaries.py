"""Executable examples of the constitutional dependency direction."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

from imports import check_source, scan_package


@pytest.mark.parametrize(('module', 'source'), [
    ('mikrocam.core.units', 'import math\nimport numpy as np\nfrom shapely import geometry'),
    ('mikrocam.core.units', 'from . import geometry\nfrom ..core import units'),
    ('mikrocam.laser.paths', 'from ..core import units\nfrom . import recipe'),
    ('mikrocam.bridge.gerber', 'from appObjects.GerberObject import GerberObject'),
    ('mikrocam.ui.panel', 'from PyQt6 import QtWidgets\nfrom ..laser import paths'),
    ('mikrocam.ui.panel', 'from ..bridge import gerber\nfrom ..core import units'),
    ('mikrocam.core', 'from . import units'),
    ('mikrocam.core.units', 'import importlib as i\ni.import_module("math")'),
    ('mikrocam.core.units', 'from importlib import import_module as im\nim(".units", "mikrocam.core")'),
    ('mikrocam.core.units', 'text = "import appMain"'),
])
def test_allowed_dependencies(module, source):
    assert check_source(source, module, is_package=module == 'mikrocam.core') == []


@pytest.mark.parametrize(('module', 'source', 'target'), [
    ('mikrocam.core.units', 'import PyQt6.QtCore', 'PyQt6'),
    ('mikrocam.core.units', 'from appMain import App', 'appMain'),
    ('mikrocam.core.units', 'import scipy', 'scipy'),
    ('mikrocam.core.units', 'import socket', 'socket'),
    ('mikrocam.core.units', 'import subprocess', 'subprocess'),
    ('mikrocam.core.units', 'from mikrocam import bridge', 'bridge'),
    ('mikrocam.core.units', 'from .. import ui', 'ui'),
    ('mikrocam.core.units', 'from ..laser import paths', 'laser'),
    ('mikrocam.laser.paths', 'from ..machine import status', 'machine'),
    ('mikrocam.laser.paths', 'from PyQt6 import QtCore', 'PyQt6'),
    ('mikrocam.laser.paths', 'from camlib import Geometry', 'camlib'),
    ('mikrocam.laser.paths', 'import scipy', 'scipy'),
    ('mikrocam.laser.paths', 'import numpy', 'numpy'),
    ('mikrocam.laser.paths', 'import shapely', 'shapely'),
    ('mikrocam.machine.controller', 'import serial', 'serial'),
    ('mikrocam.laser.paths', 'import requests', 'requests'),
    ('mikrocam.bridge.gerber', 'from ..ui import panel', 'ui'),
    ('mikrocam.ui.panel', 'import appMain', 'appMain'),
    ('mikrocam.ui.panel', 'from libs import qdarktheme', 'libs'),
    ('mikrocam', 'import mikrocam.core', 'core'),
    ('mikrocam.core.units', 'from ... import appMain', 'relative'),
    ('mikrocam.core.units', 'if TYPE_CHECKING:\n    import appMain', 'appMain'),
    ('mikrocam.core.units', 'import importlib as i\ni.import_module("appMain")', 'appMain'),
    ('mikrocam.core.units', 'from importlib import import_module as im\nim("..ui", "mikrocam.core")', 'ui'),
    ('mikrocam.core.units', '__import__("appMain")', 'appMain'),
    ('mikrocam.core.units', '__import__("mikrocam", fromlist=["bridge"])', 'bridge'),
    ('mikrocam.core.units', '__import__("mikrocam", fromlist=names)', 'dynamic'),
    ('mikrocam.core.units', '__import__("mikrocam", {}, {}, ["ui"])', 'ui'),
    ('mikrocam.core.units', 'from builtins import __import__ as load\nload("appMain")', 'appMain'),
    ('mikrocam.core.units', 'import importlib\nimportlib.import_module(name)', 'dynamic'),
    ('mikrocam.core.units', '__import__(target)', 'dynamic'),
    ('mikrocam.core.units', 'import importlib\nimportlib.import_module(".units", package)', 'dynamic'),
])
def test_forbidden_dependencies(module, source, target):
    errors = check_source(source, module)
    assert errors, source
    assert any(target in error for error in errors)
    assert all(f'{module}:' in error for error in errors)


def test_package_initializer_and_nested_files_are_checked(tmp_path):
    core = tmp_path / 'mikrocam' / 'core'
    core.mkdir(parents=True)
    (core / '__init__.py').write_text('from .. import bridge\n', encoding='utf8')
    assert 'bridge' in '\n'.join(scan_package(tmp_path / 'mikrocam'))


def test_syntax_errors_have_source_location(tmp_path):
    package = tmp_path / 'mikrocam'
    package.mkdir()
    (package / '__init__.py').write_text('import (', encoding='utf8')
    assert 'syntax' in '\n'.join(scan_package(package)).lower()


def test_real_package_obeys_boundaries():
    root = Path(__file__).resolve().parents[2]
    package = root / 'mikrocam'
    assert (package / 'core' / '__init__.py').is_file(), 'core skeleton is required'
    assert scan_package(package) == []


def test_core_import_has_no_desktop_or_host_side_effects():
    root = Path(__file__).resolve().parents[2]
    code = ('import sys; import mikrocam.core; '
            'assert not any(n.startswith(("PyQt", "vispy", "appMain", "camlib")) '
            'for n in sys.modules)')
    env = {key: value for key, value in os.environ.items() if key != 'PYTHONPATH'}
    result = subprocess.run([sys.executable, '-S', '-c', code], cwd=root, env=env,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
