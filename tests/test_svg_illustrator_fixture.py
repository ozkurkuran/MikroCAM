"""Independent analytic checks for original artwork, never claimed as a vendor export."""
from hashlib import sha256
from pathlib import Path

import pytest
from shapely import union_all

from mikrocam.bridge.svg_import import import_svg_bytes
from mikrocam.core.import_report import build_import_report
from mikrocam.core.import_report_codec import report_from_dict, report_to_dict


FIXTURE = Path(__file__).parent / 'reference/svg-illustrator.svg'


@pytest.mark.parametrize('object_type', ['geometry', 'gerber'])
@pytest.mark.parametrize('flip', [False, True])
def test_authored_fixture_physical_material_and_historical_source_report(object_type, flip):
    source = FIXTURE.read_bytes()
    result = import_svg_bytes(source, FIXTURE.name, flip=flip, object_type=object_type)
    material = union_all(result.geometry_mm)
    bounds = (15, 16, 35, 29) if flip else (15, 11, 35, 24)
    assert material.is_valid and material.bounds == pytest.approx(bounds)
    assert material.area == pytest.approx(130, abs=.001)
    assert len(material.geoms) == 2
    assert len(result.document.elements) == 1
    element = result.document.elements[0]
    assert element.layer_path == ('Visible material',)
    assert len(element.clips) == 1
    assert dict(element.attributes)['class'] == 'artwork'
    assert 'style' not in dict(element.attributes)
    assert len(result.rendered[0].paths_mm) == 2
    assert all(path.closed for path in result.rendered[0].paths_mm)
    report = build_import_report(result)
    assert report.source_sha256 == sha256(source).hexdigest()
    assert report.coordinates.source_units == ('%', '%')
    assert report.coordinates.source_width == report.coordinates.source_height == '100%'
    assert report.coordinates.viewport_mm == pytest.approx((60, 40))
    assert report.quality.bounds_mm == pytest.approx(bounds)
    assert report.quality.closed_paths == 2 and report.quality.open_paths == 0
    assert report.quality.invalid_count == 0
    assert report_from_dict(report_to_dict(report)) == report
    assert any('xmp' in notice.message.lower() for notice in report.notices)
    assert FIXTURE.read_bytes() == source


def test_fixture_declares_authored_origin_and_license_without_vendor_claim():
    text = FIXTURE.read_text(encoding='utf-8')
    assert 'SPDX-License-Identifier: MIT' in text
    assert 'authored' in text and 'not exported by Adobe Illustrator' in text
