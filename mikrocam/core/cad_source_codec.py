"""Strict schema-one historical source dictionaries with bounded UTF-8 encoding."""
import json

from .cad_source import CadSourceAssessment, CadSourceEvidence


SOURCE_SCHEMA_VERSION = 1
MAX_SOURCE_REPORT_BYTES = 65536
_TOP_KEYS = frozenset(('schema_version', 'source_name', 'source_format', 'source_sha256',
                       'application', 'status', 'evidence', 'reason'))
_EVIDENCE_KEYS = frozenset(('application', 'field', 'value'))


def _record(value: object, keys: frozenset[str], label: str) -> dict:
    if type(value) is not dict or value.keys() != keys:
        raise ValueError(f'{label} requires exactly the schema keys')
    return value


def _size(value: dict) -> None:
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                             allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ValueError('Source assessment requires strict UTF-8 JSON data') from error
    if len(encoded) > MAX_SOURCE_REPORT_BYTES:
        raise ValueError('Source assessment exceeds canonical JSON byte limit')


def source_to_dict(record: CadSourceAssessment) -> dict:
    """Encode an exact assessment into newly detached JSON containers."""
    if type(record) is not CadSourceAssessment:
        raise ValueError('Source codec requires an exact CadSourceAssessment')
    record.__post_init__()
    value = dict(schema_version=SOURCE_SCHEMA_VERSION, source_name=record.source_name,
                 source_format=record.source_format, source_sha256=record.source_sha256,
                 application=record.application, status=record.status,
                 evidence=[dict(application=claim.application, field=claim.field, value=claim.value)
                           for claim in record.evidence], reason=record.reason)
    _size(value)
    return value


def source_from_dict(value: object) -> CadSourceAssessment:
    """Decode strict schema one; missing historical owner fields belong to the bridge."""
    data = _record(value, _TOP_KEYS, 'Source assessment')
    if type(data['schema_version']) is not int or data['schema_version'] != SOURCE_SCHEMA_VERSION:
        raise ValueError('Unsupported source assessment schema version')
    claims = data['evidence']
    if type(claims) is not list or len(claims) > 32:
        raise ValueError('Source evidence requires a bounded JSON array')
    evidence = tuple(CadSourceEvidence(**_record(claim, _EVIDENCE_KEYS, 'Source evidence'))
                     for claim in claims)
    record = CadSourceAssessment(data['source_name'], data['source_format'], data['source_sha256'],
                                 data['application'], data['status'], evidence, data['reason'])
    _size(data)
    return record
