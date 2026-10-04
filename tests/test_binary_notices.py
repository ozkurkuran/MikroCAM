"""Notices for the Windows binary: build tools, CPython, Qt third-party code, NSIS and assets."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / 'THIRD_PARTY_LICENSES' / 'inventory.json'
PROVENANCE = ROOT / 'THIRD_PARTY_LICENSES' / 'inherited-assets' / 'provenance.json'
SHIPPED_ASSETS = ('assets/resources', 'assets/examples', 'assets/icon.png')


@pytest.fixture(scope='module')
def inventory():
    return json.loads(INVENTORY.read_text(encoding='utf-8'))


def _text(item, role='license'):
    return '\n'.join((ROOT / f['path']).read_text(encoding='utf-8', errors='replace')
                     for f in item['files'] if f['role'] == role)


def _pins(filename):
    pins = {}
    for line in (ROOT / filename).read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==(\S+)', line.strip())
        if match:
            pins[re.sub(r'[-_.]+', '-', match[1]).lower()] = match[2]
    return pins


def test_build_tools_are_pinned_and_inventoried_with_bootloader_exception(inventory):
    pins = _pins('requirements-build.txt')
    assert pins == {'altgraph': '0.17.5', 'pefile': '2024.8.26', 'pyinstaller': '6.22.3',
                    'pyinstaller-hooks-contrib': '2026.8', 'pywin32-ctypes': '0.2.3'}
    packages = {item['name']: item for item in inventory['dependencies']}
    for name, version in pins.items():
        assert packages[name]['version'] == version and packages[name]['groups'] == ['build']
    assert 'Bootloader Exception' in _text(packages['pyinstaller'])


def test_cpython_windows_runtime_notice_is_retained(inventory):
    cpython = next(item for item in inventory['components'] if item['name'] == 'cpython')
    version = (ROOT / '.python-version').read_text(encoding='utf-8').strip()
    assert cpython['version'] == version
    assert cpython['source']['url'] == f'https://www.python.org/ftp/python/{version}/python-{version}-amd64.exe'
    text = _text(cpython)
    assert 'PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2' in text
    assert 'Additional Conditions for this Windows binary build' in text
    assert 'Microsoft Distributable Code' in text and 'libbzip2' in text


def test_qt_third_party_attributions_match_the_pinned_qt_wheel(inventory):
    qt = next(item for item in inventory['components'] if item['name'] == 'qt-third-party')
    assert qt['version'] == _pins('requirements.txt')['pyqt6-qt6']
    pages = {Path(f['path']).name: f for f in qt['files']}
    index = (ROOT / pages['licenses-used-in-qt.html']['path']).read_text(encoding='utf-8')
    assert f"Qt {qt['version']}" in index
    names = ' '.join(pages)
    for fragment in ('pdfium', 'pcre2', 'freetype', 'harfbuzz', 'libpng', 'libjpeg', 'zlib', 'llvmpipe'):
        assert fragment in names.lower(), fragment
    assert all(f['source'].startswith('https://doc.qt.io/qt-6.11/') for f in qt['files'])


def test_nsis_installer_stub_notice_is_retained(inventory):
    nsis = next(item for item in inventory['components'] if item['name'] == 'nsis')
    assert nsis['version'] == '3.12'
    text = _text(nsis)
    assert 'zlib/libpng license' in text


def _shipped_asset_files():
    files = []
    for entry in SHIPPED_ASSETS:
        path = ROOT / entry
        files += [path] if path.is_file() else sorted(p for p in path.rglob('*') if p.is_file())
    return {p.relative_to(ROOT).as_posix(): p for p in files}


def test_inherited_assets_have_per_file_upstream_provenance():
    record = json.loads(PROVENANCE.read_text(encoding='utf-8'))
    assert record['schema_version'] == 1
    entries = {item['path']: item for item in record['files']}
    shipped = _shipped_asset_files()
    assert set(entries) == set(shipped)
    for path, file in shipped.items():
        item = entries[path]
        assert item['sha256'] == hashlib.sha256(file.read_bytes()).hexdigest(), path
        assert re.fullmatch(r'[0-9a-f]{40}', item['added_commit']) and item['added_author']
        assert re.fullmatch(r'[0-9a-f]{40}', item['last_commit']) and item['last_author']
        assert item['origin'] in {'flatcam-upstream', 'mikrocam'}


def test_provenance_commits_exist_in_history():
    record = json.loads(PROVENANCE.read_text(encoding='utf-8'))
    commits = sorted({item['added_commit'] for item in record['files']} |
                     {item['last_commit'] for item in record['files']})
    result = subprocess.run(['git', 'cat-file', '--batch-check'], cwd=ROOT, input='\n'.join(commits) + '\n',
                            capture_output=True, text=True)
    if result.returncode or 'fatal' in result.stderr:
        pytest.skip('git history unavailable')
    missing = [line for line in result.stdout.splitlines() if line.endswith('missing')]
    assert not missing, missing[:5]


def test_binary_audit_gaps_state_windows_distribution(inventory):
    gaps = {gap['component']: gap for gap in inventory['audit_gaps']}
    assert gaps['rasterio']['windows_binary'] == 'excluded'
    assert gaps['ortools']['windows_binary'] == 'excluded' and 'EPL-2.0' in gaps['ortools']['detail']
    assert gaps['inherited-assets']['status'] == 'upstream-provenance-recorded'
    assert gaps['inherited-assets']['windows_binary'] == 'shipped-with-credits-and-provenance'
    assert gaps['resvg-py']['windows_binary'] == 'shipped-with-crate-notices'
    assert gaps['qt-third-party']['windows_binary'] == 'shipped-with-attributions'
    assert gaps['microsoft-runtime']['windows_binary'] == 'shipped-with-distributable-code-terms'


def test_binary_notice_names_pinned_sources_and_identity():
    from mikrocam.core import identity
    text = (ROOT / 'release' / 'windows' / 'NOTICE-BINARY.txt').read_text(encoding='utf-8')
    runtime = _pins('requirements.txt')
    assert f"PyQt6 {runtime['pyqt6']}" in text and f"Qt {runtime['pyqt6-qt6']}" in text
    assert 'GNU General Public' in text and 'version 3' in text
    assert identity.REPOSITORY_URL in text and 'Microsoft Distributable Code' in text
    assert 'OR-Tools' in text and 'not code-signed' in text
    notice = (ROOT / 'NOTICE.md').read_text(encoding='utf-8')
    assert '## Windows binary distribution' in notice
