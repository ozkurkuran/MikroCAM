from dataclasses import replace

import pytest

from mikrocam.core.import_report import ImportCoordinates, build_import_report
from mikrocam.core.import_report_codec import report_from_dict, report_to_dict


def percentage_coordinates(token='100%', unit='%'):
    return ImportCoordinates(token, None, (unit, 'absent'), None, 'none',
                             (10, 20), (1, 0, 0, 1, 0, 0), False)


def test_percentage_source_facts_are_strict_and_have_exact_label():
    assert percentage_coordinates('25.5%').source_units == ('%', 'absent')
    for token, unit in [('0%', '%'), ('-1%', '%'), ('nan%', '%'), ('1 2%', '%'),
                        ('10%', 'mm'), ('10mm', '%'), ('10%%', '%'), ('1 %', '%')]:
        with pytest.raises(ValueError):
            percentage_coordinates(token, unit)


def test_actual_xmp_import_report_keeps_raw_percent_tokens_and_effective_mapping():
    from mikrocam.bridge.svg_import import import_svg_bytes
    source = (b'<svg width="100%" height="100%" viewBox="0 0 10 20" '
              b'xmlns:t="http://ns.adobe.com/xap/1.0/t/pg/" '
              b'xmlns:d="http://ns.adobe.com/xap/1.0/sType/Dimensions#">'
              b'<metadata><t:MaxPageSize d:w="10" d:h="20" d:unit="mm"/></metadata>'
              b'<rect width="10" height="20"/></svg>')
    result = import_svg_bytes(source, 'page.svg', flip=True)
    report = build_import_report(result)
    assert report.coordinates.source_width == report.coordinates.source_height == '100%'
    assert report.coordinates.source_units == ('%', '%')
    assert report.coordinates.viewport_mm == pytest.approx((10, 20))
    assert report.coordinates.matrix_mm == result.document.viewport.matrix
    assert report.quality.bounds_mm == pytest.approx((0, 0, 10, 20))
    assert report_to_dict(report)['schema_version'] == 2
    assert report_from_dict(report_to_dict(report)) == report


def test_schema_one_migrates_valid_old_report_but_never_allows_percentage():
    from test_import_report_codec import report
    data = report_to_dict(report())
    data['schema_version'] = 1
    decoded = report_from_dict(data)
    assert decoded == report()
    assert report_to_dict(decoded)['schema_version'] == 2
    data['coordinates']['source_width'] = '100%'
    data['coordinates']['source_units'][0] = '%'
    with pytest.raises(ValueError):
        report_from_dict(data)


def test_schema_two_percentage_roundtrip_without_changing_container_shape():
    from test_import_report_codec import report
    value = replace(report(), coordinates=percentage_coordinates())
    data = report_to_dict(value)
    assert data['schema_version'] == 2
    assert set(data) == {'schema_version', 'source_name', 'source_sha256', 'coordinates', 'quality', 'notices'}
    assert report_from_dict(data) == value
