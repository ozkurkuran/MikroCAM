"""Analytic contour/hatch oracles and final-copper Gerber semantics."""
import json
from pathlib import Path

import pytest
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Point, Polygon, box

from mikrocam.core.laser_features import features_from_gerber
from mikrocam.core.laser_geometry import contour_paths, hatch_paths, selected_area
from mikrocam.core.laser_job import PlanarRegion
from mikrocam.core.laser_paths import CopperFeatures, PlanningCancelled


REF = json.loads((Path(__file__).parent / 'reference/laser_contour_hatch.json').read_text())


def region(geometry):
    return PlanarRegion.from_geometry(geometry)


def reference_region():
    return region(Polygon(REF['outer'], [REF['hole']]))


def lines(paths):
    return [LineString(path.points) for path in paths]


def test_outer_inner_and_disconnected_contours():
    copper = reference_region()
    features = CopperFeatures(copper)
    assert sum(line.length for line in lines(contour_paths(features, 'outer'))) == REF['outer_length']
    assert sum(line.length for line in lines(contour_paths(features, 'inner'))) == REF['inner_length']
    assert contour_paths(features, 'none') == ()
    multi = CopperFeatures(region(MultiPolygon([copper.to_geometry(), box(6, 0, 7, 1)])))
    assert len(contour_paths(multi, 'outer')) == 2
    assert len(contour_paths(multi, 'inner')) == 1


def test_trace_pad_metadata_respects_final_clear_copper():
    final = region(box(0, 0, 4, 2).difference(box(1, 0, 2, 2)))
    records = [('C', box(0, 0, 4, 2), LineString([(0, 1), (4, 1)])),
               ('C', box(0, 0, 2, 2), Point(1, 1)),
               ('REG', box(3, 0, 4, 2), LineString([(3, 0), (4, 0), (4, 2), (3, 0)]))]
    features = features_from_gerber(final, records, 'MM')
    assert features.traces.to_geometry().equals(final.to_geometry())
    assert features.pads.to_geometry().equals(box(0, 0, 1, 2))
    assert len(contour_paths(features, 'trace')) == 2
    assert len(contour_paths(features, 'pad')) == 1
    empty = features_from_gerber(final, [('REG', box(0, 0, 1, 1), records[2][2])], 'MM')
    assert empty.traces is None and empty.pads is None


def test_metadata_inch_conversion_once_and_missing_features():
    copper = region(box(0, 0, 25.4, 25.4))
    features = features_from_gerber(copper, [('C', box(0, 0, 1, 1), Point(0.5, 0.5))], 'IN')
    assert features.pads.to_geometry().area == pytest.approx(25.4**2, rel=0, abs=1e-8)
    for mode in ('trace', 'pad', 'board'):
        with pytest.raises(ValueError, match='available|outline'):
            contour_paths(CopperFeatures(copper), mode)


def test_explicit_outline_even_odd_nested_cutouts_and_islands():
    outer, cutout, island = (box(0, 0, 10, 10).exterior, box(2, 2, 8, 8).exterior,
                             box(4, 4, 6, 6).exterior)
    features = features_from_gerber(region(box(0.1, 0.1, 1, 1)), (), 'MM',
                                   [island, outer, cutout], 'MM')
    assert features.board.to_geometry().area == 100-36+4
    assert len(contour_paths(features, 'board')) == 3
    inch = features_from_gerber(region(box(1, 1, 2, 2)), (), 'MM', box(0, 0, 1, 1).exterior, 'IN')
    assert inch.board.to_geometry().area == pytest.approx(25.4**2, rel=0, abs=1e-8)


@pytest.mark.parametrize('outline', [
    None, [], LineString([(0, 0), (1, 0)]), Point(0, 0),
    LineString([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)]),
    [box(0, 0, 2, 2).exterior, box(1, 0, 3, 2).exterior],
    [box(0, 0, 2, 2).exterior, box(2, 0, 3, 2).exterior],
    [box(0, 0, 2, 2).exterior, box(0, 0, 2, 2).exterior],
    LineString([(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 0, 1)]),
])
def test_invalid_explicit_outline_fails(outline):
    if outline is None:
        assert features_from_gerber(reference_region(), (), 'MM').board is None
    else:
        with pytest.raises(ValueError):
            features_from_gerber(reference_region(), (), 'MM', outline, 'MM')


def test_clearance_requires_containing_board_and_retains_cutout():
    copper = region(box(1, 1, 2, 2))
    board = region(Polygon(REF['outer'], [[(2.5, 2.5), (3, 2.5), (3, 3), (2.5, 3)]]))
    features = CopperFeatures(copper, board=board)
    selected = selected_area(features, 'clearance').to_geometry()
    assert selected.area == 14.75 and not selected.covers(Point(2.75, 2.75))
    assert selected_area(features, 'copper') == copper
    for other in (None, region(box(1.5, 1.5, 3, 3)), copper):
        with pytest.raises(ValueError):
            selected_area(CopperFeatures(copper, board=other), 'clearance')


