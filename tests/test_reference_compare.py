"""Reference metrics must detect manufacturing changes without byte equality."""
from dataclasses import FrozenInstanceError
import pytest
from shapely import from_wkt, set_srid, to_wkb
from shapely.affinity import scale, translate
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Point, Polygon, box

from mikrocam.core import reference_compare as reference


def wkb(geometry):
    return to_wkb(geometry, hex=True, byte_order=1, flavor='iso')


def compare(first, second, distance=0, area=0):
    return reference.compare_geometry(wkb(first), wkb(second), distance_mm=distance, area_mm2=area)


def path(points, kind=('C', 'F')):
    return reference.ReferencePath(kind, wkb(LineString(points)))


def test_identical_geometry_has_zero_metrics_and_immutable_result():
    result = compare(box(0, 0, 10, 5), box(0, 0, 10, 5))
    assert result.matches and result.topology_equal
    assert result.hausdorff_mm == result.symmetric_difference_mm2 == 0
    assert result.bounds_delta_mm == (0, 0, 0, 0)
    with pytest.raises(FrozenInstanceError):
        result.matches = False


def test_component_order_and_ring_orientation_do_not_change_set_comparison():
    first = MultiPolygon([box(0, 0, 1, 1), box(3, 0, 4, 1)])
    second = MultiPolygon([Polygon(list(p.exterior.coords)[::-1]) for p in reversed(first.geoms)])
    assert wkb(first) != wkb(second)
    assert compare(first, second).matches


def test_absolute_distance_and_area_are_independent_thresholds():
    first = box(0, 0, 10, 5)
    second = translate(first, xoff=.01)
    result = compare(first, second, .011, .101)
    assert result.matches
    assert result.hausdorff_mm == pytest.approx(.01)
    assert result.symmetric_difference_mm2 == pytest.approx(.1)
    assert result.bounds_delta_mm == pytest.approx((.01, 0, .01, 0))
    assert not compare(first, second, .009, .101).matches
    assert not compare(first, second, .011, .099).matches


def test_hole_and_component_topology_cannot_be_hidden_by_large_tolerance():
    solid = box(0, 0, 10, 10)
    hole = solid.difference(box(4, 4, 6, 6))
    result = compare(solid, hole, 100, 1000)
    assert not result.matches and not result.topology_equal
    split = MultiPolygon([box(0, 0, 4, 10), box(6, 0, 10, 10)])
    assert not compare(solid, split, 100, 1000).matches
    assert not compare(solid, MultiPolygon([solid]), 0, 0).matches


def test_equal_area_translation_and_wrong_inch_scale_are_detected():
    first = box(0, 0, 1, 2)
    assert not compare(first, translate(first, xoff=1), .001, .001).matches
    assert not compare(first, scale(first, 25.4, 25.4, origin=(0, 0)), .001, .001).matches
    normalized = scale(scale(first, 1/25.4, 1/25.4, origin=(0, 0)), 25.4, 25.4, origin=(0, 0))
    assert compare(first, normalized, 1e-12, 1e-12).matches


def test_line_displacement_uses_distance_even_when_areas_are_zero():
    first = LineString([(0, 0), (2, 0)])
    assert not compare(first, translate(first, yoff=.1), .01, 100).matches


@pytest.mark.parametrize('value', [True, False, -1, float('nan'), float('inf'), '0.1', None])
@pytest.mark.parametrize('key', ['distance_mm', 'area_mm2'])
def test_invalid_tolerances_are_errors(value, key):
    kwargs = dict(distance_mm=0, area_mm2=0)
    kwargs[key] = value
    with pytest.raises(ValueError):
        reference.compare_geometry(wkb(box(0, 0, 1, 1)), wkb(box(0, 0, 1, 1)), **kwargs)


@pytest.mark.parametrize('value', ['', 'bad', '00', None, 123, '01ZZ', '0101'])
def test_malformed_wkb_is_rejected(value):
    with pytest.raises(ValueError):
        reference.compare_geometry(value, wkb(Point(0, 0)), distance_mm=1, area_mm2=1)


@pytest.mark.parametrize('geometry', [Point(), GeometryCollection(), Point(0, 0, 1),
                                      LineString([(0, 0), (float('inf'), 1)]),
                                      Polygon([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)])])
def test_empty_nonfinite_nonplanar_invalid_geometry_is_rejected(geometry):
    with pytest.raises(ValueError):
        reference.compare_geometry(wkb(geometry), wkb(Point(0, 0)), distance_mm=1, area_mm2=1)


def test_trailing_wkb_bytes_and_big_endian_encoding_are_rejected():
    good = wkb(Point(0, 0))
    for value in (good + '00', to_wkb(Point(0, 0), hex=True, byte_order=0, flavor='iso')):
        with pytest.raises(ValueError):
            reference.compare_geometry(value, good, distance_mm=0, area_mm2=0)


def test_measured_coordinate_and_spatial_reference_tags_are_rejected():
    good = wkb(Point(0, 0))
    invalid = (wkb(from_wkt('POINT M (0 0 12)')),
               to_wkb(set_srid(Point(0, 0), 4326), hex=True, byte_order=1, include_srid=True))
    for value in invalid:
        with pytest.raises(ValueError):
            reference.compare_geometry(value, good, distance_mm=0, area_mm2=0)


def test_oversized_wkb_is_rejected_before_decode(monkeypatch):
    monkeypatch.setattr(reference, 'MAX_WKB_BYTES', 8)
    with pytest.raises(ValueError, match='size|large|limit'):
        compare(Point(0, 0), Point(0, 0))


