"""Capture boundaries reject substituted source, leaks, runaway children and overwrites."""
from pathlib import Path
import subprocess
import sys
import json
import hashlib
from types import SimpleNamespace

import pytest

REFERENCE = Path(__file__).parent / 'reference'
sys.path.insert(0, str(REFERENCE))
import capture
import baseline_host


def repository(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'camlib.py').write_text('VALUE = 1\n')
    for args in [('init',), ('add', '.'), ('-c', 'user.name=Capture Test',
                  '-c', 'user.email=capture@example.invalid', 'commit', '-m', 'source')]:
        subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    return root, revision


def test_clean_exact_current_source_is_required(tmp_path):
    root, revision = repository(tmp_path)
    assert capture.verify_source(root, 'current', revision) == revision
    for wrong in [None, 'HEAD', revision[:12], '0' * 40]:
        with pytest.raises(ValueError):
            capture.verify_source(root, 'current', wrong)


@pytest.mark.parametrize('change', ['tracked', 'untracked'])
def test_dirty_source_is_rejected(tmp_path, change):
    root, revision = repository(tmp_path)
    (root / ('camlib.py' if change == 'tracked' else 'extra.py')).write_text('changed')
    with pytest.raises(ValueError, match='[Dd]irty|clean'):
        capture.verify_source(root, 'current', revision)


@pytest.mark.parametrize('engine', ['evo', 'legacy8994'])
def test_baseline_label_cannot_be_attached_to_arbitrary_revision(tmp_path, engine):
    root, revision = repository(tmp_path)
    with pytest.raises(ValueError):
        capture.verify_source(root, engine, revision)


