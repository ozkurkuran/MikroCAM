"""Strict configuration/capture codecs, provenance linkage and bounded gzip decoding."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

import pytest
from shapely import to_wkb
from shapely.geometry import LineString, box

from test_reference_dataset import fixture_manifest


CONFIG = Path(__file__).parent / 'reference/capture-config.json'


def example_capture(tmp_path):
    manifest = fixture_manifest(tmp_path)
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    digest = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    geometry = to_wkb(box(0, 0, 2, 2), hex=True, byte_order=1, flavor='iso', output_dimension=2)
    line = to_wkb(LineString([(0, 0), (2, 0)]), hex=True, byte_order=1, flavor='iso', output_dimension=2)
    stages = [dict(input_path='board-0/copper.gbr', stage=name, status='ok', units='mm',source_units='MM',
                   tools=[], geometry_wkb=[geometry] if name != 'cnc' else [],
                   paths=[dict(kind=['C','F'], wkb_hex=line)] if name == 'cnc' else [],
                   gcode='G90\nG01 X2 Y0\n' if name == 'cnc' else None, diagnostic=None)
              for name in ('gerber', 'isolation', 'cnc')]
    capture = dict(kind='mikrocam.reference-capture',schema_version=1,board_id='board-0',engine='evo',
        source=dict(revision='d0a86cf4f1ac41a206b20f316d4a29f28a93bbff',files=[dict(path='camlib.py',sha256='a'*64)]),
        runtime=dict(python='3.13.7',architecture='64bit',dependencies={'shapely':'2.1.2'},harness_sha256='b'*64),
        inputs=[dict(path=file['path'],sha256=file['sha256']) for file in manifest['boards'][0]['files']],
        configuration=dict(sha256=digest,requested=config,effective_optimization='N'),stages=stages)
    return capture, manifest, config


def test_fixed_configuration_has_explicit_probe_values_and_deterministic_codec():
    from reference.reference_data import load_config, config_from_json, config_to_json
    config = load_config(CONFIG)
    assert config['parameters']['cnc']['tooldia'] == .2
    assert config['parameters']['cnc']['z_cut'] == -.1
    assert config['parameters']['parser']['excellon']['excellon_format_lower_in'] == 4
    assert config_from_json(config_to_json(config)) == config


@pytest.mark.parametrize('mutation',[lambda d:d.update(schema_version=2),lambda d:d.update(extra=1),
    lambda d:d['parameters']['cnc'].pop('feedrate'),lambda d:d['parameters']['cnc'].update(feedrate=True),
    lambda d:d['parameters']['cnc'].update(feedrate=float('inf')),lambda d:d['parameters']['cnc'].update(tooldia=0),
    lambda d:d['parameters']['parser']['gerber'].update(gerber_circle_steps=1.5),
    lambda d:d['parameters']['parser']['excellon'].update(zeros='guess'),
    lambda d:d['stages'].update(copper=['gerber','gerber']),lambda d:d['stages'].pop('archive')])
def test_configuration_never_falls_back_missing_or_invalid_parameters(mutation):
    from reference.reference_data import validate_config
    data=json.loads(CONFIG.read_text(encoding='utf-8'))
    mutation(data)
    with pytest.raises(ValueError):
        validate_config(data)


def test_capture_roundtrip_provenance_linkage_and_deterministic_gzip(tmp_path):
    from reference.reference_data import validate_capture, write_capture, load_capture
    capture,manifest,config=example_capture(tmp_path)
    assert validate_capture(capture,manifest=manifest,config=config,expected_engine='evo',expected_board='board-0')==capture
    first,second=tmp_path/'one.gz',tmp_path/'two.gz'
    write_capture(first,capture)
    write_capture(second,capture)
    assert first.read_bytes()==second.read_bytes()
    assert load_capture(first,manifest=manifest,config=config)==capture
    with pytest.raises(FileExistsError):
        write_capture(first,capture)


@pytest.mark.parametrize('mutation',[lambda d:d.update(schema_version=True),lambda d:d.update(extra=1),
    lambda d:d['source'].update(revision='main'),lambda d:d['source']['files'][0].update(path='../camlib.py'),
    lambda d:d['runtime'].update(architecture='32bit'),lambda d:d['runtime'].update(python='3.14.0'),
    lambda d:d['configuration'].update(sha256='0'*64),lambda d:d['configuration'].update(effective_optimization='RTree'),
    lambda d:d['stages'].pop(),lambda d:d['stages'].append(deepcopy(d['stages'][0])),
    lambda d:d['stages'][0].update(units='in'),lambda d:d['stages'][0].update(source_units='CM'),
    lambda d:d['stages'][0].update(geometry_wkb=['garbage']),
    lambda d:d['stages'][2]['paths'][0].update(kind=[]),lambda d:d['inputs'][0].update(sha256='f'*64)])
def test_capture_rejects_bad_provenance_missing_duplicate_invalid_stages(tmp_path,mutation):
    from reference.reference_data import validate_capture
    capture,manifest,config=example_capture(tmp_path)
    mutation(capture)
    with pytest.raises(ValueError):
        validate_capture(capture,manifest=manifest,config=config)


def test_real_failure_is_retained_without_fake_geometry(tmp_path):
    from reference.reference_data import validate_capture
    capture,manifest,config=example_capture(tmp_path)
    stage=capture['stages'][1]
    stage.update(status='error',geometry_wkb=[],diagnostic='Actual baseline parser exception')
    assert validate_capture(capture,manifest=manifest,config=config)['stages'][1]['status']=='error'
    stage['geometry_wkb']=capture['stages'][0]['geometry_wkb']
    with pytest.raises(ValueError):
        validate_capture(capture)


def test_gzip_corruption_duplicate_keys_and_decoded_limit_are_invalid(tmp_path,monkeypatch):
    import reference.reference_data as codec
    capture,_manifest,_config=example_capture(tmp_path)
    path=tmp_path/'broken.gz'
    path.write_bytes(b'not gzip')
    with pytest.raises(ValueError):
        codec.load_capture(path)
    text=json.dumps(capture).replace('"schema_version": 1','"schema_version": 1,"schema_version": 1',1)
    with pytest.raises(ValueError,match='duplicate'):
        codec.capture_from_json(text)
    path.write_bytes(gzip.compress(json.dumps(capture).encode()))
    monkeypatch.setattr(codec,'MAX_JSON_BYTES',20)
    with pytest.raises(ValueError,match='limit|size'):
        codec.load_capture(path)


def test_excellon_json_slots_unused_tools_and_duplicate_hits_roundtrip(tmp_path):
    from reference.reference_data import capture_to_json, capture_from_json
    capture, _, _ = example_capture(tmp_path)
    stage = capture['stages'][0]
    stage.update(stage='excellon', source_units='IN', tools=[
        dict(id='1', diameter_mm=.8, drills=[[1, 2], [1, 2]], slots=[[[0, 0], [2, 0]]]),
        dict(id='2', diameter_mm=1.0, drills=[], slots=[])])
    assert capture_from_json(capture_to_json(capture)) == capture


@pytest.mark.parametrize('python', ['3.13.garbage', '3.13.7-extra', '3.13.7.1'])
def test_runtime_python_requires_exact_numeric_version(tmp_path, python):
    from reference.reference_data import validate_capture
    capture, _, _ = example_capture(tmp_path)
    capture['runtime']['python'] = python
    with pytest.raises(ValueError):
        validate_capture(capture)


def test_drill_resource_limits_are_aggregate_and_checked_before_conversion(tmp_path, monkeypatch):
    import reference.reference_capture_data as codec
    capture, _, _ = example_capture(tmp_path)
    stage = capture['stages'][0]
    stage.update(stage='excellon', tools=[
        dict(id='1', diameter_mm=.8, drills=[[0, 0], [1, 1]], slots=[]),
        dict(id='2', diameter_mm=.9, drills=[[2, 2], [3, 3]], slots=[])])
    monkeypatch.setattr(codec, 'MAX_VERTICES', 3)
    with pytest.raises(ValueError, match='vertex|resource'):
        codec.validate_capture(capture)
    monkeypatch.setattr(codec, 'MAX_VERTICES', 100)
    monkeypatch.setattr(codec, 'MAX_PATHS', 1)
    with pytest.raises(ValueError, match='count|resource'):
        codec.validate_capture(capture)


@pytest.mark.parametrize('existing', [False, True])
def test_failed_capture_write_is_atomic_and_cleans_temporary_file(tmp_path, monkeypatch, existing):
    import reference.reference_capture_data as codec
    capture, _, _ = example_capture(tmp_path)
    destination = tmp_path / 'capture.json.gz'
    if existing:
        destination.write_bytes(b'original')
    before = {path.name for path in tmp_path.iterdir()}
    def broken_write(self, data):
        raise OSError('simulated gzip write failure')
    monkeypatch.setattr(codec.gzip.GzipFile, 'write', broken_write)
    with pytest.raises(OSError):
        codec.write_capture(destination, capture)
    assert destination.read_bytes() == b'original' if existing else not destination.exists()
    assert {path.name for path in tmp_path.iterdir()} == before


@pytest.mark.parametrize('mutation', [lambda d: d.update(engine=[]),
    lambda d: d['stages'][0].update(stage={}), lambda d: d['stages'][0].update(status=[]),
    lambda d: d['stages'][0].update(source_units={})])
def test_wrong_capture_enum_types_are_value_errors(tmp_path, mutation):
    from reference.reference_data import validate_capture
    capture, _, _ = example_capture(tmp_path)
    mutation(capture)
    with pytest.raises(ValueError):
        validate_capture(capture)


def test_atomic_publication_failure_leaves_no_target_or_temporary(tmp_path, monkeypatch):
    import reference.reference_capture_data as codec
    capture, _, _ = example_capture(tmp_path)
    before = {path.name for path in tmp_path.iterdir()}
    def broken_link(source, destination):
        raise OSError('simulated publication failure')
    monkeypatch.setattr(codec.os, 'link', broken_link)
    with pytest.raises(OSError, match='publication'):
        codec.write_capture(tmp_path / 'capture.gz', capture)
    assert {path.name for path in tmp_path.iterdir()} == before


def test_decoded_json_limit_counts_utf8_bytes_and_accepts_exact_boundary(tmp_path, monkeypatch):
    import reference.reference_data as codec
    capture, _, _ = example_capture(tmp_path)
    capture['stages'][1].update(status='error', geometry_wkb=[], diagnostic='Parser error: \u03c0')
    text = codec.capture_to_json(capture)
    byte_count = len(text.encode('utf-8'))
    assert byte_count > len(text)
    path = tmp_path / 'bounded.gz'
    path.write_bytes(gzip.compress(text.encode('utf-8')))
    monkeypatch.setattr(codec, 'MAX_JSON_BYTES', byte_count)
    assert codec.capture_from_json(text) == capture
    assert codec.capture_to_json(capture) == text
    assert codec.load_capture(path) == capture
    monkeypatch.setattr(codec, 'MAX_JSON_BYTES', byte_count - 1)
    for operation in (lambda: codec.capture_from_json(text), lambda: codec.capture_to_json(capture),
                      lambda: codec.load_capture(path), lambda: codec.write_capture(tmp_path / 'rejected.gz', capture)):
        with pytest.raises(ValueError, match='limit|size'):
            operation()
    assert not (tmp_path / 'rejected.gz').exists()