def test_ordered_paths_tolerate_coordinate_noise_but_keep_count_and_kind():
    expected = [path([(0, 0), (1, 0)]), reference.ReferencePath(('T', 'S'), wkb(Point(4, 5)))]
    actual = [path([(0, .001), (1, .001)]), reference.ReferencePath(('T', 'S'), wkb(Point(4, 5)))]
    assert reference.compare_paths(expected, actual, distance_mm=.002).matches
    result = reference.compare_paths(expected, actual, distance_mm=.0005)
    assert not result.matches and result.differing_indices == (0,)
    assert result.expected_count == result.actual_count == 2
    with pytest.raises(FrozenInstanceError):
        result.matches = True


@pytest.mark.parametrize('replacement', [path([(1, 0), (0, 0)]),
                                        path([(0, 0), (.5, 0), (1, 0)]),
                                        path([(0, 0), (0, 0), (1, 0)]),
                                        path([(0, 0), (1, 0)], ('T', 'F'))])
def test_path_direction_vertices_repetition_and_kind_are_significant(replacement):
    assert not reference.compare_paths([path([(0, 0), (1, 0)])], [replacement], distance_mm=0).matches


def test_path_order_and_unmatched_tails_are_reported():
    first, second = path([(0, 0), (1, 0)]), path([(2, 0), (3, 0)])
    swapped = reference.compare_paths([first, second], [second, first], distance_mm=0)
    assert swapped.differing_indices == (0, 1)
    shorter = reference.compare_paths([first, second], [first], distance_mm=0)
    assert shorter.differing_indices == (1,) and shorter.expected_count == 2 and shorter.actual_count == 1


@pytest.mark.parametrize('kind', [(), ('',), ('C', 1), ['C', 'F'], 'CF'])
def test_path_kind_requires_nonempty_immutable_string_tuple(kind):
    with pytest.raises(ValueError):
        reference.ReferencePath(kind, wkb(Point(0, 0)))


def test_path_requires_point_or_linestring_and_valid_nonempty_sequences():
    with pytest.raises(ValueError):
        reference.ReferencePath(('C',), wkb(box(0, 0, 1, 1)))
    for expected, actual in (([], []), (['bad'], [path([(0, 0), (1, 0)])]), (None, [])):
        with pytest.raises(ValueError):
            reference.compare_paths(expected, actual, distance_mm=0)
    with pytest.raises(ValueError):
        reference.compare_paths([path([(0, 0), (1, 0)])], [path([(0, 0), (1, 0)])], distance_mm=True)


def test_path_resource_limits_are_explicit(monkeypatch):
    values = [path([(0, 0), (1, 0)])]
    monkeypatch.setattr(reference, 'MAX_PATHS', 0)
    with pytest.raises(ValueError, match='limit'):
        reference.compare_paths(values, values, distance_mm=0)
    monkeypatch.setattr(reference, 'MAX_PATHS', 10)
    monkeypatch.setattr(reference, 'MAX_VERTICES', 1)
    with pytest.raises(ValueError, match='limit'):
        reference.compare_paths(values, values, distance_mm=0)


def tool(identifier='1', diameter=1, drills=((0, 0),), slots=()):
    return reference.ReferenceTool(identifier, diameter, drills, slots)


def test_drill_diameters_duplicate_hits_and_slot_direction_are_preserved():
    expected = tool(drills=((0, 0), (0, 0)), slots=(((1, 2), (3, 4)),))
    assert reference.compare_tools([expected], [expected], distance_mm=0).matches
    for changed in (tool(drills=((0, 0),), slots=expected.slots),
                    tool(diameter=2, drills=expected.drills, slots=expected.slots),
                    tool(identifier='2', drills=expected.drills, slots=expected.slots),
                    tool(drills=expected.drills, slots=(((3, 4), (1, 2)),))):
        result = reference.compare_tools([expected], [changed], distance_mm=.001)
        assert not result.matches and result.differing_indices == (0,)


def test_drill_comparison_has_explicit_coordinate_diameter_tolerance_and_tool_order():
    expected = [tool(), tool('2', 2, slots=(((1, 2), (3, 4)),))]
    actual = [tool(diameter=1.001, drills=((.001, 0),)), expected[1]]
    assert reference.compare_tools(expected, actual, distance_mm=.002).matches
    assert not reference.compare_tools(expected, actual, distance_mm=.0001).matches
    assert not reference.compare_tools(expected, expected[::-1], distance_mm=0).matches
    assert reference.compare_tools(expected, expected[:1], distance_mm=0).differing_indices == (1,)


@pytest.mark.parametrize('kwargs', [dict(identifier=''), dict(diameter=0), dict(diameter=True),
                                  dict(diameter=float('inf')), dict(drills=[]),
                                  dict(drills=((0, 0, 0),)), dict(slots=(((1, 2),),)),
                                  dict(drills=((float('nan'), 0),))])
def test_invalid_drill_records_are_errors(kwargs):
    with pytest.raises(ValueError):
        tool(**kwargs)


def test_unused_declared_tools_are_retained_and_duplicate_ids_are_invalid():
    unused = tool('2', 2, drills=())
    assert reference.compare_tools([tool(), unused], [tool(), unused], distance_mm=0).matches
    with pytest.raises(ValueError, match='unique'):
        reference.compare_tools([tool(), tool()], [tool()], distance_mm=0)
    with pytest.raises(ValueError):
        reference.compare_tools([], [], distance_mm=0)
