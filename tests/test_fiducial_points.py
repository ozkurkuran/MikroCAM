"""Design fiducial candidates come from loaded objects in mm without modifying them."""
from types import SimpleNamespace

import pytest
from shapely.geometry import LineString, Point

from mikrocam.bridge.fiducial_points import MAX_CANDIDATES, design_points


def excellon(units='MM'):
    return SimpleNamespace(kind='excellon', units=units, tools={
        1: {'tooldia': 1., 'drills': [Point(1., 2.), Point(30., 4.)], 'slots': []},
        2: {'tooldia': 3., 'drills': [Point(50., 60.)]}})


def test_excellon_drill_centres_in_mm_with_labels():
    obj = excellon()
    before = {key: list(tool['drills']) for key, tool in obj.tools.items()}
    points = design_points(obj)
    assert [xy for _, xy in points] == [(1., 2.), (30., 4.), (50., 60.)]
    assert all(type(label) is str and label for label, _ in points)
    assert {key: list(tool['drills']) for key, tool in obj.tools.items()} == before


def test_inch_objects_are_converted_to_mm():
    points = design_points(excellon('IN'))
    assert points[0][1] == pytest.approx((25.4, 50.8))


def test_gerber_flashes_only():
    obj = SimpleNamespace(kind='gerber', units='MM', tools={
        '10': {'geometry': [{'follow': Point(5., 6.), 'solid': None},
                            {'follow': LineString([(0, 0), (1, 1)])}, {'solid': None}]},
        '11': {'geometry': [{'follow': Point(7., 8.)}]}})
    assert [xy for _, xy in design_points(obj)] == [(5., 6.), (7., 8.)]


@pytest.mark.parametrize('obj', [None, SimpleNamespace(kind='geometry', units='MM'),
                                 SimpleNamespace(kind='excellon', units='CM', tools={}),
                                 SimpleNamespace(kind='excellon', units='MM', tools=None),
                                 SimpleNamespace(kind='excellon', units='MM', tools={})])
def test_unsupported_or_empty_objects_are_refused(obj):
    with pytest.raises(ValueError):
        design_points(obj)


def test_candidate_count_is_bounded():
    obj = SimpleNamespace(kind='excellon', units='MM', tools={
        1: {'drills': [Point(float(i), 0.) for i in range(MAX_CANDIDATES + 5)]}})
    assert len(design_points(obj)) == MAX_CANDIDATES
