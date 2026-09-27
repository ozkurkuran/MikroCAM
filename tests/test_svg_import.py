"""Physical SVG import outcomes independent of desktop/host object mutation."""
import hashlib
import math

import pytest
from shapely import LineString, Point, union_all

from mikrocam.bridge.svg_import import import_svg_bytes, load_svg_file, host_geometry


def source(body, attrs='width="100mm" height="100mm" viewBox="0 0 100 100"'):
    return f'<svg {attrs}>{body}</svg>'.encode()


@pytest.mark.parametrize('size', ['25.4mm', '2.54cm', '1in', '72pt', '6pc', '96px', '96'])
def test_equivalent_physical_roots_produce_same_material(size):
    result = import_svg_bytes(source('<rect width="96" height="48"/>',
                              f'width="{size}" height="{size}" viewBox="0 0 96 96"'), 'units.svg', flip=False)
    shape = union_all(result.geometry_mm)
    assert shape.bounds == pytest.approx((0., 0., 25.4, 12.7), abs=1e-6)
    assert shape.area == pytest.approx(25.4 * 12.7)


def test_child_absolute_lengths_are_local_css_units_before_viewbox():
    result = import_svg_bytes(source('<rect width="4in" height="2in"/>',
                              'width="400px" height="200px" viewBox="0 0 4000 2000"'), 'child.svg', flip=False)
    assert union_all(result.geometry_mm).bounds == pytest.approx((0., 0., 38.4*25.4/96, 19.2*25.4/96))


def test_transform_stroke_then_single_flip_and_host_unit_boundary():
    payload = source('<g stroke="black" stroke-width="2" fill="none" transform="translate(10 20) scale(2 3)">'
                     '<path d="M0 0 L5 0"/></g>')
    result = import_svg_bytes(payload, 'stroke.svg')
    assert result.document.source_sha256 == hashlib.sha256(payload).hexdigest()
    assert union_all(result.geometry_mm).bounds == pytest.approx((10., 77., 20., 83.))
    assert union_all(host_geometry(result, 'IN')).bounds == pytest.approx(tuple(v/25.4 for v in (10., 77., 20., 83.)))
    assert union_all(host_geometry(result, 'MM')).equals(union_all(result.geometry_mm))


def test_root_transform_and_viewbox_origin_do_not_commute():
    result = import_svg_bytes(source('<rect x="10" y="20" width="1" height="1"/>',
                              'width="100mm" height="100mm" viewBox="10 20 100 100" transform="translate(10 0)"'),
                              'root.svg', flip=False)
    assert union_all(result.geometry_mm).bounds == pytest.approx((10*25.4/96, 0., 1+10*25.4/96, 1.))


def test_open_default_fill_is_implicitly_closed_but_source_path_metadata_stays_open():
    result = import_svg_bytes(source('<path d="M1 1 L4 1 L1 5"/>'), 'open.svg', flip=False)
    assert union_all(result.geometry_mm).area == pytest.approx(6.)
    assert not result.rendered[0].paths_mm[0].closed
    assert result.rendered[0].paths_mm[0].points[-1] == (1., 5.)


def test_geometry_retains_unpainted_open_cam_path_but_gerber_requires_material():
    payload = source('<path d="M0 0 L5 5" fill="none"/>')
    result = import_svg_bytes(payload, 'centerline.svg', flip=False)
    assert isinstance(result.geometry_mm[0], LineString)
    assert any('centreline' in notice.message.lower() or 'centerline' in notice.message.lower()
               for notice in result.notices)
    with pytest.raises(ValueError, match='solid|empty|material'):
        import_svg_bytes(payload, 'centerline.svg', object_type='gerber')


@pytest.mark.parametrize('path', ['M0 0 C0 10 10 10 10 0', 'M0 0 Q5 10 10 0',
                                 'M10 0 A10 10 0 0 1 0 10', 'M10 0 A10 5 30 0 1 0 10'])
def test_curved_paths_preserve_endpoints_and_valid_stroked_material(path):
    payload = source(f'<path d="{path}" fill="none" stroke="black" stroke-width=".2"/>')
    result = import_svg_bytes(payload, 'curve.svg', flip=False)
    geometry = union_all(result.geometry_mm)
    assert geometry.is_valid and geometry.area > 0
    assert result.rendered[0].paths_mm[0].points[-1] == ((10., 0.) if ' A' not in path else (0., 10.))


def test_bezier_error_budget_is_measured_after_large_affine_scale():
    result = import_svg_bytes(source('<path transform="scale(100)" d="M0 0 Q1 2 2 0" fill="none"/>'),
                              'scaled.svg', flip=False)
    path = LineString(result.rendered[0].paths_mm[0].points)
    for index in range(1001):
        t = index / 1000
        assert path.distance(Point(200*t, 400*t*(1-t))) <= .005 + 1e-10


@pytest.mark.parametrize('path', ['M0 0 Lnan 1', 'M0 0 L1e999 0', 'M0 0 R1 2',
                                 'M0 0 L1 2 trailing', 'M0 0 L1e10 0', 'M0 0 A1 1 0 4 0 2 2'])
def test_malformed_or_unbounded_path_cannot_return_partial_geometry(path):
    with pytest.raises(ValueError):
        import_svg_bytes(source(f'<rect width="1" height="1"/><path d="{path}"/>'), 'bad.svg')


def test_local_use_never_renders_its_definition_separately():
    result = import_svg_bytes(source('<defs><rect id="one" width="2" height="3"/></defs>'
                              '<use href="#one" x="10" y="20"/>'), 'use.svg', flip=False)
    assert len(result.rendered) == 1
    assert union_all(result.geometry_mm).bounds == (10., 20., 12., 23.)


def test_load_file_is_bounded_and_does_not_modify_source(tmp_path, monkeypatch):
    import mikrocam.bridge.svg_import as bridge
    payload = source('<rect width="2" height="3"/>')
    path = tmp_path / 'test.svg'
    path.write_bytes(payload)
    result = load_svg_file(path)
    assert result.document.source_sha256 == hashlib.sha256(payload).hexdigest()
    assert path.read_bytes() == payload
    monkeypatch.setattr(bridge, 'MAX_SVG_BYTES', 10)
    with pytest.raises(ValueError, match='size|limit|byte'):
        load_svg_file(path)


@pytest.mark.parametrize('units', ['mm', 'cm', None, True])
def test_unknown_host_units_are_explicit_error(units):
    result = import_svg_bytes(source('<rect width="1" height="1"/>'), 'rect.svg')
    with pytest.raises(ValueError):
        host_geometry(result, units)


def test_inferred_viewport_size_notice_reaches_import_consumer():
    result = import_svg_bytes(source('<rect width="1" height="1"/>', 'viewBox="0 0 100 100"'),
                              'inferred.svg')
    assert result.document.viewport.notices
    assert all(notice in result.notices for notice in result.document.viewport.notices)
