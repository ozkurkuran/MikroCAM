"""Collect the additional notices required by the Windows binary into THIRD_PARTY_LICENSES.

    python release/windows/collect_notices.py [--offline]

Run from the isolated build environment (requirements + visual + build pins). Copies exact
license bytes for the build tools from their installed wheels (RECORD-verified), the CPython
Windows LICENSE.txt, the NSIS COPYING file, Qt 6.11.2 third-party attribution pages for the
shipped Qt modules, and records per-file git provenance of the shipped inherited assets.
The result is committed; builds and tests then work offline. Idempotent.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import importlib.metadata as metadata
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
LICENSES = ROOT / 'THIRD_PARTY_LICENSES'
INVENTORY = LICENSES / 'inventory.json'
BUILD_TOOLS = ('altgraph', 'pefile', 'pyinstaller', 'pyinstaller-hooks-contrib', 'pywin32-ctypes')
NOTICE_NAME = re.compile(r'license|licence|notice|copying|copyright|authors', re.I)
QT_VERSION = '6.11.2'
QT_DOCS = 'https://doc.qt.io/qt-6.11/'
QT_SECTIONS = ('qt-core', 'qt-gui', 'qt-image-formats', 'qt-network', 'qt-pdf', 'qt-svg', 'qt-test')
QT_EXTRA_PAGES = ('qt-attribution-llvmpipe.html', 'pdf-licensing.html')
NSIS_COPYING = Path(r'C:\Program Files (x86)\NSIS\COPYING')
SHIPPED_ASSETS = ('assets/resources', 'assets/examples', 'assets/icon.png')
UPSTREAM_TAG = 'upstream-evo-beta1-baseline'


def normalized(name: str) -> str:
    return re.sub(r'[-_.]+', '-', name).lower()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={'User-Agent': 'MikroCAM-notice-collector'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def write_notice(relative: str, data: bytes) -> str:
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return sha256(data)


def wheel_source(distribution) -> dict:
    """Identify the exact PyPI wheel matching the installed WHEEL tag."""
    name, version = distribution.metadata['Name'], distribution.version
    tags = [line.split(': ', 1)[1] for line in distribution.read_text('WHEEL').splitlines()
            if line.startswith('Tag: ')]
    release = json.loads(fetch(f'https://pypi.org/pypi/{name}/{version}/json'))
    def expanded(filename):
        python, abi, platform = filename[:-4].split('-')[-3:]
        return {f'{p}-{a}-{o}' for p in python.split('.') for a in abi.split('.') for o in platform.split('.')}
    for item in release['urls']:
        if item['packagetype'] == 'bdist_wheel' and expanded(item['filename']) == set(tags):
            return {'kind': 'installed-wheel', 'url': item['url'], 'filename': item['filename'],
                    'sha256': item['digests']['sha256'], 'wheel_tags': tags}
    raise SystemExit(f'No PyPI wheel for {name} {version} with tags {tags}')


def build_tool_record(name: str) -> dict:
    distribution = metadata.distribution(name)
    version = distribution.version
    source = wheel_source(distribution)
    files = []
    for item in distribution.files:
        parts = Path(str(item)).parts
        if not parts[0].endswith('.dist-info') or not NOTICE_NAME.search(parts[-1]):
            continue
        if parts[-1] in {'METADATA', 'RECORD', 'WHEEL'}:
            continue
        data = Path(distribution.locate_file(item)).read_bytes()
        if item.hash:
            expected = base64.urlsafe_b64decode(item.hash.value + '==').hex()
            if sha256(data) != expected:
                raise SystemExit(f'{name} {item} differs from its RECORD')
        relative = f'THIRD_PARTY_LICENSES/{normalized(name)}/{version}/wheel/{Path(*parts).as_posix()}'
        files.append({'path': relative, 'role': 'license', 'source': source['url'] + '#' + Path(*parts).as_posix(),
                      'sha256': write_notice(relative, data)})
    meta = distribution.metadata
    return {'name': normalized(name), 'version': version, 'groups': ['build'],
            'license_metadata': {'expression': meta.get('License-Expression'), 'license': meta.get('License'),
                                 'classifiers': [c for c in meta.get_all('Classifier') or [] if c.startswith('License')],
                                 'license_files': meta.get_all('License-File') or []},
            'source': source, 'files': files,
            'notes': 'Build tool. Not imported at runtime; PyInstaller bootloader and runtime hooks are '
                     'embedded in MikroCAM.exe under the bootloader exception.' if name == 'pyinstaller'
            else 'Build tool only; not shipped in the Windows binary.'}


def cpython_component() -> dict:
    version = (ROOT / '.python-version').read_text(encoding='utf-8').strip()
    data = (Path(sys.base_prefix) / 'LICENSE.txt').read_bytes()
    url = f'https://www.python.org/ftp/python/{version}/python-{version}-amd64.exe'
    relative = f'THIRD_PARTY_LICENSES/cpython/{version}/LICENSE.txt'
    return {'name': 'cpython', 'version': version, 'groups': ['windows-binary'],
            'license_metadata': {'declared': 'PSF-2.0 with bundled third-party notices'},
            'source': {'kind': 'official-installer', 'url': url},
            'files': [{'path': relative, 'role': 'license', 'source': url + '#LICENSE.txt',
                       'sha256': write_notice(relative, data)}],
            'notes': 'Interpreter, stdlib, DLLs and Tcl/Tk from the official Windows build; includes '
                     'the Microsoft Distributable Code additional conditions.'}


def nsis_component() -> dict:
    data = NSIS_COPYING.read_bytes()
    url = 'https://sourceforge.net/projects/nsis/files/NSIS%203/3.12/'
    relative = 'THIRD_PARTY_LICENSES/nsis/3.12/COPYING'
    return {'name': 'nsis', 'version': '3.12', 'groups': ['installer'],
            'license_metadata': {'declared': 'zlib/libpng (zlib compressor; bzip2 and CPL-1.0 modules unused)'},
            'source': {'kind': 'official-release', 'url': url},
            'files': [{'path': relative, 'role': 'license', 'source': url + '#COPYING',
                       'sha256': write_notice(relative, data)}],
            'notes': 'Installer stub and plug-ins embedded in the setup executable.'}


def qt_pages(index: str) -> list[str]:
    pages = []
    for section in QT_SECTIONS:
        start = index.index(f'<h2 id="{section}">')
        end = index.find('<h2 ', start + 1)
        pages += re.findall(r'href="([a-z0-9-]+\.html)"', index[start:end])
    return sorted(set(pages) | set(QT_EXTRA_PAGES))


def qt_component() -> dict:
    index_url = QT_DOCS + 'licenses-used-in-qt.html'
    index = fetch(index_url)
    if f'Qt {QT_VERSION}'.encode() not in index:
        raise SystemExit(f'{index_url} no longer documents Qt {QT_VERSION}')
    base = f'THIRD_PARTY_LICENSES/qt-third-party/{QT_VERSION}/'
    files = [{'path': base + 'licenses-used-in-qt.html', 'role': 'attribution', 'source': index_url,
              'sha256': write_notice(base + 'licenses-used-in-qt.html', index)}]
    for page in qt_pages(index.decode('utf-8')):
        data = fetch(QT_DOCS + page)
        files.append({'path': base + page, 'role': 'license', 'source': QT_DOCS + page,
                      'sha256': write_notice(base + page, data)})
    return {'name': 'qt-third-party', 'version': QT_VERSION, 'groups': ['windows-binary'],
            'license_metadata': {'declared': 'Per-component licenses of third-party code in Qt modules'},
            'source': {'kind': 'official-documentation', 'url': index_url},
            'files': files,
            'notes': 'Third-party code in the shipped Qt Core, GUI, Image Formats, Network, PDF (PDFium), '
                     'SVG and Test modules and Mesa llvmpipe (opengl32sw.dll). Pages kept as fetched.'}


def git(*args: str) -> str:
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True, text=True,
                          encoding='utf-8').stdout


def file_history(paths: set[str]) -> dict[str, dict]:
    """One newest→oldest pass: last change and the addition of each file's rename lineage."""
    tracked = {path: path for path in paths}
    found = {path: {} for path in paths}
    commit = None
    for line in git('log', '-M', '--name-status', '--format=%x01%H%x09%an%x09%aI').splitlines():
        if line.startswith('\x01'):
            commit = dict(zip(('commit', 'author', 'date'), line[1:].split('\t')))
            continue
        fields = line.split('\t')
        if len(fields) < 2:
            continue
        status, current = fields[0], fields[-1]
        if current not in tracked:
            continue
        key = tracked[current]
        found[key].setdefault('last', commit)
        if status.startswith('R'):
            tracked[fields[1]] = tracked.pop(current)
        elif status == 'A':
            found[key]['added'] = commit
            tracked.pop(current)
    for path, item in found.items():
        if 'added' not in item:  # Introduced by a merge resolution: use its earliest visible commit.
            earliest = git('log', '--reverse', '--format=%H%x09%an%x09%aI', '--', path).splitlines()[0]
            item['added'] = dict(zip(('commit', 'author', 'date'), earliest.split('\t')))
            item.setdefault('last', item['added'])
    return found


