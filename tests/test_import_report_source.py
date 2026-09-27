"""Source sizing and actual flip remain available without re-reading an SVG."""
from dataclasses import replace

import pytest

from mikrocam.bridge.svg_import import import_svg_bytes
from mikrocam.importers.svg_document import parse_svg_document


SOURCE = (b'<svg width="1in" height="25.4mm" viewBox="10 20 96 96" '
          b'preserveAspectRatio="xMinYMax meet" transform="translate(3 4)">'
          b'<rect x="10" y="20" width="4" height="5"/></svg>')


def test_original_root_facts_preserved_verbatim_without_mutable_xml():
    document = parse_svg_document(SOURCE, 'facts.svg')
    assert document.root_attributes == (('width', '1in'), ('height', '25.4mm'),
                                       ('viewBox', '10 20 96 96'),
                                       ('preserveAspectRatio', 'xMinYMax meet'),
                                       ('transform', 'translate(3 4)'))
    assert isinstance(document.root_attributes, tuple)
    assert SOURCE.startswith(b'<svg width="1in"')


@pytest.mark.parametrize('flip', [False, True])
def test_result_records_actual_flip_independently_of_notice_text(flip):
    result = import_svg_bytes(SOURCE, 'facts.svg', flip=flip)
    assert result.flipped is flip
    assert dict(result.document.root_attributes)['viewBox'] == '10 20 96 96'
    assert result.document.viewport.width_mm == pytest.approx(25.4)


def test_root_fact_validation_and_flip_strictness():
    result = import_svg_bytes(SOURCE, 'facts.svg')
    with pytest.raises(ValueError):
        replace(result.document, root_attributes=[('width', '1in')])
    with pytest.raises(ValueError):
        replace(result.document, root_attributes=(('width', '1in'), ('width', '2in')))
    with pytest.raises(ValueError):
        replace(result, flipped=1)
