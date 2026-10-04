"""Pure Windows release layout rules; no PyInstaller, NSIS, Qt or network is needed."""
import hashlib
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'release' / 'windows'))
import release_layout as layout  # noqa: E402
from mikrocam.core import identity  # noqa: E402


def test_artifact_names_and_version_come_from_identity():
    names = layout.artifact_names(identity.NAME, identity.VERSION)
    assert names == {
        'folder': 'MikroCAM',
        'zip': f'MikroCAM-{identity.VERSION}-win64-portable.zip',
        'setup': f'MikroCAM-{identity.VERSION}-win64-setup.exe',
        'checksums': f'MikroCAM-{identity.VERSION}-SHA256SUMS.txt',
    }


@pytest.mark.parametrize('version,expected', [('0.1.0', (0, 1, 0, 0)), ('12.3.45', (12, 3, 45, 0))])
def test_windows_version_tuple(version, expected):
    assert layout.version_tuple(version) == expected


@pytest.mark.parametrize('version', ['0.1', '0.1.0rc1', '1.2.3.4', 'v1.2.3', '1.2.70000'])
def test_windows_version_tuple_rejects_non_release_versions(version):
    with pytest.raises(ValueError):
        layout.version_tuple(version)


def test_version_resource_is_valid_python_with_identity_strings():
    text = layout.version_resource(identity)
    compile(text, 'version_info.txt', 'eval')
    for value in (identity.NAME, identity.VERSION, identity.COPYRIGHT, 'MikroCAM.exe', '0, 1, 0, 0'):
        assert value in text


def _parse_like_launcher(text):
    """Mirror flatcam.py's configuration parser without importing the GUI."""
    values = {}
    for line in text.splitlines(keepends=True):
        param = str(line).replace('\n', '').rpartition('=')
        values[param[0]] = eval(param[2])
    return values


@pytest.mark.parametrize('portable', [True, False])
def test_configuration_is_understood_by_the_launcher(portable):
    assert _parse_like_launcher(layout.configuration_text(portable)) == {'portable': portable, 'headless': False}


@pytest.mark.parametrize('destination,excluded', [
    ('OpenGL/DLLS/freeglut64.vc14.dll', True), ('OpenGL\\DLLS\\gle64.vc10.dll', True),
    ('MSVCR100.dll', True), ('msvcr90.dll', True), ('_internal/MSVCR100.dll', True),
    ('_internal/OpenGL/DLLS/gle64.vc14.dll', True), ('api-ms-win-crt-heap-l1-1-0.dll', True),
    ('ucrtbase.dll', True), ('libssl-3-x64.dll', True),
    ('PyQt6/Qt6/bin/Qt6Core.dll', False), ('libcrypto-3.dll', False), ('VCRUNTIME140.dll', False),
])
def test_excluded_destinations(destination, excluded):
    assert layout.is_excluded_destination(destination) is excluded


def _tree(tmp_path):
    root = tmp_path / 'payload'
    (root / '_internal' / 'assets').mkdir(parents=True)
    (root / 'MikroCAM.exe').write_bytes(b'exe')
    (root / '_internal' / 'assets' / 'icon.png').write_bytes(b'png')
    (root / '_internal' / 'z.txt').write_text('z', encoding='utf-8')
    return root


def test_deterministic_zip_is_byte_identical_and_rooted(tmp_path):
    root = _tree(tmp_path)
    first, second = tmp_path / 'a.zip', tmp_path / 'b.zip'
    names = layout.write_deterministic_zip(root, first, 'MikroCAM', 1700000000)
    (root / 'MikroCAM.exe').touch()  # filesystem time must not leak into the archive
    layout.write_deterministic_zip(root, second, 'MikroCAM', 1700000000)
    assert first.read_bytes() == second.read_bytes()
    assert names == ['MikroCAM/MikroCAM.exe', 'MikroCAM/_internal/assets/icon.png', 'MikroCAM/_internal/z.txt']
    with zipfile.ZipFile(first) as archive:
        assert archive.namelist() == names
        assert archive.read('MikroCAM/_internal/assets/icon.png') == b'png'
        assert {info.date_time for info in archive.infolist()} == {(2023, 11, 14, 22, 13, 20)}