def asset_provenance() -> dict:
    files = []
    for entry in SHIPPED_ASSETS:
        path = ROOT / entry
        files += [path] if path.is_file() else sorted(p for p in path.rglob('*') if p.is_file())
    history = file_history({path.relative_to(ROOT).as_posix() for path in files})
    upstream_commits = set(git('rev-list', UPSTREAM_TAG).split())
    records = []
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        added, last = history[relative]['added'], history[relative]['last']
        records.append({'path': relative, 'sha256': sha256(path.read_bytes()),
                        'origin': 'flatcam-upstream' if last['commit'] in upstream_commits else 'mikrocam',
                        'added_commit': added['commit'], 'added_author': added['author'],
                        'added_date': added['date'], 'last_commit': last['commit'],
                        'last_author': last['author'], 'last_date': last['date']})
    return {'schema_version': 1, 'upstream_baseline': UPSTREAM_TAG,
            'note': 'Git provenance of each shipped asset. It identifies who committed the file to '
                    'FlatCAM/FlatCAM Evo/MikroCAM, not the original artwork author or license; '
                    'NOTICE.md keeps the inherited artwork credits.',
            'files': records}


def replace_by_name(items: list[dict], new: dict) -> None:
    """Replace a record in place, or append it, keeping the existing order stable."""
    for index, item in enumerate(items):
        if item['name'] == new['name']:
            items[index] = new
            return
    items.append(new)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--skip-qt', action='store_true', help='keep the existing Qt pages')
    args = parser.parse_args(argv)
    inventory = json.loads(INVENTORY.read_text(encoding='utf-8'))
    for name in BUILD_TOOLS:
        replace_by_name(inventory['dependencies'], build_tool_record(name))
    components = inventory['components']
    for component in (cpython_component(), nsis_component()) + (() if args.skip_qt else (qt_component(),)):
        replace_by_name(components, component)
    provenance = LICENSES / 'inherited-assets' / 'provenance.json'
    provenance.parent.mkdir(parents=True, exist_ok=True)
    provenance.write_text(json.dumps(asset_provenance(), indent=1, ensure_ascii=False) + '\n',
                          encoding='utf-8', newline='\n')
    # The committed inventory keeps its original CRLF, two-space, non-ASCII-preserving layout.
    INVENTORY.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + '\n', encoding='utf-8',
                         newline='\r\n')
    print(f'{len(inventory["dependencies"])} dependencies, {len(components)} components')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
