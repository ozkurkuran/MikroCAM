"""SVG topology and polygon adapters beyond the baseline fixtures."""

import numpy as np
import pytest
from matplotlib.path import Path
from shapely.geometry import Polygon
from svg.path import parse_path

from appParsers.ParseSVG import path2shapely
from descartes.patch import PolygonPath


def test_svg_nested_rings_are_order_independent():
    path = parse_path(
        'M2,2 L8,2 L8,8 L2,8 Z '
        'M3,3 L4,3 L4,4 L3,4 Z '
        'M0,0 L10,0 L10,10 L0,10 Z'
    )
    polygons = path2shapely(path, 'geometry')
    assert sorted(p.area for p in polygons) == pytest.approx([1, 64])
    assert sum(len(p.interiors) for p in polygons) == 1
    assert all(p.is_valid for p in polygons)


def test_svg_closed_coordinates_without_close_stay_a_line():
    result = path2shapely(parse_path('M0,0 L2,0 L2,2 L0,0 M9,9'), 'geometry')
    assert len(result) == 1
    assert result[0].geom_type == 'LineString'
    assert list(result[0].coords) == [(0, 0), (2, 0), (2, 2), (0, 0)]


@pytest.mark.parametrize('curve', [
    'M1,2 C2,5 5,7 8,9',
    'M1,2 Q2,5 8,9',
    'M1,2 A4,3 0 0,1 8,9',
])
def test_svg_curve_scaling_is_applied_once(curve):
    original = path2shapely(parse_path(curve), 'geometry')[0]
    scaled = path2shapely(parse_path(curve), 'geometry', factor=2)[0]
    np.testing.assert_allclose(scaled.coords, np.asarray(original.coords) * 2)
    assert scaled.geom_type == 'LineString'


def test_polygon_path_accepts_geojson_and_empty_coordinates():
    polygon = Polygon([(0, 0), (3, 0), (3, 3)], [[(1, 1), (2, 1), (2, 2)]])
    actual = PolygonPath(polygon.__geo_interface__)
    expected = PolygonPath(polygon)
    np.testing.assert_array_equal(actual.vertices, expected.vertices)
    np.testing.assert_array_equal(actual.codes, expected.codes)
    assert np.count_nonzero(actual.codes == Path.MOVETO) == 2
    assert PolygonPath({'type': 'Polygon', 'coordinates': []}).vertices.shape == (0, 2)


def test_polygon_path_projects_three_dimensional_rings_to_xy():
    polygon = Polygon([(0, 0, 7), (3, 0, 7), (3, 3, 7)])
    path = PolygonPath(polygon)
    assert path.vertices.shape == (4, 2)
    np.testing.assert_array_equal(path.vertices, np.asarray(polygon.exterior.coords)[:, :2])
