"""Pure Windows release layout rules shared by the PyInstaller spec, build script and tests.

Standard library only. Nothing here imports the application, Qt, PyInstaller or NSIS.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import time
import zipfile

SCHEMA_VERSION = 1
APP_EXE = 'MikroCAM.exe'
SMOKE_EXE = 'MikroCAMSmoke.exe'
UNINSTALLER_EXE = 'Uninstall.exe'

# Optional image tools, the test stack and OR-Tools (EPL-2.0 Coin-OR linked into ortools.dll,
# incompatible with distributing alongside GPLv3 PyQt6) never enter the Windows binary.
EXCLUDED_DISTRIBUTIONS = frozenset({
    'rasterio', 'affine', 'svgtrace', 'playwright', 'install-playwright', 'pyee', 'greenlet',
    'ortools', 'absl-py', 'immutabledict', 'pytest', 'pytest-qt', 'pluggy', 'iniconfig',
    'pyinstaller-hooks-contrib', 'altgraph', 'pefile', 'pywin32-ctypes',
})
# Source-vendored components keep their own notices (THIRD_PARTY_LICENSES/vendored).
VENDORED_PREFIXES = (('libs/qdarktheme/', 'qdarktheme'), ('descartes/', 'descartes'))
EXCLUDED_MODULES = (
    'rasterio', 'affine', 'svgtrace', 'playwright', 'install_playwright', 'pyee', 'greenlet',
    'ortools', 'absl', 'immutabledict', 'pytest', '_pytest', 'pytestqt', 'pluggy', 'iniconfig',
    'PyInstaller', 'altgraph', 'pefile', 'win32ctypes',
)

# Repository data copied next to the frozen modules (source, destination).
DATA_ENTRIES = (
    ('assets/resources', 'assets/resources'),
    ('assets/examples', 'assets/examples'),
    ('assets/icon.png', 'assets'),
    ('locale', 'locale'),
    ('preprocessors', 'preprocessors'),
)

_EXCLUDED_DESTINATION = re.compile(
    r'^(?:_internal/)?(opengl/dlls/.*|msvcr\d+\.dll|api-ms-win-.*\.dll|ucrtbase\.dll|libssl-3-x64\.dll|libcrypto-3-x64\.dll)$',
    re.IGNORECASE)
_RELEASE_VERSION = re.compile(r'(\d+)\.(\d+)\.(\d+)')
_SAFE_RELATIVE = re.compile(r'^[^"$<>|*?:]+$')
_REGISTRY_UNINSTALL = 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\'


class BundleError(RuntimeError):
    """A frozen payload would ship an unmapped, unlicensed or excluded file."""


def artifact_names(name: str, version: str) -> dict[str, str]:
    """Return release folder and artifact file names for one product version."""
    version_tuple(version)
    return {'folder': name, 'zip': f'{name}-{version}-win64-portable.zip',
            'setup': f'{name}-{version}-win64-setup.exe', 'checksums': f'{name}-{version}-SHA256SUMS.txt'}


def version_tuple(version: str) -> tuple[int, int, int, int]:
    """Convert a strict X.Y.Z release version into a Windows four-part file version."""
    match = _RELEASE_VERSION.fullmatch(version)
    if not match:
        raise ValueError(f'Windows release version must be X.Y.Z: {version!r}')
    parts = tuple(int(part) for part in match.groups())
    if any(part > 65535 for part in parts):
        raise ValueError(f'Windows version component exceeds 65535: {version!r}')
    return (*parts, 0)


def version_resource(identity) -> str:
    """Return a PyInstaller VSVersionInfo expression for the GUI executable."""
    numbers = version_tuple(identity.VERSION)
    dotted = '.'.join(map(str, numbers))
    strings = (('CompanyName', identity.PUBLISHER), ('FileDescription', identity.NAME),
               ('FileVersion', dotted), ('InternalName', identity.NAME),
               ('LegalCopyright', identity.COPYRIGHT), ('OriginalFilename', APP_EXE),
               ('ProductName', identity.NAME), ('ProductVersion', identity.VERSION))
    entries = ',\n          '.join(f'StringStruct({key!r}, {value!r})' for key, value in strings)
    return (f'VSVersionInfo(\n  ffi=FixedFileInfo(filevers={numbers}, prodvers={numbers}, mask=0x3f, flags=0x0,\n'
            f'    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),\n'
            f'  kids=[StringFileInfo([StringTable(\'040904B0\', [\n          {entries}])]),\n'
            f'        VarFileInfo([VarStruct(\'Translation\', [1033, 1200])])])\n')


def configuration_text(portable: bool) -> str:
    """Return config/configuration.txt understood by flatcam.py and appLifecycle."""
    return f'portable={bool(portable)}\nheadless=False\n'


def is_excluded_destination(destination: str) -> bool:
    """Reject legacy GLUT/GLE DLLs, old MSVC runtimes and PATH-leaked system libraries."""
    return bool(_EXCLUDED_DESTINATION.match(destination.replace('\\', '/')))


def _relative(path: str) -> PurePosixPath:
    text = path.replace('\\', '/')
    pure = PurePosixPath(text)
    if (not text or pure.is_absolute() or re.match(r'^[A-Za-z]:', text) or '..' in pure.parts
            or not _SAFE_RELATIVE.match(text)):
        raise ValueError(f'Unsafe payload path: {path!r}')
    return pure


def payload_files(directory: Path) -> list[str]:
    """Return sorted POSIX relative regular files; symbolic links are refused."""
    directory = Path(directory)
    files = []
    for path in directory.rglob('*'):
        if path.is_symlink():
            raise ValueError(f'Symbolic link in payload: {path}')
        if path.is_file():
            files.append(path.relative_to(directory).as_posix())
    return sorted(files)


def write_deterministic_zip(directory: Path, zip_path: Path, root_name: str, timestamp: int,
                            extra: dict[str, bytes] | None = None) -> list[str]:
    """Write a byte-reproducible ZIP below one root folder and return its member names.

    ``extra`` adds generated files (for example the portable configuration) that are not in
    the shared payload directory; it may not replace a payload file.
    """
    if '/' in root_name or '\\' in root_name or root_name in {'', '.', '..'}:
        raise ValueError(f'Invalid archive root: {root_name!r}')
    stamp = time.gmtime(max(int(timestamp), 315532800))[:6]
    members = {relative: Path(directory) / relative for relative in payload_files(directory)}
    for relative, data in (extra or {}).items():
        relative = str(_relative(relative))
        if relative in members:
            raise ValueError(f'{relative} is already in payload')
        members[relative] = bytes(data)
    names = []
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in sorted(members):
            name = f'{root_name}/{_relative(relative)}'
            info = zipfile.ZipInfo(name, date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            source = members[relative]
            data = source if isinstance(source, bytes) else source.read_bytes()
            archive.writestr(info, data, compresslevel=9)
            names.append(name)
    return names


def uninstall_script(files: list[str]) -> str:
    """Return NSIS lines deleting exactly the installed files and their now-empty directories."""
    lines, directories = [], set()
    for item in sorted(files):
        relative = _relative(item)
        lines.append('Delete "$INSTDIR\\%s"' % '\\'.join(relative.parts))
        directories.update(relative.parents)
    directories.discard(PurePosixPath('.'))
    for directory in sorted(directories, key=lambda d: (-len(d.parts), str(d))):
        lines.append('RMDir "$INSTDIR\\%s"' % '\\'.join(directory.parts))
    return '\n'.join(lines) + '\n'


def nsis_defines(identity, payload: Path, setup: Path, uninstall_list: Path, license_text: Path,
                 icon: Path) -> dict[str, str]:
    """Return makensis /D values; all product identity comes from the identity module."""
    defines = {
        'APP_NAME': identity.NAME, 'APP_VERSION': identity.VERSION,
        'VI_VERSION': '.'.join(map(str, version_tuple(identity.VERSION))),
        'PUBLISHER': identity.PUBLISHER, 'COPYRIGHT': identity.COPYRIGHT,
        'URL': identity.REPOSITORY_URL, 'HELP_URL': identity.ISSUES_URL,
        'APP_EXE': APP_EXE, 'UNINSTALLER': UNINSTALLER_EXE,
        'REG_KEY': _REGISTRY_UNINSTALL + identity.NAME,
        'SOURCE_DIR': str(Path(payload)), 'OUTFILE': str(Path(setup)),
        'UNINSTALL_LIST': str(Path(uninstall_list)), 'LICENSE_FILE': str(Path(license_text)),
        'ICON_FILE': str(Path(icon)),
    }
    for key, value in defines.items():
        if '"' in value or '\n' in value:
            raise ValueError(f'Unsafe NSIS define {key}: {value!r}')
    return defines


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def classify_owner(source: Path, roots: dict[str, Path], records: dict[Path, str]) -> str:
    """Name the component that supplied one frozen file, or raise for an unknown origin."""
    source = Path(source).resolve()
    resolved = {key: Path(value).resolve() for key, value in roots.items()}
    if _inside(source, resolved['site']):
        owner = records.get(source)
        if owner is None:
            raise BundleError(f'{source} belongs to no installed distribution RECORD')
        return owner
    if _inside(source, resolved['work']):
        return 'pyinstaller-generated'
    if _inside(source, resolved['repo']):
        relative = source.relative_to(resolved['repo']).as_posix()
        for prefix, owner in VENDORED_PREFIXES:
            if relative.startswith(prefix):
                return owner
        return 'assets' if relative.startswith('assets/') else 'mikrocam'
    if _inside(source, resolved['base']):
        return 'cpython'
    raise BundleError(f'{source} is outside allowed roots')


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(files, roots: dict[str, Path], records: dict[Path, str],
                   licenses: dict[str, list[str]], *, excluded: frozenset[str],
                   extra: dict | None = None) -> dict:
    """Map every (destination, source) pair to a licensed owner; refuse anything else."""
    entries, seen, owners = [], set(), {}
    for destination, source in files:
        destination = str(_relative(str(destination)))
        key = destination.casefold()
        if key in seen:
            raise BundleError(f'duplicate destination {destination}')
        seen.add(key)
        if is_excluded_destination(destination):
            raise BundleError(f'excluded destination {destination}')
        owner = classify_owner(Path(source), roots, records)
        if owner in excluded:
            raise BundleError(f'{destination} comes from excluded distribution {owner}')
        if not licenses.get(owner):
            raise BundleError(f'{destination} owner {owner} has no license in the payload')
        entries.append({'path': destination, 'owner': owner, 'sha256': _sha256(Path(source)),
                        'size': os.path.getsize(source)})
        record = owners.setdefault(owner, {'files': 0, 'licenses': sorted(licenses[owner])})
        record['files'] += 1
    entries.sort(key=lambda entry: entry['path'])
    manifest = {'schema_version': SCHEMA_VERSION, 'files': entries, 'owners': dict(sorted(owners.items()))}
    if extra:
        manifest.update(extra)
    return manifest
