from dataclasses import FrozenInstanceError, replace

import pytest
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Point, Polygon

from mikrocam.core.import_report import (
    ImportCoordinates, ImportQuality, ImportReport, build_import_report,
)
from mikrocam.core.svg_models import (
    CURVE_TOLERANCE_MM, SvgDocument, SvgElement, SvgImportResult, SvgNotice,
    SvgPaint, SvgPath, SvgRendered,
)
from mikrocam.core.svg_transform import resolve_svg_viewport


def coordinates(**changes):
    values = dict(source_width='10mm', source_height='20mm', source_units=('mm', 'mm'),
                  view_box=(0., 0., 10., 20.), aspect_ratio='xMidYMid meet',
                  viewport_mm=(10., 20.), matrix_mm=(1., 0., 0., 1., 0., 0.), flipped=False)
    return ImportCoordinates(**(values | changes))


def quality(**changes):
    values = dict(bounds_mm=(0., 0., 1., 1.), geometry_count=1, valid_count=1,
                  invalid_count=0, empty_count=0, open_paths=0, closed_paths=1,
                  precision_mm=0.01)
    return ImportQuality(**(values | changes))


def result_for(geometries, paths=(), attributes=(('width', '10mm'), ('height', '20mm')),
               notices=()):
    viewport = resolve_svg_viewport(attributes)
    element = SvgElement('e', 'path', (), viewport.matrix, SvgPaint())
    document = SvgDocument('board.svg', 'a' * 64, viewport, (element,), notices,
                           root_attributes=attributes)
    return SvgImportResult(document, (SvgRendered(paths, geometries),))


def test_records_are_frozen_and_keep_only_immutable_facts():
    report = ImportReport('board.svg', 'a' * 64, coordinates(), quality())
    with pytest.raises(FrozenInstanceError):
        report.source_name = 'other.svg'
    with pytest.raises(FrozenInstanceError):
        report.quality.valid_count = 0


@pytest.mark.parametrize('changes', [
    {'source_width': ''}, {'source_width': ' 10mm'}, {'source_height': 'x' * 129},
    {'source_units': ['mm', 'mm']}, {'source_units': ('%', 'mm')},
    {'view_box': [0, 0, 1, 1]}, {'view_box': (0, 0, 0, 1)},
    {'view_box': (True, 0, 1, 1)}, {'view_box': (0, 0, float('nan'), 1)},
    {'viewport_mm': (0, 1)}, {'viewport_mm': (1, float('inf'))},
    {'viewport_mm': (1e9 + 1, 1)}, {'matrix_mm': (0, 0, 0, 0, 0, 0)},
    {'matrix_mm': [1, 0, 0, 1, 0, 0]}, {'flipped': 1},
    {'aspect_ratio': 'xMidYMid'}, {'aspect_ratio': 'xMidYMid slice'},
])
def test_coordinates_reject_invalid_or_mutable_facts(changes):
    with pytest.raises(ValueError):
        coordinates(**changes)


@pytest.mark.parametrize('changes', [
    {'source_width': 'garbage'}, {'source_width': '10%'},
    {'source_width': '0mm'}, {'source_height': '-1mm'},
    {'source_units': ('in', 'mm')}, {'source_width': None},
    {'source_width': '10mm', 'source_units': ('absent', 'mm')},
    {'source_width': '10', 'source_units': ('px', 'mm')},
])
def test_source_dimension_tokens_and_unit_labels_cannot_contradict(changes):
    with pytest.raises(ValueError):
        coordinates(**changes)


def test_absent_dimensions_remain_modelable_without_inventing_physical_facts():
    value = coordinates(source_width=None, source_height=None,
                        source_units=('absent', 'absent'), view_box=None)
    assert value.source_width is None and value.view_box is None


@pytest.mark.parametrize('changes', [
    {'geometry_count': True}, {'valid_count': -1}, {'open_paths': 500001},
    {'geometry_count': 2}, {'precision_mm': 0}, {'precision_mm': True},
    {'precision_mm': 1.01}, {'bounds_mm': (1, 0, 0, 1)},
    {'bounds_mm': (0, 0, float('nan'), 1)}, {'bounds_mm': [0, 0, 1, 1]},
    {'bounds_mm': None},
])
def test_quality_rejects_inconsistent_counts_and_bounds(changes):
    with pytest.raises(ValueError):
        quality(**changes)


def test_empty_quality_has_no_bounds_or_invented_precision():
    value = quality(bounds_mm=None, geometry_count=1, valid_count=0, empty_count=1,
                    closed_paths=0, precision_mm=None)
    assert value.bounds_mm is None and value.precision_mm is None
    with pytest.raises(ValueError):
        replace(value, bounds_mm=(0, 0, 0, 0))


@pytest.mark.parametrize('changes', [
    {'source_name': ''}, {'source_name': 'x' * 257}, {'source_sha256': 'A' * 64},
    {'coordinates': {}}, {'quality': {}}, {'notices': []},
    {'notices': (SvgNotice('x', 'm'),) * 201},
])
def test_report_rejects_invalid_envelope(changes):
    values = dict(source_name='x.svg', source_sha256='a' * 64,
                  coordinates=coordinates(), quality=quality(), notices=())
    with pytest.raises(ValueError):
        ImportReport(**(values | changes))


