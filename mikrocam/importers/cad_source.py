"""Offline source assessment from explicit bounded producer metadata only."""
from dataclasses import replace
import hashlib
import re

from mikrocam.core.cad_source import CadSourceAssessment, MAX_CAD_SOURCE_BYTES
from .cad_dxf_source import dxf_source_evidence
from .cad_svg_source import svg_source_evidence
from .cad_producer import classify_producer, desc_declaration, is_inkscape_version, producer_declaration


def validate_cad_assessment(record: CadSourceAssessment) -> None:
    """Reject retained evidence whose field, format or producer interpretation disagrees."""
    if type(record) is not CadSourceAssessment:
        raise ValueError('Source evidence requires an exact assessment')
    record.__post_init__()
    for claim in record.evidence:
        if not claim.field.startswith(record.source_format.lower() + '.'):
            raise ValueError('Source evidence field does not match its format')
        if claim.field == 'svg.inkscape.version':
            if not is_inkscape_version(claim.value):
                raise ValueError('Retained Inkscape version is malformed')
            application = 'Inkscape'
        elif claim.field == 'svg.xmp.CreatorTool':
            application = classify_producer(claim.value)
        elif claim.field in ('svg.desc', 'svg.generator-comment', 'dxf.999'):
            if claim.field == 'dxf.999' and not re.match(
                    r'\s*(?:Generator\s*:|Creator\s*:|Created\s+with\b|Generated\s+by\b)', claim.value, re.I):
                raise ValueError('Retained DXF comment is not a producer declaration')
            producer = (desc_declaration if claim.field == 'svg.desc' else producer_declaration)(claim.value)
            if producer is None:
                raise ValueError('Retained source field is not a producer declaration')
            application = classify_producer(producer)
        else:
            raise ValueError('Unsupported retained source evidence field')
        if application != claim.application:
            raise ValueError('Retained source application disagrees with its producer value')


def detect_cad_source(source: bytes, source_name: str, source_format: str) -> CadSourceAssessment:
    """Keep missing/conflicting/uninspectable sources Unknown without guessing geometry."""
    if type(source) is not bytes:
        raise ValueError('CAD source inspection requires exact bytes')
    base = CadSourceAssessment(source_name, source_format, None, 'Unknown', 'unavailable', (),
                               'Source exceeds the metadata inspection byte limit.')
    if len(source) > MAX_CAD_SOURCE_BYTES:
        return base
    base = replace(base, source_sha256=hashlib.sha256(source).hexdigest())
    try:
        evidence = (svg_source_evidence(source) if source_format == 'SVG'
                    else dxf_source_evidence(source))
        evidence = tuple(dict.fromkeys(evidence))
        applications = {claim.application for claim in evidence}
        if len(applications) > 1:
            return replace(base, status='conflicting', evidence=evidence,
                           reason='Producer metadata contains conflicting application claims; source is Unknown.')
        if not applications or applications == {'Unknown'}:
            return replace(base, status='unknown', evidence=evidence,
                           reason='No supported explicit producer claim was found; source is Unknown.')
        return replace(base, application=next(iter(applications)), status='identified', evidence=evidence,
                       reason='Embedded producer metadata indicates this application; it is not proof of authorship.')
    except ValueError as error:
        return replace(base, reason=('Source metadata could not be inspected: ' + str(error))[:512])
