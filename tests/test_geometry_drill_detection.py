"""Current geometry is the authority; no source reparse or CAM transform."""
import math

import pytest
from shapely.affinity import rotate, scale
from shapely.geometry import GeometryCollection, LinearRing, LineString, MultiPolygon, Point, Polygon

from mikrocam.core.geometry_drills import review_geometry_sources


def review(geometry, units='MM', name='board'):
    return review_geometry_sources((('geometry', geometry),), name, units)


def disk(x=10, y=12, r=1):
    return Point(x, y).buffer(r, quad_segs=64)


def test_polygon_rings_roles_and_exact_source_preserved():
    geometry = Polygon(disk(r=3).exterior.coords, [disk(r=1).exterior.coords])
    before = geometry.wkb
    result = review(geometry)
    assert [c.role for c in result.candidates] == ['exterior', 'interior']
    assert [c.diameter_mm for c in result.candidates] == pytest.approx([6, 2])
    assert all(c.center_mm == pytest.approx((10, 12)) for c in result.candidates)
    assert len({c.source_id for c in result.candidates}) == 2
    assert geometry.wkb == before
    assert result == review(geometry)


def test_units_and_transformed_current_geometry():
    geometry = rotate(scale(disk(0, 0), 2, 2), 31)
    a = review(geometry)
    b = review(scale(geometry, 1/25.4, 1/25.4, origin=(0, 0)), 'IN')
    assert a.candidates[0].diameter_mm == pytest.approx(4)
    assert b.candidates[0].diameter_mm == pytest.approx(4)
    assert review(scale(geometry, 2, 1)).candidates == ()


def test_nested_multipart_order_and_duplicate_roles():
    a, b = disk(), disk(20)
    result = review([MultiPolygon([a, b]), (LineString(a.exterior.coords),)])
    assert len(result.candidates) == 2
    assert result.candidates[0].duplicate_count == 1
    assert result.candidates[0].role == 'exterior'
    assert any('duplicate' in n.lower() for n in result.notices)


def test_non_chaining_duplicates_keep_first_measurement():
    result = review([disk(0), disk(.015), disk(.03)])
    assert len(result.candidates) == 2
    assert result.candidates[0].center_mm == pytest.approx((0, 12), abs=1e-12)
    assert result.candidates[0].duplicate_count == 1


@pytest.mark.parametrize('geometry', [Point(0, 0), Polygon(), LineString([(0, 0), (1, 1)]),
    Point(0, 0).buffer(1, quad_segs=2), scale(disk(), 1.2, 1)])
def test_valid_noncircles_excluded_with_notice(geometry):
    result = review(geometry)
    assert result.candidates == ()
    assert result.notices


@pytest.mark.parametrize('geometry', [None, {}, iter([]),
    LineString([(0, 0, 0), (1, 1, 0)]), Point(math.inf, 0),
    Polygon([(0, 0), (1, 1), (0, 1), (1, 0), (0, 0)]), disk(1e9, 0, 10)])
def test_invalid_geometry_rejects_entire_review(geometry):
    with pytest.raises(ValueError):
        review([disk(), geometry])


def test_fingerprint_covers_name_units_label_type_and_geometry():
    original = review(disk()).geometry_sha256
    variants = [review(disk(), name='renamed'), review(disk(), units='IN'),
                review([disk()]), review((disk(),)), review(disk(11)),
                review_geometry_sources((('tool:int:1', disk()),), 'board', 'MM')]
    assert all(v.geometry_sha256 != original for v in variants)
    assert len({v.geometry_sha256 for v in variants}) == len(variants)


def test_bounded_cycles_nodes_coordinates_candidates_and_notices():
    cycle = []; cycle.append(cycle)
    with pytest.raises(ValueError, match='depth|budget'):
        review(cycle)
    with pytest.raises(ValueError, match='budget|nodes'):
        review([Point()] * 10001)
    with pytest.raises(ValueError, match='contour|points'):
        review(LineString([(0, 0), (1, 1)] * 50001))
    with pytest.raises(ValueError, match='candidate'):
        review([Point(i * 3, 0).buffer(.1, quad_segs=8) for i in range(1001)])
    result = review([Point(i, 0) for i in range(300)])
    assert len(result.notices) == 200
    assert 'omitted' in result.notices[-1]


@pytest.mark.parametrize('sources', [[], (('x', disk()), ('x', disk())),
    (('', disk()),), (('x',),), ((True, disk()),)])
def test_strict_sources(sources):
    with pytest.raises(ValueError):
        review_geometry_sources(sources, 'board', 'MM')


def test_invalid_multipart_parent_is_not_treated_as_valid_separate_polygons():
    geometry = MultiPolygon([disk(0), disk(.5)])
    assert not geometry.is_valid
    with pytest.raises(ValueError, match='[Ii]nvalid'):
        review(geometry)


def test_original_primitive_type_affects_fingerprint():
    ring = LinearRing(disk().exterior.coords)
    line = LineString(ring.coords)
    assert ring.wkb == line.wkb
    assert review(ring).geometry_sha256 != review(line).geometry_sha256


def test_total_coordinate_budget_and_inch_physical_bounds():
    line = LineString([(0, 0), (1, 1)] * 45000)
    with pytest.raises(ValueError, match='coordinate budget'):
        review([line]*6)
    with pytest.raises(ValueError, match='physical'):
        review(Point(1e8, 0), units='IN')


def test_depth_boundary_empty_collection_and_long_unicode_identity():
    geometry = disk()
    for _ in range(64): geometry = [geometry]
    assert len(review(geometry).candidates) == 1
    with pytest.raises(ValueError, match='depth'):
        review([geometry])
    assert review(GeometryCollection()).notices
    result = review_geometry_sources((('ü'*128, disk()),), 'board', 'MM')
    assert len(result.candidates[0].source_id.encode('utf-8')) <= 256


@pytest.mark.parametrize('name,units', [('', 'MM'), ('x'*257, 'MM'), ('\ud800', 'MM'),
    ('board', 'mm'), ('board', None), (None, 'MM')])
def test_bad_source_metadata(name, units):
    with pytest.raises(ValueError):
        review_geometry_sources((('geometry', disk()),), name, units)
