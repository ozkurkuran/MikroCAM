"""Genuine third-party vendor exports, kept byte-identical with recorded provenance and licenses."""
import hashlib
import json
from pathlib import Path

import pytest

from mikrocam.bridge.svg_import import import_svg_bytes
from mikrocam.importers.cad_source import detect_cad_source, validate_cad_assessment


ROOT = Path(__file__).parent / 'reference/cad-source'
PROTEUS = ROOT / 'proteus-breath-analyzer'


def _provenance(folder: Path) -> dict:
    return json.loads((folder / 'provenance.json').read_text(encoding='utf-8'))


def _assert_retained_bytes(folder: Path) -> dict:
    provenance = _provenance(folder)
    for name, record in provenance['files'].items():
        data = (folder / name).read_bytes()
        assert len(data) == record['bytes'], name
        assert hashlib.sha256(data).hexdigest() == record['sha256'], name
        blob = hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()
        assert record.get('git_blob_sha1', blob) == blob, name
    return provenance


def test_proteus_export_is_unmodified_apache_licensed_upstream_bytes():
    provenance = _assert_retained_bytes(PROTEUS)
    assert provenance['license'] == 'Apache-2.0'
    assert provenance['upstream_revision'] == '5872bbe211318a74ec51ccff3bf4ef2fc1d371b7'
    license_text = (PROTEUS / 'LICENSE').read_text(encoding='utf-8')
    assert 'Apache License' in license_text and 'Version 2.0, January 2004' in license_text
    source = (PROTEUS / 'B_A_.svg').read_bytes()
    assert source.count(b'\r\n') == source.count(b'\n') > 0  # Upstream CRLF bytes, never normalized.
    assert b'<desc>Created by Proteus Design Suite</desc>' in source


def test_genuine_proteus_svg_desc_marker_identifies_proteus():
    source = (PROTEUS / 'B_A_.svg').read_bytes()
    assessment = detect_cad_source(source, 'renamed-kicad.svg', 'SVG')
    assert assessment.application == 'Proteus' and assessment.status == 'identified'
    assert [(item.field, item.application, item.value) for item in assessment.evidence] == [
        ('svg.desc', 'Proteus', 'Created by Proteus Design Suite')]
    assert assessment.source_sha256 == _provenance(PROTEUS)['files']['B_A_.svg']['sha256']
    validate_cad_assessment(assessment)  # The retained claim survives the bridge validator.


@pytest.mark.parametrize('object_type', ['geometry', 'gerber'])
def test_genuine_proteus_geometry_import_fails_explicitly_not_partially(object_type):
    # Real Proteus exports mark every filled path with vector-effect:non-scaling-stroke; the
    # importer's documented policy rejects vector-effect, so 018 drill review cannot run yet.
    source = (PROTEUS / 'B_A_.svg').read_bytes()
    with pytest.raises(ValueError, match='vector-effect'):
        import_svg_bytes(source, 'B_A_.svg', object_type=object_type)
