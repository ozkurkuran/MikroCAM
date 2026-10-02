"""Exact-source Rust notice graph for the optional visual renderer, without imports."""
import hashlib
import json
from pathlib import Path
import tomllib

ROOT=Path(__file__).resolve().parents[1]


def test_resvg_source_lock_and_complete_notice_graph_are_retained():
    lock_path=ROOT/'THIRD_PARTY_LICENSES/resvg-py/0.5.0/sdist/resvg_py-0.5.0/Cargo.lock'
    data=lock_path.read_bytes()
    assert hashlib.sha256(data).hexdigest()=='578b2a28b47041de07b6722712aca776efdf8b1b1b2ac49e91f5e829df4ea70a'
    lock=tomllib.loads(data.decode('utf-8'))
    expected={(p['name'],p['version']):p['checksum'] for p in lock['package'] if 'source' in p}
    assert len(expected)==75 and ('resvg','0.48.1') in expected and ('usvg','0.48.1') in expected
    inventory=json.loads((ROOT/'THIRD_PARTY_LICENSES/inventory.json').read_text(encoding='utf-8'))
    components=[item for item in inventory['components'] if item.get('scope')=='resvg-py-source-lock']
    actual={(item['crate_name'],item['version']):item for item in components}
    assert set(actual)==set(expected)
    for key,checksum in expected.items():
        record=actual[key]
        assert record['source']['sha256']==checksum and record['source']['url'].startswith('https://static.crates.io/crates/')
        assert record['license_metadata']['expression'] and any(file['role']=='license' for file in record['files'])
        for file in record['files']:
            assert hashlib.sha256((ROOT/file['path']).read_bytes()).hexdigest()==file['sha256']


def test_notice_graph_does_not_claim_unavailable_wheel_build_provenance():
    inventory=json.loads((ROOT/'THIRD_PARTY_LICENSES/inventory.json').read_text(encoding='utf-8'))
    gap=next(item for item in inventory['audit_gaps'] if item['component']=='resvg-py')
    assert gap['status']=='source-notices-retained'
    assert '75' in gap['detail'] and 'build provenance' in gap['detail']
