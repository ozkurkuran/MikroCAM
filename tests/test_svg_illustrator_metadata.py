import xml.etree.ElementTree as ET

import pytest

from mikrocam.importers.svg_metadata import resolve_page_attributes
from mikrocam.core.svg_transform import resolve_svg_viewport


TPG = 'http://ns.adobe.com/xap/1.0/t/pg/'
DIM = 'http://ns.adobe.com/xap/1.0/sType/Dimensions#'


def root(attributes='', fields=None, *, unit='Millimeters', width='25.4', height='50.8',
         attribute_fields=False):
    node = ET.fromstring(f'<svg {attributes}/>')
    if fields is None:
        page = ET.SubElement(ET.SubElement(node, 'metadata'), f'{{{TPG}}}MaxPageSize')
        for key, value in (('w', width), ('h', height), ('unit', unit)):
            if attribute_fields:
                page.set(f'{{{DIM}}}{key}', value)
            else:
                ET.SubElement(page, f'{{{DIM}}}{key}').text = value
    else:
        node.append(ET.fromstring(fields))
    return node


@pytest.mark.parametrize('unit,w,h', [('mm', '25.4', '50.8'), ('CENTIMETERS', '2.54', '5.08'),
    ('inch', '1', '2'), ('INCHES', '1', '2'), ('point', '72', '144'),
    ('Points', '72', '144'), ('pica', '6', '12'), ('PICAS', '6', '12'),
    ('pixel', '96', '192'), ('Pixels', '96', '192'), ('in', '1', '2'),
    ('pt', '72', '144'), ('pc', '6', '12'), ('px', '96', '192')])
@pytest.mark.parametrize('attribute_fields', [False, True])
def test_exact_xmp_fields_and_supported_units_supply_physical_page(unit, w, h, attribute_fields):
    node = root('viewBox="0 0 96 192"', unit=unit, width=w, height=h,
                attribute_fields=attribute_fields)
    original = ET.tostring(node)
    attrs, notices = resolve_page_attributes(node)
    viewport = resolve_svg_viewport(attrs)
    assert (viewport.width_mm, viewport.height_mm) == pytest.approx((25.4, 50.8))
    assert any(notice.code == 'xmp-page-size' for notice in notices)
    assert ET.tostring(node) == original


def test_fallback_is_independent_by_axis_and_percentage_means_page_not_percent_of_page():
    node = root('width="10mm" height="50%" viewBox="0 0 10 20"')
    attrs, notices = resolve_page_attributes(node)
    viewport = resolve_svg_viewport(attrs)
    assert (viewport.width_mm, viewport.height_mm) == pytest.approx((10, 50.8))
    assert dict(attrs)['width'] == '10mm'
    assert any(notice.code == 'xmp-conflict' for notice in notices)
    assert node.attrib['height'] == '50%'


def test_complete_explicit_dimensions_override_conflicting_xmp():
    attrs, notices = resolve_page_attributes(root('width="96px" height="10mm"'))
    assert dict(attrs)['width'] == '96px' and dict(attrs)['height'] == '10mm'
    assert any(notice.code == 'xmp-conflict' for notice in notices)


def test_without_metadata_existing_viewbox_inference_is_unchanged():
    node = ET.fromstring('<svg width="10mm" viewBox="0 0 10 20"/>')
    attrs, notices = resolve_page_attributes(node)
    assert attrs == tuple(node.attrib.items()) and notices == ()
    assert resolve_svg_viewport(attrs).height_mm == pytest.approx(20)


@pytest.mark.parametrize('changes', [dict(unit='furlong'), dict(width='nan'), dict(height='0'),
                                   dict(width='-1'), dict(width='1e10'), dict(width='1 2')])
def test_invalid_required_metadata_rejects(changes):
    with pytest.raises(ValueError):
        resolve_page_attributes(root('viewBox="0 0 1 1"', **changes))


def test_duplicate_page_and_duplicate_fields_reject_when_needed():
    node = root('width="100%" height="100%"')
    node.append(node.find('metadata'))
    with pytest.raises(ValueError):
        resolve_page_attributes(node)
    node = root()
    page = node.find(f'.//{{{TPG}}}MaxPageSize')
    page.set(f'{{{DIM}}}w', '25.4')
    with pytest.raises(ValueError):
        resolve_page_attributes(node)


def test_invalid_unused_metadata_warns_without_replacing_complete_root():
    attrs, notices = resolve_page_attributes(root('width="1in" height="2in"', unit='unknown'))
    assert dict(attrs)['width'] == '1in'
    assert any(notice.code == 'xmp-invalid' for notice in notices)


@pytest.mark.parametrize('attributes', ['width="10%" height="20%"',
    'width="nanmm" height="1mm"', 'width="0mm" height="1mm"',
    'width="-1%" height="10mm"', 'width="1 2%" height="10mm"',
    'width="1 %" height="10mm"'])
def test_missing_metadata_or_malformed_root_never_guesses_page(attributes):
    with pytest.raises(ValueError):
        resolve_page_attributes(ET.fromstring(f'<svg {attributes}/>'))


@pytest.mark.parametrize('namespace', ['https://untrusted.invalid/', 'http://ns.adobe.com/xap/1.0/t/pg#'])
def test_foreign_same_local_names_do_not_supply_page_evidence(namespace):
    node = root('width="100%" height="100%"')
    node.find(f'.//{{{TPG}}}MaxPageSize').tag = f'{{{namespace}}}MaxPageSize'
    with pytest.raises(ValueError):
        resolve_page_attributes(node)


def test_incomplete_or_foreign_dimension_fields_cannot_supply_page_evidence():
    for foreign in (False, True):
        node = root('width="100%" height="100%"')
        page = node.find(f'.//{{{TPG}}}MaxPageSize')
        field = page.find(f'{{{DIM}}}w')
        if foreign:
            field.tag = '{https://untrusted.invalid/}w'
        else:
            page.remove(field)
        with pytest.raises(ValueError):
            resolve_page_attributes(node)


@pytest.mark.parametrize('token', ['garbagemm', '0mm', '-1mm', '1 %', 'nan%'])
def test_valid_xmp_never_repairs_malformed_explicit_dimension(token):
    with pytest.raises(ValueError):
        resolve_page_attributes(root(f'width="{token}" height="10mm"'))


def test_physical_limit_applies_after_xmp_unit_conversion():
    attrs, _ = resolve_page_attributes(root(width='2000000000', height='96', unit='px'))
    assert float(dict(attrs)['width'][:-2]) == pytest.approx(2000000000 * 25.4 / 96)


@pytest.mark.parametrize('container', ['defs', 'g', '{urn:foreign}metadata'])
def test_page_evidence_outside_svg_metadata_cannot_supply_scale(container):
    node = root('width="100%" height="100%"')
    node[0].tag = container
    with pytest.raises(ValueError, match='require valid XMP'):
        resolve_page_attributes(node)


def test_official_svg_metadata_namespace_and_rdf_wrapper_are_supported():
    node = root('width="100%" height="100%"')
    metadata = node[0]
    metadata.tag = '{http://www.w3.org/2000/svg}metadata'
    page = metadata[0]
    metadata.remove(page)
    rdf = ET.SubElement(metadata, '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF')
    ET.SubElement(rdf, '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description').append(page)
    attrs, _ = resolve_page_attributes(node)
    assert resolve_svg_viewport(attrs).width_mm == pytest.approx(25.4)