def test_atomic_material_count_is_not_source_closure_count():
    a = Polygon(((0, 0), (1, 0), (1, 1), (0, 0)))
    b = Polygon(((3, 0), (4, 0), (4, 1), (3, 0)))
    geometry = GeometryCollection((MultiPolygon((a, b)), LineString(((0, 2), (5, 2))),
                                   Point(6, 3), Polygon()))
    paths = (SvgPath(((0, 0), (1, 0), (1, 1))),
             SvgPath(((3, 0), (4, 0), (4, 1), (3, 0)), True))
    report = build_import_report(result_for((geometry,), paths))
    assert report.quality == ImportQuality((0, 0, 6, 3), 5, 4, 0, 1, 1, 1,
                                          CURVE_TOLERANCE_MM)


def test_source_units_inference_and_canonical_aspect_do_not_guess_tokens():
    attributes = (('width', ' 1in '), ('viewBox', '-2 3 96 192'),
                  ('preserveAspectRatio', 'xMaxYMin'))
    report = build_import_report(result_for((Point(1, 2),), attributes=attributes))
    facts = report.coordinates
    assert (facts.source_width, facts.source_height, facts.source_units) == ('1in', None, ('in', 'absent'))
    assert facts.view_box == (-2, 3, 96, 192)
    assert facts.aspect_ratio == 'xMaxYMin meet'
    assert facts.viewport_mm == pytest.approx((25.4, 50.8))
    assert facts.matrix_mm == resolve_svg_viewport(attributes).matrix
    assert report.notices[0].code == 'inferred-size'


@pytest.mark.parametrize('token,unit', [('96', 'unitless'), ('96px', 'px'), ('1cm', 'cm'),
                                     ('72pt', 'pt'), ('6pc', 'pc'), ('1mm', 'mm')])
def test_all_supported_source_unit_labels(token, unit):
    report = build_import_report(result_for((Point(1, 2),),
                                           attributes=(('width', token), ('height', token))))
    assert report.coordinates.source_units == (unit, unit)


def test_builder_preserves_actual_flipped_root_matrix_and_notices():
    result = result_for((Point(1, 2),), notices=(SvgNotice('recorded', 'unchanged'),))
    viewport = replace(result.document.viewport, matrix=(1, 0, 0, -1, 0, 20))
    result = replace(result, document=replace(result.document, viewport=viewport), flipped=True)
    report = build_import_report(result)
    assert report.coordinates.flipped is True
    assert report.coordinates.matrix_mm == viewport.matrix
    assert report.notices == result.notices


def test_missing_recorded_root_facts_are_an_error():
    result = result_for((Point(1, 2),))
    with pytest.raises(ValueError):
        build_import_report(replace(result, document=replace(result.document, root_attributes=())))


def test_actual_open_fill_is_reported_open_and_geometry_is_untouched():
    from mikrocam.bridge.svg_import import import_svg_bytes
    result = import_svg_bytes(b'<svg width="10mm" height="10mm" viewBox="0 0 10 10">'
                              b'<path d="M1 1L5 1L5 5"/></svg>', 'open.svg', flip=True)
    before = tuple(g.wkb for g in result.geometry_mm)
    report = build_import_report(result)
    assert report.quality.open_paths == 1 and report.quality.closed_paths == 0
    assert report.quality.geometry_count == report.quality.valid_count == 1
    assert report.quality.bounds_mm == pytest.approx((1, 5, 5, 9))
    assert report.coordinates.flipped is True
    assert tuple(g.wkb for g in result.geometry_mm) == before


def test_combined_notice_truncation_is_preserved():
    result = result_for((Point(1, 2),), notices=(SvgNotice('x', 'document'),) * 200)
    rendered = replace(result.rendered[0], notices=(SvgNotice('y', 'render'),))
    report = build_import_report(replace(result, rendered=(rendered,)))
    assert len(report.notices) == 200
    assert report.notices[-1] == SvgNotice('notices-truncated', '2 further notices omitted')


def test_empty_collections_count_once_and_never_invent_bounds():
    report = build_import_report(result_for((GeometryCollection(), Polygon())))
    assert report.quality == ImportQuality(None, 2, 0, 0, 2, 0, 0, CURVE_TOLERANCE_MM)


def test_quality_can_record_invalid_nonempty_material_without_claiming_validity():
    value = quality(valid_count=0, invalid_count=1)
    assert value.invalid_count == 1 and value.valid_count == 0


def test_builder_enforces_aggregate_material_coordinate_budget(monkeypatch):
    from mikrocam.core import import_report as module
    result = result_for((GeometryCollection((Point(0, 0), LineString(((0, 0), (1, 1))))),))
    monkeypatch.setattr(module, 'MAX_SVG_POINTS', 3)
    assert build_import_report(result).quality.geometry_count == 2
    monkeypatch.setattr(module, 'MAX_SVG_POINTS', 2)
    with pytest.raises(ValueError, match='coordinate budget'):
        build_import_report(result)


@pytest.mark.parametrize('attributes', [
    (('width', '10mm'),), (('width', '10%'), ('height', '10mm')),
    (('width', '10mm'), ('height', '10mm'), ('viewBox', '0 0 1 1 1')),
    (('width', '10mm'), ('height', '10mm'), ('preserveAspectRatio', 'xMidYMid slice')),
])
def test_builder_rejects_incomplete_or_invalid_recorded_source_facts(attributes):
    result = result_for((Point(1, 2),))
    document = replace(result.document, root_attributes=attributes)
    with pytest.raises(ValueError):
        build_import_report(replace(result, document=document))
