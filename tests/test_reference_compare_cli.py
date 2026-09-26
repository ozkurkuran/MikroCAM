"""Offline reports never treat unavailable or changed machining evidence as a match."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

import pytest
from shapely import to_wkb
from shapely.affinity import translate
from shapely.geometry import box

from test_reference_data_codecs import example_capture


def save(path, data):
    path.write_bytes(gzip.compress(json.dumps(data).encode(), mtime=0))


def comparison_case(tmp_path):
    boards = tmp_path / 'boards'
    capture, manifest, config = example_capture(boards)
    manifest_path, config_path = boards / 'manifest.json', tmp_path / 'config.json'
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    config_path.write_text(json.dumps(config), encoding='utf-8')
    expected, candidate = tmp_path / 'expected', tmp_path / 'candidate'
    expected.mkdir()
    candidate.mkdir()
    for board in manifest['boards']:
        data = deepcopy(capture)
        data['board_id'] = board['id']
        data['inputs'] = [dict(path=file['path'], sha256=file['sha256']) for file in board['files']]
        for stage in data['stages']:
            stage['input_path'] = f"{board['id']}/copper.gbr"
        save(expected / f"{board['id']}.json.gz", data)
        save(candidate / f"{board['id']}.json.gz", data)
    report = tmp_path / 'report.json'
    args = ['--baseline', 'evo', '--goldens', str(expected), '--candidate', str(candidate),
            '--manifest', str(manifest_path), '--config', str(config_path),
            '--distance-mm', '0.001', '--area-mm2', '0.001', '--report', str(report)]
    return args, expected, candidate, report


def mutate(path, change):
    data = json.loads(gzip.decompress(path.read_bytes()))
    change(data)
    save(path, data)


def test_offline_matching_report_does_not_modify_any_capture(tmp_path):
    from reference.compare import main
    args, expected, candidate, report = comparison_case(tmp_path)
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest()
              for directory in (expected, candidate) for path in directory.iterdir()}
    assert main(args) == 0
    result = json.loads(report.read_text(encoding='utf-8'))
    assert result['outcome'] == 'match' and len(result['results']) == 30
    assert all(item['outcome'] == 'match' for item in result['results'])
    assert {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in before} == before
    assert main(args) == 2  # The explicit report path also cannot overwrite existing data.


@pytest.mark.parametrize('change', [
    lambda d: d['stages'][0].update(geometry_wkb=[to_wkb(translate(box(0,0,2,2), xoff=.1),
                                                    hex=True, byte_order=1, flavor='iso')]),
    lambda d: d['stages'][2].update(gcode='G90\nG01 X2 Y0 F999\n'),
    lambda d: d['stages'][2]['paths'][0].update(kind=['T','F'])])
def test_real_geometry_emitted_parameter_or_path_changes_report_difference(tmp_path, change):
    from reference.compare import main
    args, _, candidate, report = comparison_case(tmp_path)
    mutate(candidate / 'board-0.json.gz', change)
    assert main(args) == 1
    result = json.loads(report.read_text(encoding='utf-8'))
    assert result['outcome'] == 'difference'
    assert any(item['board_id'] == 'board-0' and item['outcome'] == 'difference'
               for item in result['results'])


@pytest.mark.parametrize('status', ['error', 'unsupported'])
def test_repeated_real_baseline_failures_remain_indeterminate(tmp_path, status):
    from reference.compare import main
    args, expected, candidate, report = comparison_case(tmp_path)
    def failure(data):
        data['stages'][1].update(status=status, geometry_wkb=[], diagnostic='Actual unavailable CAM evidence')
    mutate(expected / 'board-0.json.gz', failure)
    mutate(candidate / 'board-0.json.gz', failure)
    assert main(args) == 2
    result = json.loads(report.read_text(encoding='utf-8'))
    assert result['outcome'] == 'indeterminate'
    assert any(item['stage'] == 'isolation' and item['outcome'] == 'indeterminate'
               for item in result['results'])


@pytest.mark.parametrize('change', [lambda d: d['stages'].pop(),
    lambda d: d['inputs'][0].update(sha256='c'*64),
    lambda d: d['configuration'].update(sha256='c'*64),
    lambda d: d['runtime']['dependencies'].update(shapely='2.0.0'),
    lambda d: d['stages'][2].update(paths=[]),
    lambda d: d['stages'][2].update(gcode='G1 X[unknown]')])
def test_invalid_incomplete_or_changed_runtime_evidence_cannot_pass(tmp_path, change):
    from reference.compare import main
    args, _, candidate, report = comparison_case(tmp_path)
    mutate(candidate / 'board-0.json.gz', change)
    assert main(args) == 2
    result = json.loads(report.read_text(encoding='utf-8'))
    assert result['outcome'] == 'indeterminate' and any(item['diagnostic'] for item in result['results'])


def test_corrupt_and_missing_capture_files_are_contextual(tmp_path):
    from reference.compare import main
    args, expected, candidate, report = comparison_case(tmp_path)
    (candidate / 'board-0.json.gz').write_bytes(b'bad gzip')
    (expected / 'board-1.json.gz').unlink()
    assert main(args) == 2
    result = json.loads(report.read_text(encoding='utf-8'))
    invalid = [item for item in result['results'] if item['outcome'] == 'indeterminate']
    assert {item['board_id'] for item in invalid} == {'board-0', 'board-1'}


def test_report_cannot_be_published_inside_golden_directory(tmp_path):
    from reference.compare import main
    args, expected, _, _ = comparison_case(tmp_path)
    args[-1] = str(expected / 'new-report.json')
    assert main(args) == 2 and not Path(args[-1]).exists()
