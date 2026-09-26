"""Gerber snapshots use current host units and detached immutable copper."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from shapely import GeometryCollection, LineString, MultiPolygon, Point, Polygon, box
from shapely.affinity import scale

from mikrocam.bridge.gerber import gerber_region
from mikrocam.core.laser_job import PlanarRegion


def host(geometry, units='MM', **fields):
    return SimpleNamespace(kind='gerber', solid_geometry=geometry, units=units, **fields)


def test_mm_copper_is_not_scaled_and_preserves_holes():
    copper = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)],
                     [[(2, 2), (4, 2), (4, 4), (2, 4)]])
    result = gerber_region(host(copper))
    assert isinstance(result, PlanarRegion)
    assert result.to_geometry().equals(copper)
    assert result.to_geometry().area == pytest.approx(96)
    assert len(result.to_geometry().interiors) == 1


@pytest.mark.parametrize('units', ['IN', 'in', ' in '])
def test_inch_and_mm_inputs_agree_with_one_25_4_conversion(units):
    inches = box(1, 2, 3, 4)
    millimeters = scale(inches, xfact=25.4, yfact=25.4, origin=(0, 0))
    converted = gerber_region(host(inches, units)).to_geometry()
    unchanged = gerber_region(host(millimeters, 'MM')).to_geometry()
    assert converted.hausdorff_distance(unchanged) <= 1e-9
    assert converted.bounds == pytest.approx((25.4, 50.8, 76.2, 101.6), abs=1e-9)


def test_current_mm_geometry_ignores_original_inch_source_and_units_found():
    copper = box(0, 0, 25.4, 25.4)
    obj = host(copper, source_file='%MOIN*%\nX10000Y10000D03*', units_found='IN')
    source = obj.source_file
    assert gerber_region(obj).to_geometry().equals(copper)
    assert obj.source_file == source and obj.units_found == 'IN' and obj.units == 'MM'


def test_no_source_or_global_defaults_are_consulted():
    class DetachedHost:
        kind = 'gerber'
        units = 'MM'
        solid_geometry = box(0, 0, 1, 1)

        def __getattr__(self, name):
            raise AssertionError(f'Unexpected host/global lookup: {name}')

    assert gerber_region(DetachedHost()).to_geometry().area == pytest.approx(1)


def test_nested_disconnected_and_overlapping_copper_is_unioned():
    shell = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)],
                    [[(2, 2), (4, 2), (4, 4), (2, 4)]])
    separate = box(20, 0, 22, 2)
    geometry = [shell, (GeometryCollection([MultiPolygon([separate])]), [box(21, 0, 23, 2)])]
    result = gerber_region(host(geometry)).to_geometry()
    assert result.geom_type == 'MultiPolygon'
    assert len(result.geoms) == 2
    assert result.area == pytest.approx(102)
    assert sum(len(polygon.interiors) for polygon in result.geoms) == 1


def test_bridge_does_not_mutate_host_and_snapshot_survives_host_changes():
    first, second = box(0, 0, 1, 1), box(3, 0, 4, 1)
    solids = [first, [second]]
    obj = host(solids, source_file='original data', units_found='MM')
    before = dict(vars(obj))
    original_wkb = (first.wkb, second.wkb)
    result = gerber_region(obj)
    assert vars(obj) == before
    assert obj.solid_geometry is solids and solids[1][0] is second
    assert (first.wkb, second.wkb) == original_wkb
    snapshot = result.wkb_hex
    solids[1].clear()
    obj.solid_geometry = box(0, 0, 9, 9)
    obj.units = 'IN'
    assert result.wkb_hex == snapshot
    assert result.to_geometry().area == pytest.approx(2)


@pytest.mark.parametrize('obj', [None, object(), SimpleNamespace(kind='geometry'),
                                SimpleNamespace(kind='cncjob'), SimpleNamespace(kind=None)])
def test_wrong_or_missing_object_kind_is_rejected(obj):
    with pytest.raises(ValueError, match='Gerber|gerber'):
        gerber_region(obj)


@pytest.mark.parametrize('units', [None, '', 'CM', 'mil', 25.4, True])
def test_missing_or_unsupported_units_never_use_global_defaults(units):
    obj = host(box(0, 0, 1, 1), units, app=SimpleNamespace(app_units='MM'))
    with pytest.raises(ValueError, match='units'):
        gerber_region(obj)


def test_absent_units_and_absent_solid_geometry_fail_explicitly():
    with pytest.raises(ValueError, match='units'):
        gerber_region(SimpleNamespace(kind='gerber', solid_geometry=box(0, 0, 1, 1)))
    with pytest.raises(ValueError, match='solid_geometry'):
        gerber_region(SimpleNamespace(kind='gerber', units='MM'))


@pytest.mark.parametrize('geometry', [
    None, [], Polygon(), GeometryCollection(), Point(1, 2), LineString([(0, 0), (1, 1)]),
    [box(0, 0, 1, 1), Point(2, 3)], {'solid': box(0, 0, 1, 1)},
    Polygon([(0, 0), (1, 1), (0, 1), (1, 0)]),
    Polygon([(0, 0, 1), (1, 0, 1), (0, 1, 1)]),
])
def test_empty_invalid_nonpolygon_or_nonplanar_copper_fails(geometry):
    with pytest.raises(ValueError):
        gerber_region(host(geometry))


def test_adapter_delegates_current_geometry_and_units_to_core(monkeypatch):
    import mikrocam.bridge.gerber as bridge
    solids = [box(0, 0, 1, 1)]
    obj = host(solids, 'IN')
    expected = PlanarRegion.from_geometry(box(0, 0, 1, 1))
    calls = []

    def capture(geometry, units):
        calls.append((geometry, units))
        return expected

    monkeypatch.setattr(bridge, 'region_from_polygons', capture)
    assert gerber_region(obj) is expected
    assert len(calls) == 1 and calls[0][0] is solids and calls[0][1] == 'IN'


def test_real_gerber_fixture_before_and_after_host_unit_conversion():
    from shapely.ops import unary_union
    from test_gerber_parser import get_gerber_parser

    parser = get_gerber_parser()
    parser.kind = 'gerber'
    fixture = Path(__file__).with_name('test_files') / 'region_test.gbr'
    assert parser.parse_file(str(fixture)) not in ('fail', 'defective')
    assert parser.units == 'IN' and '%MOIN*%' in parser.source_file
    original = unary_union(parser.solid_geometry)
    from_inches = gerber_region(parser).to_geometry()
    parser.convert_units('MM')
    assert parser.units == 'MM' and '%MOIN*%' in parser.source_file
    source = parser.source_file
    solids = parser.solid_geometry
    from_current_mm = gerber_region(parser).to_geometry()
    assert from_inches.hausdorff_distance(from_current_mm) <= 1e-9
    assert from_current_mm.area == pytest.approx(original.area * 25.4 ** 2, abs=1e-6)
    assert parser.solid_geometry is solids and parser.source_file == source
