"""Immutable source records and whole-document geometry/coordinate budgets."""
from dataclasses import FrozenInstanceError, replace
import pytest
from shapely import LineString, Polygon
from mikrocam.core.svg_models import SvgNotice, SvgPaint, SvgPath, SvgViewport, SvgElement, SvgDocument, SvgRendered, SvgImportResult
M = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

def document():
    return SvgDocument('source.svg', 'a' * 64, SvgViewport(10.0, 10.0, M), (SvgElement('p', 'path', (('d', 'M0 0L1 1'),), M, SvgPaint()),))

def test_model_defaults_identity_and_immutable_rendered_result():
    doc = document()
    path = SvgPath(((0.0, 0.0), (1.0, 1.0)))
    rendered = SvgRendered((path,), (LineString(path.points),), (SvgNotice('cam', 'Centreline'),))
    result = SvgImportResult(doc, (rendered,))
    assert result.geometry_mm == rendered.geometry_mm and result.notices == rendered.notices
    assert SvgPaint() == SvgPaint(True, False, 1.0, 'butt', 'miter', 4.0, 'nonzero')
    with pytest.raises(FrozenInstanceError):
        doc.elements = ()

@pytest.mark.parametrize('changes', [dict(fill=1), dict(stroke=0), dict(width=-1), dict(width=True), dict(width=float('inf')), dict(width=1000000000.0 + 1), dict(linecap='triangle'), dict(linejoin='arcs'), dict(miterlimit=-0.1), dict(miterlimit=1001), dict(fill_rule='unknown')])
def test_strict_paint(changes):
    with pytest.raises(ValueError):
        SvgPaint(**changes)

@pytest.mark.parametrize('points,closed', [([(0, 0), (1, 1)], False), (((0, 0),), False), (((0, 0), (True, 1)), False), (((0, 0), (float('nan'), 1)), False), (((0, 0), (1000000000.0 + 1, 1)), False), (((0, 0), (1, 0), (0, 0)), True), (((0, 0), (1, 0), (1, 1), (0, 1)), True)])
def test_paths_reject_mutability_nonfinite_and_implicit_close(points, closed):
    with pytest.raises(ValueError):
        SvgPath(points, closed)

def test_path_metadata_preserves_explicit_close_only():
    points = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 0.0))
    assert SvgPath(points, True).closed and (not SvgPath(points).closed)

@pytest.mark.parametrize('factory', [lambda: SvgNotice('x' * 65, 'message'), lambda: SvgNotice('code', 'm' * 513), lambda: SvgViewport(0, 10, M), lambda: SvgViewport(10, float('nan'), M), lambda: SvgElement('id', 'text', (), M, SvgPaint()), lambda: SvgElement('id', 'line', (('x', '1'), ('x', '2')), M, SvgPaint()), lambda: replace(document(), source_sha256='A' * 64), lambda: replace(document(), elements=[]), lambda: SvgRendered([], ()), lambda: SvgRendered((), (LineString([(0, 0, 1), (1, 1, 2)]),)), lambda: SvgRendered((), (Polygon([(0, 0), (1, 1), (0, 1), (1, 0)]),)), lambda: SvgImportResult(document(), ())])
def test_models_reject_invalid_bounded_source_or_geometry(factory):
    with pytest.raises(ValueError):
        factory()

def test_model_coordinate_and_notice_caps(monkeypatch):
    import mikrocam.core.svg_models as module
    doc = document()
    path = SvgPath(((0.0, 0.0), (1.0, 1.0)))
    rendered = SvgRendered((path,), (LineString(path.points),))
    monkeypatch.setattr(module, 'MAX_SVG_POINTS', 3)
    with pytest.raises(ValueError):
        SvgImportResult(doc, (rendered,))
    monkeypatch.setattr(module, 'MAX_ELEMENT_POINTS', 3)
    with pytest.raises(ValueError):
        SvgRendered((path,), (LineString(path.points),))
    with pytest.raises(ValueError):
        replace(doc, notices=(SvgNotice('x', 'm'),) * 201)

def test_combined_notices_keep_first_199_and_explicit_omission_marker():
    doc = replace(document(), notices=tuple((SvgNotice('source', str(i)) for i in range(200))))
    result = SvgImportResult(doc, (SvgRendered((), (), (SvgNotice('render', 'extra'),)),))
    assert len(result.notices) == 200
    assert result.notices[198].message == '198'
    assert result.notices[-1] == SvgNotice('notices-truncated', '2 further notices omitted')

def test_attribute_strings_reject_unencodable_source_facts():
    with pytest.raises(ValueError):
        SvgElement('id', 'line', (('x1', '\ud800'),), M, SvgPaint())
