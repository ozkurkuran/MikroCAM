from copy import deepcopy

import pytest

from mikrocam.core.import_report import ImportCoordinates, ImportQuality, ImportReport
from mikrocam.core.import_report_codec import report_from_dict, report_to_dict
from mikrocam.core.svg_models import SvgNotice


def report():
    return ImportReport('kart-ö.svg', 'a' * 64,
                        ImportCoordinates(None, None, ('absent', 'absent'), (0, 0, 1, 2),
                                          'none', (1, 2), (1, 0, 0, 1, 0, 0), False),
                        ImportQuality((0, 0, 1, 1), 1, 1, 0, 0, 1, 0, 0.01),
                        (SvgNotice('x', '<plain> notice', 'e'),))


def test_schema_roundtrip_and_fresh_detached_containers():
    original = report()
    data = report_to_dict(original)
    assert data['schema_version'] == 2
    assert data['coordinates']['view_box'] == [0, 0, 1, 2]
    assert data['coordinates']['source_width'] is None
    assert report_from_dict(data) == original
    data['coordinates']['matrix_mm'][0] = 4
    data['notices'][0]['message'] = 'changed'
    assert report_to_dict(original)['coordinates']['matrix_mm'][0] == 1
    assert original.notices[0].message == '<plain> notice'


@pytest.mark.parametrize('section', [None, 'coordinates', 'quality', 'notice'])
@pytest.mark.parametrize('operation', ['missing', 'unknown'])
def test_exact_keys_at_every_level(section, operation):
    data = report_to_dict(report())
    target = data if section is None else data['notices'][0] if section == 'notice' else data[section]
    if operation == 'missing':
        del target[next(iter(target))]
    else:
        target['extra'] = 1
    with pytest.raises(ValueError):
        report_from_dict(data)


@pytest.mark.parametrize('version', [True, 0, 3, 1., '1', None])
def test_schema_version_has_no_coercion_or_future_guessing(version):
    data = report_to_dict(report())
    data['schema_version'] = version
    with pytest.raises(ValueError):
        report_from_dict(data)


@pytest.mark.parametrize('path,value', [
    (('coordinates', 'flipped'), 0), (('coordinates', 'matrix_mm'), [1, 0, 0, 0, 0, 0]),
    (('coordinates', 'viewport_mm'), [float('nan'), 1]),
    (('coordinates', 'source_units'), ('absent', 'absent')),
    (('quality', 'geometry_count'), True), (('quality', 'open_paths'), '1'),
    (('quality', 'precision_mm'), float('inf')), (('source_name',), 'x' * 257),
    (('source_name',), '\ud800'), (('notices',), [{}] * 201),
    (('notices',), ()), (('coordinates', 'view_box'), [0, 0, 1]),
])
def test_malformed_nested_types_and_values_reject(path, value):
    data = report_to_dict(report())
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        report_from_dict(data)


@pytest.mark.parametrize('value', [None, [], 'record', 1])
def test_nonrecord_and_unversioned_payloads_are_not_migrated(value):
    with pytest.raises(ValueError):
        report_from_dict(value)


def test_utf8_canonical_size_is_checked_on_both_directions(monkeypatch):
    import json
    from mikrocam.core import import_report_codec as codec
    original = report()
    data = report_to_dict(original)
    size = len(json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8'))
    monkeypatch.setattr(codec, 'MAX_REPORT_BYTES', size)
    assert report_from_dict(data) == original
    assert report_to_dict(original) == data
    monkeypatch.setattr(codec, 'MAX_REPORT_BYTES', size - 1)
    with pytest.raises(ValueError):
        report_from_dict(data)
    with pytest.raises(ValueError):
        report_to_dict(original)


def test_input_payload_is_never_mutated():
    data = report_to_dict(report())
    before = deepcopy(data)
    report_from_dict(data)
    assert data == before


@pytest.mark.parametrize('token,unit', [('garbage', 'mm'), ('0mm', 'mm'),
                                     ('10mm', 'in'), (None, 'mm'), ('10', 'px')])
def test_codec_rejects_contradictory_source_dimension_facts(token, unit):
    data = report_to_dict(report())
    data['coordinates']['source_width'] = token
    data['coordinates']['source_units'][0] = unit
    with pytest.raises(ValueError):
        report_from_dict(data)
