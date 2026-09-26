"""Verify the declared runtime policy against its pin and the running interpreter."""
from pathlib import Path
import platform
import struct
import sys
import sysconfig
import tomllib

from packaging.specifiers import SpecifierSet
from packaging.version import Version
import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def project():
    with (ROOT / 'pyproject.toml').open('rb') as source:
        return tomllib.load(source)['project']


def test_project_metadata_identifies_skeleton_without_replacing_requirements(project):
    assert project['name'] == 'mikrocam'
    from mikrocam.core.identity import VERSION
    version = Version(VERSION)
    assert 'version' not in project and project['dynamic'] == ['version']
    assert not version.is_prerelease and not version.is_devrelease
    assert not project.get('dependencies'), 'Pinned requirements remain authoritative'
    assert not project.get('optional-dependencies')


@pytest.mark.parametrize('version', ['3.13.0', '3.13.13', '3.13.99'])
def test_supported_minor_accepts_standard_patch_releases(project, version):
    assert Version(version) in SpecifierSet(project['requires-python'])


@pytest.mark.parametrize('version', ['3.12.99', '3.14.0', '4.0.0', '3.13.0rc1'])
def test_runtime_range_excludes_unvalidated_interpreters(project, version):
    assert Version(version) not in SpecifierSet(project['requires-python'])


def test_exact_python_pin_matches_metadata_and_standard_target_runtime(project):
    pin = Version((ROOT / '.python-version').read_text(encoding='utf-8').strip())
    assert len(pin.release) == 3 and pin.release[:2] == (3, 13)
    assert not pin.is_prerelease and not pin.is_devrelease
    assert pin in SpecifierSet(project['requires-python'])
    assert Version(platform.python_version()) == pin, 'Use the interpreter from .python-version'
    assert sys.implementation.name == 'cpython'
    assert not sysconfig.get_config_var('Py_GIL_DISABLED'), 'Free-threaded CPython is not certified'
    assert struct.calcsize('P') * 8 == 64
