"""Placement behavior in mm, independent of Qt, the host and manufacturing hardware."""

from dataclasses import FrozenInstanceError
import json
import math
from pathlib import Path
import random
import subprocess
import sys

import pytest
from shapely import from_wkt, get_coordinates
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Point, Polygon, box

from mikrocam.core.placement import Placement


REFERENCE = json.loads((Path(__file__).parent / 'reference/placement.json').read_text())


@pytest.mark.parametrize('case', REFERENCE['cases'], ids=lambda case: case['name'])
def test_reference_point_and_geometry_use_the_same_placement(case):
    placement = Placement(**case['placement'])
    assert placement.apply_point(case['point']) == pytest.approx(case['expected'], abs=1e-9, rel=0)
    point = placement.apply_geometry(Point(case['point']))
    assert tuple(point.coords[0]) == pytest.approx(case['expected'], abs=1e-9, rel=0)
    assert placement.inverse().apply_point(case['expected']) == pytest.approx(case['point'], abs=1e-9, rel=0)


def test_pair_inputs_are_copied_to_immutable_finite_float_values():
    original = [1, 2]
    placement = Placement(origin=original, translation=[3, 4], rotation_deg=90)
    original[0] = 99
    assert placement.origin == (1.0, 2.0)
    assert placement.translation == (3.0, 4.0)
    assert all(isinstance(value, float) for value in placement.origin)
    with pytest.raises(FrozenInstanceError):
        placement.mirror_x = True


def test_point_sequences_preserve_order_and_do_not_mutate_sources():
    source = [[1, 2], [3, 4]]
    assert Placement(translation=(5, 6)).apply_points(iter(source)) == ((6, 8), (8, 10))
    assert source == [[1, 2], [3, 4]]
    assert Placement().apply_points([]) == ()


@pytest.mark.parametrize(('angle', 'expected'), [(0, (2, 3)), (90, (-3, 2)),
                                               (180, (-2, -3)), (270, (3, -2)), (450, (-3, 2))])
def test_cardinal_rotations_have_exact_zero_coefficients(angle, expected):
    assert Placement(rotation_deg=angle).apply_point((2, 3)) == expected


@pytest.mark.parametrize('points', [None, True, 3, '12'])
def test_malformed_point_sequences_fail_explicitly(points):
    with pytest.raises(ValueError):
        Placement().apply_points(points)


@pytest.mark.parametrize('kwargs', [
    {'origin': (1,)}, {'origin': (1, 2, 3)}, {'origin': None}, {'origin': '12'},
    {'origin': (True, 0)}, {'translation': ('1', 2)}, {'translation': (math.inf, 0)},
    {'rotation_deg': math.nan}, {'rotation_deg': True}, {'rotation_deg': '90'},
    {'rotation_deg': 10 ** 1000},
    {'mirror_x': 1}, {'mirror_x': 'false'},
])
def test_invalid_placement_fails_explicitly(kwargs):
    with pytest.raises(ValueError):
        Placement(**kwargs)


@pytest.mark.parametrize('point', [(1,), (1, 2, 3), None, '12', (True, 1),
                                  (math.nan, 1), (math.inf, 0), ('1', 2), (10 ** 1000, 0)])
def test_invalid_points_fail_explicitly(point):
    with pytest.raises(ValueError):
        Placement().apply_point(point)


def test_computed_overflow_is_not_silently_returned():
    with pytest.raises(ValueError, match='finite'):
        Placement(translation=(1e308, 0)).apply_point((1e308, 0))


@pytest.mark.parametrize('geometry', [
    Point(2, 3), LineString([(1, 2), (4, 5)]),
    Polygon([(0, 0), (8, 0), (8, 8), (0, 8)], holes=[[(2, 2), (2, 4), (4, 4), (4, 2)]]),
    MultiPolygon([box(0, 0, 1, 2), box(4, 5, 6, 7)]),
    GeometryCollection([Point(3, 4), LineString([(0, 0), (2, 3)])]),
    Point(), Polygon(), GeometryCollection(),
])
def test_geometry_preserves_topology_and_agrees_with_vertices(geometry):
    placement = Placement(origin=(5, -3), translation=(-7, 12), rotation_deg=37, mirror_x=True)
    original = geometry.wkb
    result = placement.apply_geometry(geometry)
    assert result.geom_type == geometry.geom_type
    assert result.is_empty == geometry.is_empty
    assert result.area == pytest.approx(geometry.area, abs=1e-9, rel=0)
    assert result.length == pytest.approx(geometry.length, abs=1e-9, rel=0)
    for point, expected in zip(get_coordinates(geometry), get_coordinates(result), strict=True):
        assert placement.apply_point(point) == pytest.approx(expected, abs=1e-9, rel=0)
    assert placement.inverse().apply_geometry(result).equals_exact(geometry, tolerance=1e-9)
    assert geometry.wkb == original


def test_one_hundred_deterministic_round_trips_and_determinants():
    randomizer = random.Random(412)
    geometry = box(-2, 3, 7, 9)
    for _ in range(100):
        placement = Placement(origin=tuple(randomizer.uniform(-100, 100) for _ in range(2)),
                              translation=tuple(randomizer.uniform(-500, 500) for _ in range(2)),
                              rotation_deg=randomizer.uniform(-720, 720),
                              mirror_x=randomizer.choice((True, False)))
        point = tuple(randomizer.uniform(-100, 100) for _ in range(2))
        assert placement.inverse().apply_point(placement.apply_point(point)) == pytest.approx(point, abs=1e-9, rel=0)
        result = placement.inverse().apply_geometry(placement.apply_geometry(geometry))
        assert result.equals_exact(geometry, tolerance=1e-9)
        a, b, d, e, _, _ = placement.matrix
        assert a * e - b * d == pytest.approx(-1 if placement.mirror_x else 1)


@pytest.mark.parametrize('geometry', [
    Point(1, 2, 3), from_wkt('POINT M (1 2 3)'), from_wkt('POINT ZM (1 2 3 4)'),
    GeometryCollection([Point(0, 1), Point(1, 2, 3)]),
    Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)]),
    Point(math.inf, 0),
])
def test_invalid_nonplanar_geometry_is_rejected(geometry):
    with pytest.raises(ValueError):
        Placement().apply_geometry(geometry)


def test_non_geometry_is_rejected():
    with pytest.raises(TypeError):
        Placement().apply_geometry([(1, 2), (3, 4)])


def test_placement_import_and_use_do_not_load_desktop_or_host_modules():
    code = ('import sys; from mikrocam.core.placement import Placement; '
            'assert Placement(translation=(1, 2)).apply_point((3, 4)) == (4, 6); '
            'assert not any(name.startswith(("PyQt", "vispy", "appMain", "camlib", "serial")) '
            'for name in sys.modules)')
    result = subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
