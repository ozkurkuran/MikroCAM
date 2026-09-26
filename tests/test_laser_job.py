"""Explicit laser values and detached planar copper, without host defaults."""
from dataclasses import FrozenInstanceError
import math

import pytest
from shapely import from_wkt
from shapely.affinity import scale
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Polygon, box

from mikrocam.core.placement import Placement


def recipe():
    from mikrocam.core.laser_job import LaserPass, LaserRecipe
    return LaserRecipe('two passes', (LaserPass('first', 20, 250, 30, 100),
                                      LaserPass('second', 40, 500, 60, 200)))


def test_pass_recipe_values_are_explicit_ordered_and_frozen():
    value = recipe()
    assert [item.name for item in value.passes] == ['first', 'second']
    assert value.passes[0].speed_mm_s == 250
    with pytest.raises(FrozenInstanceError):
        value.name = 'changed'
    with pytest.raises(FrozenInstanceError):
        value.passes[0].power_percent = 90
    from mikrocam.core.laser_job import LaserPass
    with pytest.raises(TypeError):
        LaserPass('missing')


@pytest.mark.parametrize('field', ['power_percent', 'speed_mm_s', 'frequency_khz', 'pulse_width_ns'])
@pytest.mark.parametrize('invalid', [True, False, 0, -1, math.nan, math.inf, -math.inf, '20', None, 10**400])
def test_pass_parameters_reject_implicit_or_nonpositive_nonfinite_values(field, invalid):
    from mikrocam.core.laser_job import LaserPass
    data = dict(name='explicit', power_percent=20, speed_mm_s=250, frequency_khz=30, pulse_width_ns=100)
    data[field] = invalid
    with pytest.raises(ValueError, match=field):
        LaserPass(**data)


def test_power_ceiling_and_recipe_names_and_pass_types():
    from mikrocam.core.laser_job import LaserPass, LaserRecipe
    first = LaserPass('first', 100, 1, 1, 1)
    with pytest.raises(ValueError, match='power_percent'):
        LaserPass('too high', 100.001, 1, 1, 1)
    for name in ['', ' \t', None, 1]:
        with pytest.raises(ValueError, match='name'):
            LaserRecipe(name, (first,))
        with pytest.raises(ValueError, match='name'):
            LaserPass(name, 20, 1, 1, 1)
    for passes in [(), (first, first), ('invalid',), [first], None]:
        with pytest.raises(ValueError):
            LaserRecipe('recipe', passes)


def test_region_keeps_holes_parts_and_canonical_plain_data():
    from mikrocam.core.laser_job import PlanarRegion
    hole = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)], [[(1, 1), (2, 1), (2, 2), (1, 2)]])
    source = MultiPolygon([hole, box(8, 0, 9, 1)])
    region = PlanarRegion.from_geometry(source)
    assert isinstance(region.wkb_hex, str)
    assert region.to_geometry().equals(source)
    assert len(region.to_geometry().geoms) == 2
    assert sum(len(part.interiors) for part in region.to_geometry().geoms) == 1
    assert PlanarRegion.from_geometry(MultiPolygon(list(reversed(source.geoms)))) == region
    with pytest.raises(FrozenInstanceError):
        region.wkb_hex = ''


@pytest.mark.parametrize('source', [Polygon(), box(0, 0, 1, 1).boundary,
    Polygon([(0, 0), (1, 1), (0, 1), (1, 0)]),
    from_wkt('POLYGON Z ((0 0 1, 1 0 1, 1 1 1, 0 0 1))'),
    from_wkt('POLYGON M ((0 0 1, 1 0 1, 1 1 1, 0 0 1))'),
    from_wkt('POLYGON ((0 0, 1 0, 1 Infinity, 0 0))')])
def test_invalid_nonplanar_nonpolygon_regions_are_rejected(source):
    from mikrocam.core.laser_job import PlanarRegion
    with pytest.raises(ValueError):
        PlanarRegion.from_geometry(source)


def test_invalid_geometry_object_and_wkb_fail_explicitly():
    from mikrocam.core.laser_job import PlanarRegion
    with pytest.raises(TypeError):
        PlanarRegion.from_geometry('polygon')
    for value in ['', 'nothex', None, 42, '01000000']:
        with pytest.raises(ValueError, match='WKB'):
            PlanarRegion(value)
    region = PlanarRegion.from_geometry(box(0, 0, 1, 1))
    with pytest.raises(ValueError, match='WKB'):
        PlanarRegion(region.wkb_hex + '00')


def test_job_uses_existing_placement_once_and_keeps_source(monkeypatch):
    from mikrocam.core.laser_job import LaserJob, PlanarRegion
    region = PlanarRegion.from_geometry(box(1, 2, 3, 5))
    placement = Placement(origin=(1, 2), translation=(20, 30), rotation_deg=90, mirror_x=True)
    job = LaserJob('job', region, recipe(), placement)
    expected = placement.apply_geometry(region.to_geometry())
    original = Placement.apply_geometry
    calls = []
    def apply(self, geometry):
        calls.append(geometry)
        return original(self, geometry)
    monkeypatch.setattr(Placement, 'apply_geometry', apply)
    assert job.placed_geometry().equals_exact(expected, 1e-12)
    assert len(calls) == 1
    assert job.region == region and region.to_geometry().bounds == (1, 2, 3, 5)
    with pytest.raises(FrozenInstanceError):
        job.name = 'changed'
    for name, geometry, passes, transform in [('', region, recipe(), placement),
                                             ('job', 'region', recipe(), placement),
                                             ('job', region, 'recipe', placement),
                                             ('job', region, recipe(), 'placement')]:
        with pytest.raises(ValueError):
            LaserJob(name, geometry, passes, transform)


def test_polygon_collection_unions_copper_and_converts_current_units_once():
    from mikrocam.core.laser_job import region_from_polygons
    first = box(0, 0, 2, 2)
    second = box(1, 0, 3, 2)
    hole = Polygon([(5, 0), (9, 0), (9, 4), (5, 4)], [[(6, 1), (7, 1), (7, 2), (6, 2)]])
    nested = [[first], (GeometryCollection([second, MultiPolygon([hole])]),)]
    mm = region_from_polygons(nested, ' mm ').to_geometry()
    inch = region_from_polygons(nested, 'in').to_geometry()
    assert mm.area == 21
    assert inch.equals_exact(scale(mm, 25.4, 25.4, origin=(0, 0)), 1e-9)
    assert sum(len(part.interiors) for part in inch.geoms) == 1
    assert first.bounds == (0, 0, 2, 2) and second.bounds == (1, 0, 3, 2)


@pytest.mark.parametrize('units', ['', 'CM', 'inch', None, 1])
def test_units_are_not_guessed(units):
    from mikrocam.core.laser_job import region_from_polygons
    with pytest.raises(ValueError, match='units'):
        region_from_polygons(box(0, 0, 1, 1), units)


@pytest.mark.parametrize('geometry', [[], (), None, GeometryCollection(), [box(0, 0, 1, 1), LineString([(0, 0), (1, 1)])],
                                     [box(0, 0, 1, 1), Polygon()]])
def test_collection_rejects_empty_and_nonpolygon_components(geometry):
    from mikrocam.core.laser_job import region_from_polygons
    with pytest.raises(ValueError):
        region_from_polygons(geometry, 'MM')
