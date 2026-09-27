"""Existing path facts and independently authored whole-document geometry."""
import hashlib
import json
from pathlib import Path

import pytest
from shapely import union_all

from mikrocam.bridge.svg_import import import_svg_bytes, load_svg_file


REFERENCE = Path(__file__).parent / 'reference'
CASES = json.loads((REFERENCE / 'svg_paths.json').read_text(encoding='utf-8'))


def test_existing_open_subpath_reference_through_physical_bridge():
    case = CASES['open_subpaths']
    payload = (f'<svg width="200mm" height="200mm" viewBox="0 0 100 100">'
               f'<path d="{case["path"]}" fill="none"/></svg>').encode()
    result = import_svg_bytes(payload, 'open-reference.svg', flip=False)
    assert len(result.rendered[0].paths_mm) == len(case['coordinates'])
    for actual, expected in zip(result.rendered[0].paths_mm, case['coordinates']):
        assert actual.points == tuple(tuple(point) for point in expected)
        assert not actual.closed


def test_existing_hole_contour_reference_with_explicit_evenodd():
    case = CASES['holes_and_contours']
    payload = (f'<svg width="100mm" height="100mm" viewBox="0 0 100 100">'
               f'<path d="{case["path"]}" fill-rule="evenodd"/></svg>').encode()
    material = union_all(import_svg_bytes(payload, 'hole-reference.svg', flip=False).geometry_mm)
    assert sorted(polygon.area for polygon in material.geoms) == pytest.approx(case['areas'])
    assert sum(len(polygon.interiors) for polygon in material.geoms) == case['holes']
    # The old helper inferred holes regardless of winding. SVG's default nonzero fills this one.
    payload = payload.replace(b'fill-rule="evenodd"', b'fill-rule="nonzero"')
    assert union_all(import_svg_bytes(payload, 'nonzero.svg', flip=False).geometry_mm).area == 104.


def test_authored_document_exact_source_and_analytic_bounds_area():
    path = REFERENCE / 'svg-physical-transform.svg'
    digest = 'd51453ef6998bd33a67c7a2c92b4fec1f01d2e88920855e728235fb5e56d5fb3'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    result = load_svg_file(path, flip=False)
    assert result.document.source_sha256 == digest
    material = union_all(result.geometry_mm)
    assert material.bounds == (10., 10., 30., 20.)
    assert material.area == 200.