def test_deterministic_zip_adds_generated_files_in_sorted_order(tmp_path):
    root = _tree(tmp_path)
    archive_path = tmp_path / 'c.zip'
    names = layout.write_deterministic_zip(root, archive_path, 'MikroCAM', 1700000000,
                                           extra={'config/configuration.txt': b'portable=True\n'})
    assert names[0] == 'MikroCAM/MikroCAM.exe' and 'MikroCAM/config/configuration.txt' in names
    assert names == sorted(names)
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.read('MikroCAM/config/configuration.txt') == b'portable=True\n'
    with pytest.raises(ValueError, match='already in payload'):
        layout.write_deterministic_zip(root, tmp_path / 'd.zip', 'MikroCAM', 1700000000,
                                       extra={'MikroCAM.exe': b'other'})


def test_deterministic_zip_rejects_symlink_or_escape(tmp_path):
    root = _tree(tmp_path)
    with pytest.raises(ValueError):
        layout.write_deterministic_zip(root, tmp_path / 'x.zip', '../MikroCAM', 1700000000)


def test_uninstall_script_removes_only_listed_files_deepest_directories_first():
    script = layout.uninstall_script(['MikroCAM.exe', '_internal/a/b/c.dll', '_internal/a/d.txt'])
    lines = script.splitlines()
    assert 'Delete "$INSTDIR\\MikroCAM.exe"' in lines
    assert 'Delete "$INSTDIR\\_internal\\a\\b\\c.dll"' in lines
    dirs = [line for line in lines if line.startswith('RMDir')]
    assert dirs == ['RMDir "$INSTDIR\\_internal\\a\\b"', 'RMDir "$INSTDIR\\_internal\\a"',
                    'RMDir "$INSTDIR\\_internal"']
    assert '/r' not in script


@pytest.mark.parametrize('path', ['/abs.dll', 'C:/x.dll', '../x.dll', 'a/../../x', 'a"b.dll', 'a$b.dll'])
def test_uninstall_script_rejects_unsafe_paths(path):
    with pytest.raises(ValueError):
        layout.uninstall_script([path])


def test_nsis_defines_come_from_identity(tmp_path):
    defines = layout.nsis_defines(identity, tmp_path / 'payload', tmp_path / 'setup.exe',
                                  tmp_path / 'uninstall.nsh', tmp_path / 'license.txt', tmp_path / 'app.ico')
    assert defines['APP_NAME'] == identity.NAME
    assert defines['APP_VERSION'] == identity.VERSION
    assert defines['VI_VERSION'] == '.'.join(map(str, layout.version_tuple(identity.VERSION)))
    assert defines['PUBLISHER'] == identity.PUBLISHER == 'MikroCAM contributors'
    assert defines['URL'] == identity.REPOSITORY_URL
    assert defines['APP_EXE'] == 'MikroCAM.exe'
    assert defines['REG_KEY'] == 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\MikroCAM'
    assert all('"' not in value for value in defines.values())


# ---------------------------------------------------------------- bundle manifest

def _roots(tmp_path):
    roots = {name: tmp_path / name for name in ('repo', 'base', 'site', 'work')}
    for path in roots.values():
        path.mkdir()
    return roots


