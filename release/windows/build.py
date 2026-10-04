"""Build the MikroCAM Windows portable ZIP and per-user NSIS installer.

    python release/windows/build.py [--out DIR] [--skip-installer]

Run with an isolated CPython 3.13 x64 virtual environment that contains exactly
requirements.txt + requirements-visual.txt + requirements-build.txt. The build refuses other
interpreters/packages, runs PyInstaller with a sanitized PATH, maps every collected file to a
licensed owner (bundle-manifest.json) and only then writes artifacts. It never publishes.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import sysconfig

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import release_layout as layout  # noqa: E402
from mikrocam.core import identity  # noqa: E402

REQUIREMENT_FILES = ('requirements.txt', 'requirements-visual.txt', 'requirements-build.txt')
TOOLING = {'pip'}
NSIS_VERSION = 'v3.12'
NSIS_DEFAULT = Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'NSIS' / 'makensis.exe'


def normalized(name: str) -> str:
    return re.sub(r'[-_.]+', '-', name).lower()


def pinned_requirements() -> dict[str, str]:
    pins = {}
    for filename in REQUIREMENT_FILES:
        for line in (ROOT / filename).read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith(('#', '-r ')):
                continue
            name, version = re.fullmatch(r'([A-Za-z0-9_.-]+)==(\S+)', line).groups()
            if pins.setdefault(normalized(name), version) != version:
                raise SystemExit(f'Conflicting pin for {name}')
    return pins


def check_environment() -> dict[str, str]:
    """Refuse anything but the pinned CPython and exactly the pinned distributions."""
    expected = (ROOT / '.python-version').read_text(encoding='utf-8').strip()
    if platform.python_version() != expected or platform.python_implementation() != 'CPython':
        raise SystemExit(f'Use CPython {expected}; running {platform.python_version()}')
    if sys.maxsize <= 2 ** 32 or sysconfig.get_config_var('Py_GIL_DISABLED'):
        raise SystemExit('A standard 64-bit CPython build is required')
    if sys.prefix == sys.base_prefix:
        raise SystemExit('Run inside an isolated virtual environment')
    pins = pinned_requirements()
    installed = {normalized(d.metadata['Name']): d.version for d in metadata.distributions()}
    extra = sorted(set(installed) - set(pins) - TOOLING)
    wrong = sorted(f'{n} {installed.get(n)} != {v}' for n, v in pins.items() if installed.get(n) != v)
    if extra or wrong:
        raise SystemExit(f'Build environment differs from pins. Extra: {extra}; mismatched: {wrong}')
    check = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True)
    if check.returncode:
        raise SystemExit(check.stdout + check.stderr)
    return installed


def verify_runtime_notice() -> None:
    """The shipped CPython must be the build whose LICENSE.txt is retained in the inventory."""
    inventory = json.loads((ROOT / 'THIRD_PARTY_LICENSES' / 'inventory.json').read_text(encoding='utf-8'))
    cpython = next(item for item in inventory['components'] if item['name'] == 'cpython')
    actual = sha256(Path(sys.base_prefix) / 'LICENSE.txt')
    if cpython['version'] != platform.python_version() or cpython['files'][0]['sha256'] != actual:
        raise SystemExit('CPython LICENSE.txt differs from THIRD_PARTY_LICENSES/cpython; rerun collect_notices.py')


def sanitized_environment(version_file: Path) -> dict[str, str]:
    """Keep only system directories and this interpreter on PATH to stop DLL leakage."""
    system_root = os.environ.get('SystemRoot', r'C:\Windows')
    path = [rf'{system_root}\System32', system_root, rf'{system_root}\System32\Wbem',
            sys.base_prefix, str(Path(sys.executable).parent)]
    env = {key: value for key, value in os.environ.items()
           if key.upper() not in {'PATH', 'PYTHONPATH', 'PYTHONHOME', 'QT_PLUGIN_PATH'}}
    env.update(PATH=os.pathsep.join(path), MIKROCAM_VERSION_FILE=str(version_file), PYTHONUTF8='1')
    return env


def run_pyinstaller(work: Path, dist: Path) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    version_file = work / 'version_info.txt'
    version_file.write_text(layout.version_resource(identity), encoding='utf-8')
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--log-level', 'WARN',
               '--distpath', str(dist), '--workpath', str(work), str(HERE / 'mikrocam.spec')]
    subprocess.run(command, check=True, cwd=ROOT, env=sanitized_environment(version_file))
    return dist / identity.NAME


def record_index() -> tuple[dict[Path, str], dict[Path, str]]:
    """Map installed files to their distribution and expected RECORD sha256."""
    owners, hashes = {}, {}
    for distribution in metadata.distributions():
        name = normalized(distribution.metadata['Name'])
        for item in distribution.files or ():
            path = Path(distribution.locate_file(item)).resolve()
            owners[path] = name
            if item.hash and item.hash.mode == 'sha256':
                hashes[path] = base64.urlsafe_b64decode(item.hash.value + '==').hex()
    return owners, hashes


def read_toc(path: Path) -> list:
    import ast
    data = ast.literal_eval(path.read_text(encoding='utf-8'))
    return next(item for item in data if isinstance(item, list))


def license_map(payload_licenses: str = 'licenses') -> dict[str, list[str]]:
    """Owner → payload-relative license/notice files, from the authoritative inventory."""
    inventory = json.loads((ROOT / 'THIRD_PARTY_LICENSES' / 'inventory.json').read_text(encoding='utf-8'))
    def shipped(item):
        return [payload_licenses + '/' + f['path'].split('/', 1)[1] for f in item['files']]
    mapping = {normalized(item['name']): shipped(item) for item in inventory['dependencies']}
    mapping.update({normalized(item['name']): shipped(item) for item in inventory['components']})
    mapping['mikrocam'] = ['LICENSE.txt', 'NOTICE.md', 'NOTICE-BINARY.txt']
    mapping['assets'] = ['NOTICE.md', payload_licenses + '/inherited-assets/provenance.json']
    mapping['pyinstaller-generated'] = mapping.get('pyinstaller', []) + mapping.get('cpython', [])
    return mapping


def collect_manifest(work: Path, collected: Path) -> dict:
    owners, hashes = record_index()
    site = Path(sysconfig.get_paths()['purelib']).resolve()
    roots = {'repo': ROOT, 'base': Path(sys.base_prefix), 'site': site, 'work': work}
    spec_work = work / 'mikrocam'
    # PyInstaller 6 places everything except the executables in the _internal contents directory.
    files = [(dest if kind == 'EXECUTABLE' else '_internal/' + dest, src)
             for dest, src, kind in read_toc(spec_work / 'COLLECT-00.toc') if Path(dest).name != layout.SMOKE_EXE]
    licenses = license_map()
    manifest = layout.build_manifest(files, roots, owners, licenses, excluded=layout.EXCLUDED_DISTRIBUTIONS)
    modules = [('pyz/' + name, src) for name, src, kind in read_toc(spec_work / 'PYZ-00.toc')
               if src not in {None, '', '-'} and kind in {'PYMODULE', 'PYSOURCE'}]  # '-' = namespace package
    module_manifest = layout.build_manifest(modules, roots, owners, licenses,
                                            excluded=layout.EXCLUDED_DISTRIBUTIONS)
    sources = {dest.replace('\\', '/'): Path(src).resolve() for dest, src in files}
    mismatched = [entry['path'] for entry in manifest['files']
                  if hashes.get(sources[entry['path']], entry['sha256']) != entry['sha256']]
    if mismatched:
        raise layout.BundleError(f'Collected files differ from installed wheel RECORD: {mismatched[:5]}')
    on_disk = set(layout.payload_files(collected)) - {layout.SMOKE_EXE}
    listed = {entry['path'] for entry in manifest['files']}
    if on_disk != listed:
        raise layout.BundleError(f'Payload/manifest mismatch: {sorted(on_disk ^ listed)[:10]}')
    manifest['module_owners'] = {owner: data['files'] for owner, data in module_manifest['owners'].items()}
    return manifest


def assemble_payload(collected: Path, payload: Path, manifest: dict) -> None:
    if payload.exists():
        shutil.rmtree(payload)
    shutil.copytree(collected, payload, ignore=lambda d, names: [n for n in names if n == layout.SMOKE_EXE])
    shutil.copytree(ROOT / 'THIRD_PARTY_LICENSES', payload / 'licenses')
    shutil.copyfile(ROOT / 'LICENSE', payload / 'LICENSE.txt')
    shutil.copyfile(ROOT / 'NOTICE.md', payload / 'NOTICE.md')
    shutil.copyfile(HERE / 'NOTICE-BINARY.txt', payload / 'NOTICE-BINARY.txt')
    (payload / 'bundle-manifest.json').write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n',
                                                  encoding='utf-8')
    for owner, data in manifest['owners'].items():
        missing = [path for path in data['licenses'] if not (payload / path).is_file()]
        if missing:
            raise layout.BundleError(f'{owner} license files missing from payload: {missing}')


def source_timestamp() -> int:
    if os.environ.get('SOURCE_DATE_EPOCH'):
        return int(os.environ['SOURCE_DATE_EPOCH'])
    result = subprocess.run(['git', 'log', '-1', '--format=%ct'], cwd=ROOT, capture_output=True, text=True)
    return int(result.stdout.strip() or 315532800)


def find_makensis() -> Path:
    candidate = os.environ.get('MAKENSIS') or shutil.which('makensis') or str(NSIS_DEFAULT)
    path = Path(candidate)
    if not path.is_file():
        raise SystemExit('makensis not found; install NSIS 3.12 or set MAKENSIS')
    version = subprocess.run([str(path), '-VERSION'], capture_output=True, text=True).stdout.strip()
    if version != NSIS_VERSION:
        raise SystemExit(f'NSIS {NSIS_VERSION} required, found {version}')
    return path


def build_installer(payload: Path, out: Path, names: dict[str, str]) -> Path:
    makensis = find_makensis()
    staging = out / 'installer'
    staging.mkdir(parents=True, exist_ok=True)
    config = staging / 'configuration.txt'
    config.write_text(layout.configuration_text(False), encoding='ascii')
    files = layout.payload_files(payload) + ['config/configuration.txt', layout.UNINSTALLER_EXE]
    uninstall = staging / 'uninstall-files.nsh'
    uninstall.write_text(layout.uninstall_script(files), encoding='utf-8')
    setup = out / names['setup']
    defines = layout.nsis_defines(identity, payload, setup, uninstall, HERE / 'NOTICE-BINARY.txt',
                                  ROOT / 'docs' / 'branding' / 'mikrocam.ico')
    defines['CONFIG_FILE'] = str(config)
    command = [str(makensis), '/V2', '/WX', '/INPUTCHARSET', 'UTF8']
    command += [f'/D{key}={value}' for key, value in sorted(defines.items())]
    command.append(str(HERE / 'MikroCAM.nsi'))
    subprocess.run(command, check=True, cwd=HERE)
    return setup


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', type=Path, default=ROOT / 'dist' / 'windows')
    parser.add_argument('--skip-installer', action='store_true')
    args = parser.parse_args(argv)
    out = args.out.resolve()
    installed = check_environment()
    verify_runtime_notice()
    names = layout.artifact_names(identity.NAME, identity.VERSION)
    collected = run_pyinstaller(out / 'work', out / 'pyinstaller')
    manifest = collect_manifest(out / 'work', collected)
    manifest.update(version=identity.VERSION, python=platform.python_version(),
                    pyinstaller=installed['pyinstaller'])
    payload = out / 'payload' / names['folder']
    assemble_payload(collected, payload, manifest)
    artifacts = [out / names['zip']]
    layout.write_deterministic_zip(payload, artifacts[0], names['folder'], source_timestamp(),
                                   extra={'config/configuration.txt': layout.configuration_text(True).encode()})
    if not args.skip_installer:
        artifacts.append(build_installer(payload, out, names))
    sums = ''.join(f'{sha256(path)}  {path.name}\n' for path in artifacts)
    (out / names['checksums']).write_text(sums, encoding='ascii')
    print(sums, end='')
    print(f'Smoke executable (not shipped): {collected / layout.SMOKE_EXE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
