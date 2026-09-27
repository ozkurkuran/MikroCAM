"""Retained source text to optional historical evidence, never host geometry."""
from mikrocam.core.cad_source import CadSourceAssessment, MAX_CAD_SOURCE_BYTES
from mikrocam.core.cad_source_codec import source_from_dict, source_to_dict
from mikrocam.importers.cad_source import detect_cad_source, validate_cad_assessment


def _bounded_bytes(source: str) -> tuple[bytes | None, str]:
    if len(source) > MAX_CAD_SOURCE_BYTES:
        return None, 'Source exceeds the UTF-8 byte limit; assessment unavailable.'
    chunks, count = [], 0
    try:
        for offset in range(0, len(source), 4096):
            chunk = source[offset:offset + 4096].encode('utf-8')
            count += len(chunk)
            if count > MAX_CAD_SOURCE_BYTES:
                return None, 'Source exceeds the UTF-8 byte limit; assessment unavailable.'
            chunks.append(chunk)
    except UnicodeEncodeError:
        return None, 'Source is not strict UTF-8 text; assessment unavailable.'
    return b''.join(chunks), ''


def _unavailable(name: str, source_format: str, digest: str | None, reason: str) -> CadSourceAssessment:
    return CadSourceAssessment(name, source_format, digest, 'Unknown', 'unavailable', (), reason)


def store_cad_source(owner: object, source: str, source_name: str, source_format: str) -> None:
    """Publish only complete encoded evidence; oversized metadata cannot block an import."""
    if type(source) is not str:
        raise ValueError('Retained CAD source must be text')
    # Validate caller identity independently, before parsing or replacing historical data.
    CadSourceAssessment(source_name, source_format, '0' * 64, 'Unknown', 'unknown', (), 'Input validation.')
    encoded, error = _bounded_bytes(source)
    record = (_unavailable(source_name, source_format, None, error) if encoded is None
              else detect_cad_source(encoded, source_name, source_format))
    try:
        validate_cad_assessment(record)
        payload = source_to_dict(record)
    except ValueError:
        record = _unavailable(source_name, source_format, record.source_sha256,
                              'Source evidence is invalid or exceeds the report limit; assessment unavailable.')
        payload = source_to_dict(record)
    owner.cad_source = payload


def read_cad_source(owner: object) -> CadSourceAssessment | None:
    """Decode retained metadata only; old absent fields remain absent without reparsing."""
    payload = getattr(owner, 'cad_source', None)
    if payload is None:
        return None
    record = source_from_dict(payload)
    validate_cad_assessment(record)
    return record
