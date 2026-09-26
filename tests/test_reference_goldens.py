"""Frozen captures retain exact bytes, admitted inputs and pinned source identity."""
import hashlib
import json
from pathlib import Path

import pytest

from reference.reference_data import load_capture, load_config, load_manifest


ROOT = Path(__file__).parent / 'reference'


@pytest.mark.parametrize('engine', ['legacy8994', 'evo'])
def test_frozen_artifacts_are_complete_hash_verified_and_source_linked(engine):
    manifest = load_manifest(ROOT / 'boards/manifest.json')
    config = load_config(ROOT / 'capture-config.json')
    inventory = json.loads((ROOT / 'goldens/inventory.json').read_text(encoding='utf-8'))
    assert set(inventory) == {'kind', 'schema_version', 'artifacts'}
    assert inventory['kind'] == 'mikrocam.reference-inventory' and inventory['schema_version'] == 1
    paths = [item['path'] for item in inventory['artifacts']]
    assert len(paths) == len(set(paths)) == 2 * len(manifest['boards'])
    records = {item['path']: item for item in inventory['artifacts']}
    expected = {f"{board['id']}.json.gz" for board in manifest['boards']}
    assert {path.name for path in (ROOT / 'goldens' / engine).iterdir()} == expected
    runtimes = []
    for board in manifest['boards']:
        relative = f"{engine}/{board['id']}.json.gz"
        record = records[relative]
        assert set(record) == {'path', 'sha256', 'bytes'}
        path = ROOT / 'goldens' / relative
        assert path.stat().st_size == record['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
        capture = load_capture(path, manifest=manifest, config=config,
                               expected_engine=engine, expected_board=board['id'])
        runtimes.append(capture['runtime'])
        assert capture['source']['files']
        assert all(stage['status'] in {'ok', 'error', 'unsupported'} for stage in capture['stages'])
    assert all(runtime == runtimes[0] for runtime in runtimes)
