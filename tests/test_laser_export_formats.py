"""Independent XML/DXF readers verify scale, registration, order and topology."""
from io import BytesIO, StringIO
import xml.etree.ElementTree as ET

import ezdxf
import pytest

from mikrocam.core.laser_paths import LaserPath, PlanningCancelled
from mikrocam.core.laser_svg import svg_document
from mikrocam.core.laser_dxf import dxf_document
from mikrocam.core.placement import Placement


NS = {'s': 'http://www.w3.org/2000/svg'}


def paths():
    return (LaserPath(((10, -5), (35.4, -5), (35.4, 7.7), (10, 7.7), (10, -5)), 'contour'),
            LaserPath(((10, 1), (15, 1)), 'hatch', 1, 0),
            LaserPath(((20, 1), (35.4, 1)), 'hatch', 1, 0))


def bounds(values):
    points = [point for path in values for point in path.points]
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)


def svg_paths(document, extent):
    root = ET.fromstring(document)
    assert root.tag == '{http://www.w3.org/2000/svg}svg'
    assert float(root.attrib['width'][:-2]) == pytest.approx(extent[2]-extent[0] or 1)
    assert root.attrib['width'].endswith('mm') and root.attrib['height'].endswith('mm')
    assert root.find('.//s:script', NS) is None
    result = []
    for node in root.findall('.//s:polyline', NS):
        assert node.attrib['fill'] == 'none'
        values = [tuple(map(float, item.split(','))) for item in node.attrib['points'].split()]
        result.append(tuple((x+extent[0], extent[3]-y) for x, y in values))
    return result


def dxf_paths(document):
    drawing = ezdxf.read(StringIO(document))
    assert drawing.dxfversion == 'AC1015' and drawing.units == 4
    audit = drawing.audit()
    assert not audit.has_errors, audit.errors
    entities = list(drawing.modelspace())
    assert all(entity.dxftype() == 'LWPOLYLINE' for entity in entities)
    result = []
    for entity in entities:
        assert entity.dxf.elevation == 0
        points = tuple(tuple(value) for value in entity.get_points('xy'))
        result.append(points + (points[0],) if entity.closed else points)
    return result


@pytest.mark.parametrize('placement', [Placement(), Placement(translation=(-40, 20)),
                                      Placement(rotation_deg=37, mirror_x=True, translation=(3, -10))])
@pytest.mark.parametrize('format', ['svg', 'dxf'])
def test_independent_reader_retains_each_placed_path_without_extra_connectors(format, placement):
    values = tuple(LaserPath(placement.apply_points(p.points), p.role, p.scan_index, p.hatch_family) for p in paths())
    extent = bounds(values)
    document = svg_document(values, extent, 'Pass <name> & "data"') if format == 'svg' else dxf_document(values, 1)
    decoded = svg_paths(document, extent) if format == 'svg' else dxf_paths(document)
    assert len(decoded) == len(values)
    for actual, expected in zip(decoded, values):
        assert len(actual) == len(expected.points)
        for point, reference in zip(actual, expected.points):
            assert point == pytest.approx(reference, abs=1e-8, rel=0)


def test_svg_physical_25_4_mm_dimensions_and_safe_title():
    document = svg_document(paths(), bounds(paths()), '<script>alert(1)</script>')
    root = ET.fromstring(document)
    assert float(root.attrib['width'][:-2]) == pytest.approx(25.4, rel=0, abs=1e-10)
    assert float(root.attrib['height'][:-2]) == pytest.approx(12.7, rel=0, abs=1e-10)
    assert list(map(float, root.attrib['viewBox'].split())) == pytest.approx([0, 0, 25.4, 12.7], rel=0, abs=1e-10)
    assert root.find('s:title', NS).text == '<script>alert(1)</script>'
    assert root.find('.//s:script', NS) is None


def test_independent_svg_renderer_reads_25_4_mm_as_one_inch():
    from svglib.svglib import svg2rlg
    drawing = svg2rlg(BytesIO(svg_document(paths(), bounds(paths()), 'reference').encode('utf-8')))
    assert drawing.width == pytest.approx(72, abs=1e-8, rel=0)
    assert drawing.height == pytest.approx(36, abs=1e-8, rel=0)


@pytest.mark.parametrize('points', [((3, 2), (3, 10)), ((3, 2), (10, 2))])
def test_zero_extent_viewport_does_not_add_registration_geometry(points):
    values = (LaserPath(points, 'contour'),)
    document = svg_document(values, bounds(values), 'single path')
    root = ET.fromstring(document)
    assert float(root.attrib['width'][:-2]) > 0 and float(root.attrib['height'][:-2]) > 0
    assert svg_paths(document, bounds(values)) == [points]


def test_dxf_per_pass_layer_and_entity_order_are_explicit():
    drawing = ezdxf.read(StringIO(dxf_document(paths(), 2)))
    assert {value.dxf.layer for value in drawing.modelspace()} == {'PASS_002'}
    assert drawing.layers.has_entry('PASS_002')
    assert [entity.closed for entity in drawing.modelspace()] == [True, False, False]


@pytest.mark.parametrize('index', [0, -1, True, 1.5, '1'])
def test_invalid_dxf_index_is_explicit(index):
    with pytest.raises(ValueError):
        dxf_document(paths(), index)


@pytest.mark.parametrize('extent', [(-1e308, 0, 1e308, 1), (0, 0, float('inf'), 1),
                                    (1, 0, 0, 1), (0, 0, 1), (0, False, 1, 1)])
def test_invalid_or_overflowing_svg_extent_fails(extent):
    with pytest.raises(ValueError):
        svg_document(paths(), extent, 'test')


def test_bounds_must_cover_paths_and_xml_control_characters_are_rejected():
    with pytest.raises(ValueError):
        svg_document(paths(), (0, 0, 1, 1), 'test')
    with pytest.raises(ValueError):
        svg_document(paths(), bounds(paths()), 'invalid\x00name')


@pytest.mark.parametrize('format', ['svg', 'dxf'])
def test_empty_paths_and_mid_serialization_cancel_fail(format):
    def serialize(values, cancelled=None):
        if format == 'svg':
            return svg_document(values, (0, 0, 40, 20), 'test', cancelled)
        return dxf_document(values, 1, cancelled)
    with pytest.raises(ValueError):
        serialize(())
    calls = []
    def stop():
        calls.append(1)
        return len(calls) >= 2
    values = (LaserPath(((0, 0), (2, 1)), 'contour'),)*4
    with pytest.raises(PlanningCancelled):
        serialize(values, stop)