def test_source_module_containment_and_missing_file_fail(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    inside = source / 'camlib.py'
    inside.write_text('')
    outside = tmp_path / 'camlib.py'
    outside.write_text('')
    assert baseline_host.verify_module_paths([SimpleNamespace(__file__=str(inside))], source)
    for module in [SimpleNamespace(__file__=str(outside)), SimpleNamespace(__file__=None)]:
        with pytest.raises(ValueError, match='source|module'):
            baseline_host.verify_module_paths([module], source)


def test_timeout_kills_and_reaps_owned_child(tmp_path):
    with pytest.raises(capture.CaptureFailure, match='timed out'):
        capture.run_worker([sys.executable, '-c', 'import time; time.sleep(30)'], tmp_path, .15)


@pytest.mark.parametrize('timeout', [0, -1, float('nan'), float('inf'), True])
def test_subprocess_timeout_is_bounded_positive(tmp_path, timeout):
    with pytest.raises(ValueError):
        capture.run_worker([sys.executable, '-c', 'print("{}")'], tmp_path, timeout)


@pytest.mark.parametrize('stream', ['stdout', 'stderr'])
def test_subprocess_output_is_bounded(tmp_path, monkeypatch, stream):
    monkeypatch.setattr(capture, 'MAX_CHILD_BYTES', 32)
    code = f'import sys; print("x"*100, file=sys.{stream})'
    with pytest.raises(capture.CaptureFailure, match='output limit'):
        capture.run_worker([sys.executable, '-c', code], tmp_path, 5)


def test_child_failure_and_invalid_json_are_not_success(tmp_path):
    with pytest.raises(capture.CaptureFailure, match='failure detail'):
        capture.run_worker([sys.executable, '-c',
                            'import sys; print("failure detail",file=sys.stderr); sys.exit(3)'], tmp_path, 5)
    with pytest.raises(capture.CaptureFailure, match='JSON'):
        capture.run_worker([sys.executable, '-c', 'print("not JSON")'], tmp_path, 5)
    assert capture.run_worker([sys.executable, '-c', 'print("{\\"ok\\":true}")'], tmp_path, 5) == {'ok': True}


def test_existing_output_is_refused_before_source_or_corpus_access(tmp_path):
    output = tmp_path / 'existing'
    output.mkdir()
    protected = output / 'record'
    protected.write_bytes(b'unchanged')
    with pytest.raises(ValueError, match='exists|existing'):
        capture.capture_dataset('current', tmp_path / 'absent', sys.executable,
                                tmp_path / 'manifest', tmp_path / 'config', output, '0' * 40, 5)
    assert protected.read_bytes() == b'unchanged'
    assert list(output.iterdir()) == [protected]


def test_named_qsettings_stays_in_sandbox(tmp_path, monkeypatch):
    from PyQt6 import QtCore
    original = QtCore.QSettings
    monkeypatch.setenv('APPDATA', str(tmp_path / 'before'))
    baseline_host.sandbox_settings(tmp_path / 'sandbox')
    try:
        settings = QtCore.QSettings('Open Source', 'FlatCAM_EVO')
        settings.setValue('capture-test', 'isolated')
        settings.sync()
        assert Path(settings.fileName()).resolve().is_relative_to((tmp_path / 'sandbox').resolve())
        assert settings.format() == original.Format.IniFormat
        assert not (tmp_path / 'before').exists()
    finally:
        QtCore.QSettings = original


def test_native_unit_conversion_uses_current_units_not_stale_labels():
    import capture_worker
    calls = []
    parser = SimpleNamespace(units='IN', units_found='MM')

    def convert(units):
        calls.append(units)
        parser.units = units

    parser.convert_units = convert
    assert capture_worker._normalize(parser) == 'IN'
    assert parser.units == 'MM' and calls == ['MM']
    parser.units = 'unknown'
    with pytest.raises(ValueError):
        capture_worker._normalize(parser)
    assert calls == ['MM']


def test_tool_snapshot_preserves_duplicate_drills_slots_and_unused_tools():
    from shapely.geometry import Point
    import capture_worker
    parser = SimpleNamespace(tools={
        2: {'tooldia': .9, 'drills': [], 'slots': []},
        1: {'tooldia': .5, 'drills': [Point(1, 2), Point(1, 2)],
            'slots': [(Point(3, 4), Point(5, 6)), (Point(3, 4), Point(5, 6))]},
    })
    assert capture_worker._tools(parser) == [
        {'id': '1', 'diameter_mm': .5, 'drills': [[1., 2.], [1., 2.]],
         'slots': [[[3., 4.], [5., 6.]], [[3., 4.], [5., 6.]]]},
        {'id': '2', 'diameter_mm': .9, 'drills': [], 'slots': []}]


def test_failed_stage_scaffold_is_contextual_and_contains_no_fabricated_geometry():
    board = {'files': [{'path': 'a/copper.gbr', 'role': 'copper'},
                       {'path': 'a/drill-map.gbr', 'role': 'drill-map'}]}
    config = {'stages': {'copper': ['gerber', 'isolation', 'cnc'], 'drill-map': []}}
    stages = capture._failed_stages(board, config, 'board timed out')
    assert [stage['stage'] for stage in stages] == ['gerber', 'isolation', 'cnc']
    assert all(stage['status'] == 'error' and stage['diagnostic'] == 'board timed out'
               and not stage['geometry_wkb'] and not stage['paths'] and stage['gcode'] is None
               for stage in stages)


@pytest.mark.parametrize('changed', ['source', 'harness', 'input'])
def test_provenance_change_during_child_aborts_publication(tmp_path, monkeypatch, changed):
    from test_reference_dataset import fixture_manifest
    from reference.reference_data import manifest_to_json
    source, revision = repository(tmp_path)
    root = tmp_path / 'dataset'
    root.mkdir()
    corpus = fixture_manifest(root)
    manifest = root / 'manifest.json'
    manifest.write_text(manifest_to_json(corpus))
    config = REFERENCE / 'capture-config.json'
    values = json.loads(config.read_text())
    mutated = False

    def child(command, cwd, timeout):
        nonlocal mutated
        if '--runtime' in command:
            return {'python': '3.13.13', 'architecture': '64bit',
                    'dependencies': {'Shapely': '2.1.2'}, 'harness_sha256': '0' * 64}
        mutated = True
        if changed == 'source':
            (source / 'camlib.py').write_text('changed')
        elif changed == 'input':
            (root / corpus['boards'][0]['files'][0]['path']).write_bytes(b'changed')
        return {'stages': capture._failed_stages(corpus['boards'][0], values, 'actual stage failed')}

    monkeypatch.setattr(capture, 'run_worker', child)
    monkeypatch.setattr(capture, '_harness_hash', lambda: ('2' if mutated and changed == 'harness' else '1') * 64)
    output = tmp_path / 'capture'
    with pytest.raises(ValueError):
        capture.capture_dataset('current', source, sys.executable, manifest, config,
                                output, revision, 5, corpus['boards'][0]['id'])
    assert not list(output.glob('*.json.gz'))


def test_worker_error_propagates_context_without_fake_downstream_results(tmp_path, monkeypatch):
    import capture_worker
    copper = tmp_path / 'copper.gbr'
    copper.write_bytes(b'input')
    request = {'source': str(Path.cwd()), 'root': str(tmp_path),
               'config': {'parameters': {}, 'stages': {'copper': ['gerber', 'isolation', 'cnc']}},
               'board': {'id': 'error-fixture', 'files': [
                   {'path': copper.name, 'role': 'copper', 'sha256': hashlib.sha256(b'input').hexdigest()}]}}
    monkeypatch.setattr(capture_worker, 'load_engine', lambda *args: SimpleNamespace())

    def fail(*args):
        raise RuntimeError('actual parser exception')

    monkeypatch.setattr(capture_worker, '_gerber', fail)
    stages = capture_worker.capture_board(request)['stages']
    assert len(stages) == 3
    assert all(s['status'] == 'error' and 'actual parser exception' in s['diagnostic']
               and not s['geometry_wkb'] and not s['paths'] and s['gcode'] is None for s in stages)
    copper.write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed'):
        capture_worker.capture_board(request)


def test_worker_wkb_is_planar_finite_and_preserves_ordered_paths():
    from shapely import from_wkb
    from shapely.geometry import LineString, Point
    import capture_worker
    points = [(3, 2), (1, 0), (3, 2)]
    encoded = capture_worker._wkb(LineString(points), ordered=True)[0]
    assert list(from_wkb(encoded).coords) == points
    for bad in [Point(1, 2, 3), Point(float('inf'), 0), Point()]:
        with pytest.raises(ValueError):
            capture_worker._wkb(bad)