def _file(path, data=b'x'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _licenses():
    return {'mikrocam': ['LICENSE'], 'assets': ['NOTICE.md'], 'cpython': ['licenses/cpython/LICENSE.txt'],
            'pyinstaller-generated': ['licenses/pyinstaller/COPYING.txt'],
            'numpy': ['licenses/numpy/LICENSE.txt'], 'ortools': ['licenses/ortools/LICENSE'],
            'qdarktheme': ['licenses/vendored/qdarktheme/LICENSE.txt'],
            'descartes': ['licenses/vendored/descartes/LICENSE']}


def test_manifest_maps_every_file_to_a_licensed_owner(tmp_path):
    roots = _roots(tmp_path)
    numpy_file = _file(roots['site'] / 'numpy' / '_core.pyd', b'numpy')
    files = [
        ('MikroCAM.exe', _file(roots['work'] / 'MikroCAM.exe')),
        ('python313.dll', _file(roots['base'] / 'python313.dll')),
        ('numpy/_core.pyd', numpy_file),
        ('assets/resources/a.png', _file(roots['repo'] / 'assets' / 'resources' / 'a.png')),
        ('preprocessors/GRBL_11.py', _file(roots['repo'] / 'preprocessors' / 'GRBL_11.py')),
        ('pyz/libs.qdarktheme.main', _file(roots['repo'] / 'libs' / 'qdarktheme' / 'main.py')),
        ('pyz/descartes.patch', _file(roots['repo'] / 'descartes' / 'patch.py')),
    ]
    records = {numpy_file.resolve(): 'numpy'}
    manifest = layout.build_manifest(files, roots, records, _licenses(), excluded=frozenset({'ortools'}))
    assert manifest['schema_version'] == 1
    owners = {entry['path']: entry['owner'] for entry in manifest['files']}
    assert owners == {'MikroCAM.exe': 'pyinstaller-generated', 'python313.dll': 'cpython',
                      'numpy/_core.pyd': 'numpy', 'assets/resources/a.png': 'assets',
                      'preprocessors/GRBL_11.py': 'mikrocam', 'pyz/libs.qdarktheme.main': 'qdarktheme',
                      'pyz/descartes.patch': 'descartes'}
    assert [entry['path'] for entry in manifest['files']] == sorted(owners)
    entry = next(e for e in manifest['files'] if e['path'] == 'numpy/_core.pyd')
    assert entry['sha256'] == hashlib.sha256(b'numpy').hexdigest()
    assert manifest['owners']['numpy'] == {'files': 1, 'licenses': ['licenses/numpy/LICENSE.txt']}


def test_manifest_rejects_files_from_outside_allowed_roots(tmp_path):
    roots = _roots(tmp_path)
    stray = _file(tmp_path / 'Program Files' / 'UVtools' / 'helper.dll')
    with pytest.raises(layout.BundleError, match='outside allowed roots'):
        layout.build_manifest([('helper.dll', stray)], roots, {}, _licenses(), excluded=frozenset())


def test_manifest_rejects_unmapped_site_packages_file(tmp_path):
    roots = _roots(tmp_path)
    orphan = _file(roots['site'] / 'mystery' / 'x.pyd')
    with pytest.raises(layout.BundleError, match='no installed distribution'):
        layout.build_manifest([('mystery/x.pyd', orphan)], roots, {}, _licenses(), excluded=frozenset())


def test_manifest_rejects_owner_without_license(tmp_path):
    roots = _roots(tmp_path)
    item = _file(roots['site'] / 'nolicense' / 'x.pyd')
    with pytest.raises(layout.BundleError, match='no license'):
        layout.build_manifest([('nolicense/x.pyd', item)], roots, {item.resolve(): 'nolicense'},
                              _licenses(), excluded=frozenset())


def test_manifest_rejects_excluded_distribution(tmp_path):
    roots = _roots(tmp_path)
    item = _file(roots['site'] / 'ortools' / '.libs' / 'ortools.dll')
    with pytest.raises(layout.BundleError, match='excluded'):
        layout.build_manifest([('ortools/.libs/ortools.dll', item)], roots, {item.resolve(): 'ortools'},
                              _licenses(), excluded=frozenset({'ortools'}))


def test_manifest_rejects_excluded_destination(tmp_path):
    roots = _roots(tmp_path)
    item = _file(roots['base'] / 'MSVCR100.dll')
    with pytest.raises(layout.BundleError, match='excluded destination'):
        layout.build_manifest([('MSVCR100.dll', item)], roots, {}, _licenses(), excluded=frozenset())


def test_manifest_rejects_duplicate_destinations(tmp_path):
    roots = _roots(tmp_path)
    item = _file(roots['base'] / 'python313.dll')
    with pytest.raises(layout.BundleError, match='duplicate'):
        layout.build_manifest([('python313.dll', item), ('PYTHON313.DLL', item)], roots, {},
                              _licenses(), excluded=frozenset())


def test_binary_excluded_distributions_cover_optional_image_and_gpl_incompatible_packages():
    assert {'rasterio', 'svgtrace', 'playwright', 'ortools', 'pytest'} <= layout.EXCLUDED_DISTRIBUTIONS
    assert 'pyinstaller' not in layout.EXCLUDED_DISTRIBUTIONS, 'bootloader/runtime hooks are shipped'
    assert {'rasterio', 'svgtrace', 'playwright', 'ortools', 'pytest'} <= set(layout.EXCLUDED_MODULES)
