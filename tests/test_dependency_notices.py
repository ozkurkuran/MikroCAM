"""Check source-traceable notices without importing installed dependencies."""

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
GROUPS = {'runtime': 'requirements.txt', 'development': 'requirements-dev.txt',
          'optional-image': 'requirements-image.txt'}
CODE_OR_BINARY_SUFFIXES = {'.py', '.pyi', '.pyc', '.pyo', '.dll', '.exe', '.pyd', '.so',
                          '.dylib', '.a', '.lib', '.js', '.mjs', '.c', '.h', '.cpp', '.rs',
                          '.whl', '.zip', '.tar', '.gz'}


def normalized(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def pinned_requirements(root):
    pins = {}

    def read(path, group, seen):
        assert path not in seen, f'Recursive requirements include: {path}'
        seen = seen | {path}
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('-r '):
                read(path.parent / line[3:].strip(), group, seen)
                continue
            match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s;]+)', line)
            assert match, f'Unsupported dependency pin: {line}'
            name, version = normalized(match[1]), match[2]
            record = pins.setdefault(name, {'version': version, 'groups': set()})
            assert record['version'] == version, f'Conflicting version for {name}'
            record['groups'].add(group)

    for group, filename in GROUPS.items():
        read(root / filename, group, set())
    return pins


def validate_inventory(record, root, pins):
    assert type(record['schema_version']) is int and record['schema_version'] == 1, 'Unsupported notice schema'
    packages = record['dependencies']
    assert len(packages) == len(pins), 'Dependency coverage mismatch'
    assert len({item['name'] for item in packages}) == len(packages), 'Duplicate dependency'
    assert {item['name'] for item in packages} == set(pins), 'Dependency coverage mismatch'
    for item in packages:
        name = item['name']
        assert normalized(name) == name, 'Dependency name is not normalized'
        assert item['version'] == pins[name]['version'], f'Wrong version: {name}'
        assert set(item['groups']) == pins[name]['groups'], f'Wrong groups: {name}'
        assert item['license_metadata'], f'Missing license metadata: {name}'
    components = record['components']
    assert len({normalized(item['name']) for item in components}) == len(components), 'Duplicate component'
    seen = set()
    for item in [*packages, *record['components']]:
        assert item['source']['url'].startswith('https://'), 'Missing upstream source'
        assert item['files'], f"Missing complete notice: {item['name']}"
        assert any(f['role'] == 'license' for f in item['files']), 'Missing full license text'
        for file in item['files']:
            path = file['path']
            parts = PurePosixPath(path).parts
            assert PurePosixPath(path).suffix.lower() not in CODE_OR_BINARY_SUFFIXES, 'Invalid notice file: code or binary'
            if item in packages:
                assert re.search(r'license|licence|notice|copying|copyright|authors',
                                 PurePosixPath(path).name, re.I), 'Invalid notice file basename'
            assert path == '/'.join(parts) and '\\' not in path, 'Unsafe notice path'
            assert parts and parts[0] == 'THIRD_PARTY_LICENSES' and '..' not in parts, 'Unsafe notice path'
            target = (root / path).resolve()
            assert target.is_relative_to((root / 'THIRD_PARTY_LICENSES').resolve()), 'Unsafe notice path'
            assert path not in seen, 'Duplicate notice path'
            seen.add(path)
            assert file['source'], 'Missing file provenance'
            assert re.fullmatch(r'[0-9a-f]{64}', file['sha256']), 'Invalid notice hash'
            content = target.read_bytes()
            assert content, 'Empty notice'
            assert hashlib.sha256(content).hexdigest() == file['sha256'], f'Notice hash mismatch: {path}'


def test_pinned_dependency_notice_coverage_and_integrity():
    record = json.loads((ROOT / 'THIRD_PARTY_LICENSES/inventory.json').read_text(encoding='utf-8'))
    validate_inventory(record, ROOT, pinned_requirements(ROOT))


def test_standard_development_install_includes_svg_renderer():
    assert 'development' in pinned_requirements(ROOT)['resvg-py']['groups']


