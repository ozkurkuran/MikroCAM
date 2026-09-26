"""Strict schema-one recipe/job exchange, independent of Evo persistence."""
import json
from pathlib import Path

import pytest
from shapely.geometry import MultiPolygon, Polygon, box

from mikrocam.core.placement import Placement


REFERENCE = Path(__file__).parent / 'reference/laser_recipe_v1.json'


def recipe_text():
    return json.dumps({'kind': 'mikrocam.laser-recipe', 'schema_version': 1, 'name': 'Synthetic two-pass recipe',
                       'passes': [dict(name='first', power_percent=20, speed_mm_s=250,
                                       frequency_khz=30, pulse_width_ns=100),
                                  dict(name='second', power_percent=40, speed_mm_s=500,
                                       frequency_khz=60, pulse_width_ns=200)]})


def test_reference_recipe_order_values_and_deterministic_roundtrip():
    from mikrocam.core.laser_json import recipe_from_json, recipe_to_json
    recipe = recipe_from_json(REFERENCE.read_text(encoding='utf-8'))
    assert [item.name for item in recipe.passes] == ['first', 'second']
    assert recipe.passes[1].frequency_khz == 60
    encoded = recipe_to_json(recipe)
    assert recipe_from_json(encoded) == recipe
    assert recipe_to_json(recipe_from_json(encoded)) == encoded
    assert json.loads(encoded) == json.loads(recipe_text())


@pytest.mark.parametrize('mutation', [lambda data: data.update(schema_version=2),
    lambda data: data.update(schema_version=True), lambda data: data.update(schema_version=1.0),
    lambda data: data.update(kind='evo.project'), lambda data: data.update(extra=True),
    lambda data: data.pop('name'), lambda data: data.update(passes=[]),
    lambda data: data['passes'][0].pop('frequency_khz'),
    lambda data: data['passes'][0].update(z_cut=-0.1),
    lambda data: data['passes'][1].update(name='first'),
    lambda data: data['passes'][0].update(speed_mm_s='250'),
    lambda data: data['passes'][0].update(power_percent=True)])
def test_recipe_rejects_missing_unknown_future_or_invalid_values(mutation):
    from mikrocam.core.laser_json import recipe_from_json
    data = json.loads(recipe_text())
    mutation(data)
    with pytest.raises(ValueError):
        recipe_from_json(json.dumps(data))


@pytest.mark.parametrize('text', ['null', '[]', '{', recipe_text().replace('"name": "first"', '"name": "first", "name": "second"'),
    recipe_text().replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'),
    recipe_text().replace('"power_percent": 20', '"power_percent": NaN'),
    recipe_text().replace('"power_percent": 20', '"power_percent": Infinity')])
def test_ambiguous_json_and_nonfinite_literals_fail(text):
    from mikrocam.core.laser_json import recipe_from_json
    with pytest.raises(ValueError):
        recipe_from_json(text)


def make_job():
    from mikrocam.core.laser_job import LaserJob, PlanarRegion
    from mikrocam.core.laser_json import recipe_from_json
    hole = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)], [[(1, 1), (2, 1), (2, 2), (1, 2)]])
    region = PlanarRegion.from_geometry(MultiPolygon([hole, box(8, 0, 9, 1)]))
    return LaserJob('Unicode copper μ', region, recipe_from_json(recipe_text()),
                    Placement(origin=(1, 2), translation=(20, 30), rotation_deg=45, mirror_x=True))


def test_job_roundtrip_preserves_region_recipe_placement_and_determinism():
    from mikrocam.core.laser_json import job_from_json, job_to_json
    job = make_job()
    encoded = job_to_json(job)
    restored = job_from_json(encoded)
    assert restored == job
    assert restored.placed_geometry().equals_exact(job.placed_geometry(), 1e-12)
    assert job_to_json(restored) == encoded
    assert 'μ' in encoded
    data = json.loads(encoded)
    assert data['units'] == 'mm' and data['schema_version'] == 1
    assert data['recipe']['kind'] == 'mikrocam.laser-recipe'
    assert data['placement'] == {'origin': [1, 2], 'translation': [20, 30], 'rotation_deg': 45, 'mirror_x': True}


@pytest.mark.parametrize('mutation', [lambda data: data.update(schema_version=2),
    lambda data: data.update(units='in'), lambda data: data.update(region_wkb_hex='invalid'),
    lambda data: data.update(gcode='M3'), lambda data: data.pop('placement'),
    lambda data: data['placement'].pop('rotation_deg'),
    lambda data: data['placement'].update(offset=[1, 2]),
    lambda data: data['placement'].update(origin=[1]),
    lambda data: data['placement'].update(translation='12'),
    lambda data: data['placement'].update(mirror_x=1),
    lambda data: data['recipe'].update(schema_version=5),
    lambda data: data['recipe']['passes'][0].pop('pulse_width_ns')])
def test_job_rejects_unversioned_or_incomplete_nested_data(mutation):
    from mikrocam.core.laser_json import job_from_json, job_to_json
    data = json.loads(job_to_json(make_job()))
    mutation(data)
    with pytest.raises(ValueError):
        job_from_json(json.dumps(data))


def test_duplicate_nested_placement_and_overflowed_json_numbers_fail():
    from mikrocam.core.laser_json import job_from_json, job_to_json, recipe_from_json
    text = job_to_json(make_job())
    with pytest.raises(ValueError, match='duplicate'):
        job_from_json(text.replace('"mirror_x":true', '"mirror_x":true,"mirror_x":false'))
    with pytest.raises(ValueError, match='power_percent'):
        recipe_from_json(recipe_text().replace('"power_percent": 20', '"power_percent": 1e400'))