def test_horizontal_hatch_reference_hole_and_no_connector():
    paths = hatch_paths(reference_region(), 1, 0)
    middle = [p for p in paths if p.scan_index == REF['scan_y']]
    assert len(middle) == 2
    for actual, expected in zip(middle, REF['segments']):
        assert actual.points == tuple(tuple(p) for p in expected)
        assert actual.role == 'hatch' and actual.hatch_family == 0


@pytest.mark.parametrize('angle', [-450, -30, 0, 23.5, 90, 180, 360, 1e10])
@pytest.mark.parametrize('cross', [False, True])
def test_angled_hatch_clipped_deterministic_and_spaced(angle, cross):
    from mikrocam.core.placement import Placement
    source = reference_region()
    paths = hatch_paths(source, 0.37, angle, cross)
    assert paths == hatch_paths(source, 0.37, angle, cross)
    assert {p.hatch_family for p in paths} == ({0, 1} if cross else {0})
    allowed = source.to_geometry().buffer(1e-8)
    for path, line in zip(paths, lines(paths)):
        assert allowed.covers(line)
        local = Placement(rotation_deg=-(angle % 360 + 90*path.hatch_family)).apply_points(path.points)
        assert all(p[1] == pytest.approx(path.scan_index * 0.37, abs=1e-8, rel=0) for p in local)


def test_multipart_hatch_does_not_join_islands():
    source = region(MultiPolygon([box(-3, -0.5, -2, 0.5), box(2, -0.5, 3, 0.5)]))
    paths = hatch_paths(source, 1, 0)
    assert len(paths) == 2 and all(path.scan_index == 0 for path in paths)
    assert sum(line.length for line in lines(paths)) == 2


@pytest.mark.parametrize('spacing', [0, -1, True, float('nan'), float('inf'), 1e-12])
def test_invalid_or_excessive_hatch_is_explicit(spacing):
    with pytest.raises(ValueError):
        hatch_paths(reference_region(), spacing, 0)


def test_cancellation_before_and_during_hatch():
    with pytest.raises(PlanningCancelled):
        contour_paths(CopperFeatures(reference_region()), 'outer', lambda: True)
    calls = []
    def cancelled():
        calls.append(1)
        return len(calls) > 3
    with pytest.raises(PlanningCancelled):
        hatch_paths(reference_region(), 0.01, 0, cancelled=cancelled)
    assert len(calls) == 4


def test_scan_limit_is_aggregate_and_inclusive(monkeypatch):
    import mikrocam.core.laser_geometry as kernel
    monkeypatch.setattr(kernel, 'MAX_SCAN_LINES', 5)
    source = region(box(0, 0, 4, 4))
    assert {p.scan_index for p in hatch_paths(source, 1, 0)} == {0, 1, 2, 3, 4}
    with pytest.raises(ValueError, match='candidate scan'):
        hatch_paths(region(box(0, 0, 4, 5)), 1, 0)
    with pytest.raises(ValueError, match='candidate scan'):
        hatch_paths(source, 1, 0, True)


def test_emitted_path_limit_never_truncates_geometry(monkeypatch):
    import mikrocam.core.laser_paths as values
    monkeypatch.setattr(values, 'MAX_PATHS', 2)
    source = region(MultiPolygon([box(-3, -0.5, -2, 0.5), box(2, -0.5, 3, 0.5)]))
    assert len(hatch_paths(source, 1, 0)) == 2
    with pytest.raises(ValueError, match='paths'):
        hatch_paths(source, 0.2, 0)


def test_boundary_overlap_and_point_only_tangency_convention():
    paths = hatch_paths(region(Polygon([(0, 0), (2, 0), (1, 1)])), 1, 0)
    assert len(paths) == 1
    assert paths[0].points == ((0, 0), (2, 0))


def test_fully_cleared_semantic_feature_reports_no_available_area():
    copper = region(box(3, 0, 4, 1))
    features = features_from_gerber(copper, [('C', box(0, 0, 1, 1), Point(0.5, 0.5))], 'MM')
    assert features.pads is None
    with pytest.raises(ValueError, match='No pad geometry available'):
        contour_paths(features, 'pad')


@pytest.mark.parametrize(('angle', 'expected_count', 'expected_indices'), [
    (0, 3, {0, 1, 2}), (90, 5, {-4, -3, -2, -1, 0}),
    (180, 3, {-2, -1, 0}), (270, 5, {0, 1, 2, 3, 4}),
])
def test_exact_cardinal_hatch_retains_both_boundary_rows(angle, expected_count, expected_indices):
    paths = hatch_paths(region(box(0, 0, 4, 2)), 1, angle)
    assert len(paths) == expected_count
    assert {path.scan_index for path in paths} == expected_indices
    assert all(LineString(path.points).length == (4 if angle % 180 == 0 else 2) for path in paths)
