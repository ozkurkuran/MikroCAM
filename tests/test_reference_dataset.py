"""Strict corpus admission, unchanged bytes and archive-entry provenance."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import zipfile

import pytest


def fixture_manifest(root):
    boards = []
    for index in range(10):
        identifier = f'board-{index}'
        files = []
        for name, role, content in [('copper.gbr', 'copper', b'synthetic test bytes'),
                                    ('LICENSE', 'notice', b'MIT fixture notice')]:
            relative = f'{identifier}/{name}'
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            files.append(dict(path=relative, source_path=name, sha256=digest, source_sha256=digest, role=role))
        boards.append(dict(id=identifier, name=f'Fixture {index}',
            origin=('KiCad', 'EasyEDA', 'Altium', 'Eagle', 'Proteus', 'DipTrace')[index % 6],
            design_identity=f'https://example.invalid/design/{index}',
            source=dict(url='https://example.invalid/source', revision='a' * 40, origin_evidence='Fixture only'),
            license=dict(identifier='MIT', evidence='Original fixture notice', notices=[f'{identifier}/LICENSE']),
            files=files))
    return dict(kind='mikrocam.reference-dataset', schema_version=1, boards=boards)


def test_manifest_verifies_corpus_bytes_and_additional_origins(tmp_path):
    from reference.reference_data import load_manifest, manifest_to_json
    data = fixture_manifest(tmp_path)
    path = tmp_path / 'manifest.json'
    path.write_text(manifest_to_json(data), encoding='utf-8')
    assert load_manifest(path) == data
    (tmp_path / data['boards'][0]['files'][0]['path']).write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash|SHA'):
        load_manifest(path)


@pytest.mark.parametrize('mutation', [lambda d: d.update(schema_version=True), lambda d: d.update(extra=1),
    lambda d: d.update(boards=d['boards'][:9]), lambda d: d['boards'][1].update(id=d['boards'][0]['id']),
    lambda d: d['boards'][1].update(design_identity=d['boards'][0]['design_identity']),
    lambda d: d['boards'][0].update(origin=''), lambda d: d['boards'][0]['source'].update(revision='main'),
    lambda d: d['boards'][0]['license'].update(notices=[]), lambda d: d['boards'][0]['files'][0].update(role='image'),
    lambda d: d['boards'][0]['files'][0].update(path='../escape.gbr'),
    lambda d: d['boards'][0]['files'][0].update(path='C:/escape.gbr'),
    lambda d: d['boards'][0]['files'][0].update(source_sha256='0' * 64),
    lambda d: d['boards'][0]['files'].append(deepcopy(d['boards'][0]['files'][0]))])
def test_manifest_rejects_invalid_or_ambiguous_admission(tmp_path, mutation):
    from reference.reference_data import validate_manifest
    data = fixture_manifest(tmp_path)
    mutation(data)
    with pytest.raises(ValueError):
        validate_manifest(data, root=tmp_path)


def test_manifest_requires_every_named_tool_but_not_only_those_tools(tmp_path):
    from reference.reference_data import validate_manifest
    data = fixture_manifest(tmp_path)
    for board in data['boards']:
        if board['origin'] == 'Proteus':
            board['origin'] = 'gEDA'
    with pytest.raises(ValueError, match='Proteus|origin'):
        validate_manifest(data)


def test_duplicate_json_keys_are_not_silently_overwritten(tmp_path):
    from reference.reference_data import manifest_from_json
    text = json.dumps(fixture_manifest(tmp_path)).replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
    with pytest.raises(ValueError, match='duplicate'):
        manifest_from_json(text)


def test_archive_original_and_extracted_member_are_both_verified(tmp_path):
    from reference.reference_data import validate_manifest
    data = fixture_manifest(tmp_path)
    board = data['boards'][0]
    archive = tmp_path / 'board-0/original.zip'
    with zipfile.ZipFile(archive, 'w') as stream:
        stream.writestr('fabrication/copper.gbr', b'synthetic test bytes')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    board['files'].append(dict(path='board-0/original.zip', source_path='production/original.zip',
                              sha256=digest, source_sha256=digest, role='archive'))
    board['files'][0]['source_path'] = 'production/original.zip!fabrication/copper.gbr'
    assert validate_manifest(data, root=tmp_path) == data
    board['files'][0]['source_path'] = 'production/original.zip!missing.gbr'
    with pytest.raises(ValueError, match='archive|member'):
        validate_manifest(data, root=tmp_path)


def test_corpus_symlink_cannot_escape_root(tmp_path):
    from reference.reference_data import validate_manifest
    data = fixture_manifest(tmp_path)
    outside = tmp_path.parent / f'{tmp_path.name}-outside'
    outside.write_bytes(b'synthetic test bytes')
    target = tmp_path / 'board-0/copper.gbr'
    target.unlink()
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip('Creating symlinks requires OS permission')
    with pytest.raises(ValueError, match='outside|escape'):
        validate_manifest(data, root=tmp_path)


def test_admitted_real_corpus_is_offline_auditable():
    from reference.reference_data import load_manifest
    data = load_manifest(Path(__file__).parent / 'reference/boards/manifest.json')
    assert 10 <= len(data['boards']) <= 20
    assert {'KiCad', 'EasyEDA', 'Altium', 'Eagle', 'Proteus'} <= {board['origin'] for board in data['boards']}


@pytest.mark.parametrize('mutation', [lambda d: d['boards'][0]['license'].update(identifier={}),
    lambda d: d['boards'][0]['license'].update(notices=[{}]),
    lambda d: d['boards'][0]['files'][0].update(role=[])])
def test_wrong_manifest_enum_types_are_value_errors(tmp_path, mutation):
    from reference.reference_data import validate_manifest
    manifest = fixture_manifest(tmp_path)
    mutation(manifest)
    with pytest.raises(ValueError):
        validate_manifest(manifest)