@pytest.fixture
def notice_fixture(tmp_path):
    path = tmp_path / 'THIRD_PARTY_LICENSES/example/LICENSE'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'An unchanged upstream license\r\n')
    record = {'schema_version': 1, 'components': [], 'dependencies': [{
        'name': 'example', 'version': '1.0', 'groups': ['runtime'],
        'license_metadata': {'expression': 'MIT'},
        'source': {'url': 'https://example.invalid/releases/1.0'},
        'files': [{'path': 'THIRD_PARTY_LICENSES/example/LICENSE', 'role': 'license',
                   'source': 'example-1.0.whl:example.dist-info/LICENSE',
                   'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}],
    }]}
    pins = {'example': {'version': '1.0', 'groups': {'runtime'}}}
    return tmp_path, record, pins


def test_valid_notice_fixture_preserves_crlf_bytes(notice_fixture):
    root, record, pins = notice_fixture
    validate_inventory(record, root, pins)


@pytest.mark.parametrize('mutation', [
    lambda record: record.update(schema_version=2),
    lambda record: record.update(schema_version=True),
    lambda record: record['dependencies'].clear(),
    lambda record: record['dependencies'].append(copy.deepcopy(record['dependencies'][0])),
    lambda record: record['dependencies'][0].update(version='2.0'),
    lambda record: record['dependencies'][0].update(groups=['optional-image']),
    lambda record: record['dependencies'][0].update(files=[]),
    lambda record: record['dependencies'][0]['files'][0].update(path='THIRD_PARTY_LICENSES/../LICENSE'),
    lambda record: record['dependencies'][0]['files'][0].update(path='/tmp/LICENSE'),
    lambda record: record['dependencies'][0]['files'][0].update(path='THIRD_PARTY_LICENSES\\example\\LICENSE'),
    lambda record: record['dependencies'][0]['files'][0].update(sha256='0' * 64),
    lambda record: record['dependencies'][0]['files'][0].update(source=''),
    lambda record: record['dependencies'][0]['files'][0].update(role='readme'),
])
def test_invalid_notice_records_are_rejected(notice_fixture, mutation):
    root, record, pins = notice_fixture
    mutation(record)
    with pytest.raises(AssertionError):
        validate_inventory(record, root, pins)


def test_modified_upstream_notice_is_detected(notice_fixture):
    root, record, pins = notice_fixture
    (root / record['dependencies'][0]['files'][0]['path']).write_bytes(b'Altered\n')
    with pytest.raises(AssertionError, match='hash mismatch'):
        validate_inventory(record, root, pins)


@pytest.mark.parametrize('filename', ['LICENSE.py', 'LICENSE.pyc', 'LICENSE.dll', 'spdx_lookup.txt'])
def test_runtime_code_and_binary_files_are_not_notice_records(notice_fixture, filename):
    root, record, pins = notice_fixture
    target = root / 'THIRD_PARTY_LICENSES/example' / filename
    target.write_bytes(b'Not a license: runtime code, data or binary')
    item = record['dependencies'][0]['files'][0]
    item.update(path=target.relative_to(root).as_posix(),
                sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    with pytest.raises(AssertionError, match='notice file'):
        validate_inventory(record, root, pins)


def test_inventory_contains_only_notice_text_and_provenance():
    record = json.loads((ROOT / 'THIRD_PARTY_LICENSES/inventory.json').read_text(encoding='utf-8'))
    for item in record['dependencies']:
        for file in item['files']:
            basename = PurePosixPath(file['path']).name
            assert re.search(r'license|licence|notice|copying|copyright|authors', basename, re.I), basename
            assert PurePosixPath(file['path']).suffix.lower() not in CODE_OR_BINARY_SUFFIXES


def test_supplied_copyleft_and_bundled_notices_are_retained():
    record = json.loads((ROOT / 'THIRD_PARTY_LICENSES/inventory.json').read_text(encoding='utf-8'))
    packages = {item['name']: item for item in record['dependencies']}
    assert packages['pyqt6']['license_metadata']['expression'] == 'GPL-3.0-only'
    assert 'LGPL' in packages['pyqt6-qt6']['license_metadata']['license']
    for name, title in [('pyqt6', 'GNU GENERAL PUBLIC LICENSE'),
                        ('pyqt6-qt6', 'GNU LESSER GENERAL PUBLIC LICENSE')]:
        assert any(title in (ROOT / file['path']).read_text(encoding='utf-8', errors='replace')
                   for file in packages[name]['files'])
    for name, fragment in [('numpy', 'lapack_lite'), ('setuptools', '_vendor'),
                           ('playwright', 'ThirdPartyNotices'), ('shapely', 'LICENSE_GEOS'),
                           ('reportlab', 'DarkGarden'), ('rasterio', 'gdal_data')]:
        assert any(fragment in file['source'] for file in packages[name]['files']), name
    components = {item['name'] for item in record['components']}
    assert {'qdarktheme', 'material-design-icons', 'qdarkstylesheet', 'descartes', 'imagetracer-js'} <= components
    notice = (ROOT / 'NOTICE.md').read_text(encoding='utf-8')
    assert 'GPLv3' in notice and 'LGPL' in notice
    assert 'Rasterio' in notice and 'audit gap' in notice
    assert 'per-file provenance' in notice


def test_missing_wheel_main_licenses_use_exact_source_archives():
    record = json.loads((ROOT / 'THIRD_PARTY_LICENSES/inventory.json').read_text(encoding='utf-8'))
    packages = {item['name']: item for item in record['dependencies']}
    for name, version, filename in [('pyopengl', '3.1.10', 'license.txt'),
                                    ('pyserial', '3.5', 'LICENSE.txt')]:
        item = packages[name]
        archives = [source for source in item['additional_sources'] if source['kind'] == 'source-archive']
        assert len(archives) == 1
        assert f'{name}-{version}.tar.gz' in archives[0]['url']
        assert any(file['source'] == archives[0]['url'] + f'#{name}-{version}/{filename}'
                   and file['role'] == 'license' for file in item['files'])


def test_vendored_source_gaps_are_explicit_and_not_relicensed():
    record = json.loads((ROOT / 'THIRD_PARTY_LICENSES/inventory.json').read_text(encoding='utf-8'))
    components = {item['name']: item for item in record['components']}
    descartes = components['descartes']
    assert any(file['role'] == 'metadata' and 'descartes-1.1.0/PKG-INFO' in file['source']
               for file in descartes['files'])
    assert any(source['kind'] == 'downstream-license-snapshot' for source in descartes['additional_sources'])
    tracer = components['imagetracer-js']
    header = (ROOT / tracer['files'][0]['path']).read_text(encoding='utf-8')
    assert 'exempt from' in header and 'MIT License' in header
    assert 'The Unlicense / PUBLIC DOMAIN' in header
    assert {'rasterio', 'inherited-assets', 'descartes', 'qdarktheme-resources'} <= {
        gap['component'] for gap in record['audit_gaps']
    }
