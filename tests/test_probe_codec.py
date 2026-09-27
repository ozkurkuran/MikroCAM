"""Strict exact schema, measured precision and bounded JSON behavior."""
import pytest

from mikrocam.core.probe_map import ProbeGrid, ProbeMap
from mikrocam.core.probe_codec import map_to_dict, map_from_dict, dumps_map, loads_map


def sample(outcome='failed'):
    heights = (.12345678901234567, -.75, None, None) if outcome != 'complete' else (.1, .2, .3, .4)
    return ProbeMap(ProbeGrid((-.25, 1.5), (2., 4.)), heights, (1., -2., .25), outcome, 'simulated')


def test_exact_schema_deterministic_full_and_partial_roundtrip():
    for value in (sample(), sample('complete')):
        data = map_to_dict(value)
        assert data == {'schema': 1, 'units': 'mm', 'grid': {'x_mm': [-.25, 1.5], 'y_mm': [2., 4.]},
                        'heights_mm': list(value.heights_mm), 'g54_offset_mm': [1., -2., .25],
                        'outcome': value.outcome, 'origin': 'simulated'}
        assert map_from_dict(data) == loads_map(dumps_map(value)) == value
        assert dumps_map(value) == dumps_map(value)
        assert 'NaN' not in dumps_map(value)


def test_returned_mutable_json_containers_do_not_alias_the_map_or_each_other():
    value = sample()
    data = map_to_dict(value)
    data['grid']['x_mm'][0] = 500
    data['heights_mm'][0] = 99
    assert value.grid.x_mm[0] == -.25 and value.heights_mm[0] != 99
    assert map_to_dict(value)['grid']['x_mm'][0] == -.25


@pytest.mark.parametrize('scope', ['root', 'grid'])
@pytest.mark.parametrize('action', ['missing', 'unknown'])
def test_exact_key_sets_are_required(scope, action):
    data = map_to_dict(sample())
    target = data if scope == 'root' else data['grid']
    if action == 'missing':
        target.pop(next(iter(target)))
    else:
        target['unexpected'] = 0
    with pytest.raises(ValueError):
        map_from_dict(data)


@pytest.mark.parametrize('field,value', [('schema', True), ('schema', 1.), ('schema', 2),
                                       ('units', 'MM'), ('units', 'in'), ('grid', []),
                                       ('heights_mm', (1, 2, None, None)),
                                       ('g54_offset_mm', (0, 0, 0)),
                                       ('outcome', 'ready'), ('origin', 'unknown')])
def test_schema_enum_and_array_types_are_strict(field, value):
    data = map_to_dict(sample())
    data[field] = value
    with pytest.raises(ValueError):
        map_from_dict(data)


@pytest.mark.parametrize('value', [False, '0', None, float('nan'), float('inf'), 1000001])
def test_invalid_numbers_never_coerce_or_enter_maps(value):
    data = map_to_dict(sample())
    data['grid']['x_mm'][0] = value
    with pytest.raises(ValueError):
        map_from_dict(data)


@pytest.mark.parametrize('text', ['{"schema":1,"schema":1}', '{"grid":{"x_mm":[],"x_mm":[]}}',
                                '{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}',
                                '[]', 'null', '', '[', '"text"'])
def test_duplicate_nonfinite_and_invalid_json_are_rejected(text):
    with pytest.raises(ValueError):
        loads_map(text)


def test_exponent_overflow_is_rejected_instead_of_becoming_infinity():
    text = dumps_map(sample()).replace(repr(sample().heights_mm[0]), '1e999')
    with pytest.raises(ValueError):
        loads_map(text)


@pytest.mark.parametrize('value', [None, b'{}', {}, 1, True, '\ud800'])
def test_load_requires_strict_utf8_text(value):
    with pytest.raises(ValueError):
        loads_map(value)


def test_json_size_bound_before_parsing_and_serialization(monkeypatch):
    import mikrocam.core.probe_codec as codec
    monkeypatch.setattr(codec, 'MAX_MAP_BYTES', 32)
    with pytest.raises(ValueError):
        loads_map(' ' * 33)
    with pytest.raises(ValueError):
        loads_map('é' * 17)
    with pytest.raises(ValueError):
        dumps_map(sample())


def test_excessive_json_nesting_is_a_validation_error():
    with pytest.raises(ValueError):
        loads_map('[' * 2000 + '0' + ']' * 2000)


@pytest.mark.parametrize('value', [None, {}, 'map'])
def test_serializer_requires_actual_map(value):
    with pytest.raises(ValueError):
        map_to_dict(value)
    with pytest.raises(ValueError):
        dumps_map(value)


def test_unit_value_requires_exact_string_even_for_direct_dictionary_api():
    class Unit(str):
        pass
    data = map_to_dict(sample())
    data['units'] = Unit('mm')
    with pytest.raises(ValueError):
        map_from_dict(data)


@pytest.mark.parametrize('heights', [(.1, None, None, None), (.1, .2, .3, .4)])
def test_incomplete_snapshot_roundtrip_never_infers_complete_from_point_count(heights):
    value = ProbeMap(ProbeGrid((0, 1), (0, 1)), heights, (0, 0, 0), 'incomplete', 'simulated')
    result = loads_map(dumps_map(value))
    assert result == value and result.outcome == 'incomplete' and not result.complete


@pytest.mark.parametrize('field,value', [('grid', {'x_mm': [[0], 1], 'y_mm': [0, 1]}),
                                       ('grid', {'x_mm': [0, {'value': 1}], 'y_mm': [0, 1]}),
                                       ('heights_mm', [{'value': .1}, None, None, None]),
                                       ('heights_mm', [[.1], None, None, None]),
                                       ('g54_offset_mm', [0, [0], 0]),
                                       ('g54_offset_mm', [0, {'value': 0}, 0])])
def test_nested_container_values_are_never_interpreted_as_measurements(field, value):
    import json
    data = map_to_dict(sample())
    data[field] = value
    with pytest.raises(ValueError):
        loads_map(json.dumps(data))


def test_extreme_integer_and_deep_nested_objects_fail_with_validation_errors():
    text = dumps_map(sample())
    for replacement in ('9' * 5000, '{"nested":' * 2000 + '0' + '}' * 2000):
        malformed = text.replace(repr(sample().heights_mm[0]), replacement)
        with pytest.raises(ValueError):
            loads_map(malformed)


def test_valid_map_at_exact_json_byte_boundary_and_one_byte_over():
    from mikrocam.core.probe_codec import MAX_MAP_BYTES
    text = dumps_map(sample())
    bounded = text + ' ' * (MAX_MAP_BYTES - len(text.encode('utf-8')))
    assert loads_map(bounded) == sample()
    with pytest.raises(ValueError, match='bounded|MiB'):
        loads_map(bounded + ' ')
