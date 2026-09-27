"""Strict bounded schema-one JSON-safe import report dictionaries."""
from dataclasses import fields
import json

from .import_report import ImportCoordinates, ImportQuality, ImportReport
from .svg_models import SvgNotice

REPORT_SCHEMA_VERSION = 1
MAX_REPORT_BYTES = 1048576
_TOP_KEYS = {'schema_version', 'source_name', 'source_sha256', 'coordinates', 'quality', 'notices'}
_TUPLES = {'source_units': 2, 'view_box': 4, 'viewport_mm': 2, 'matrix_mm': 6,
           'bounds_mm': 4}


def _record(value: object, keys: set[str], label: str) -> dict:
    if type(value) is not dict or value.keys() != keys:
        raise ValueError(f'{label} requires exactly the schema keys')
    return value


def _fields(record: object) -> dict:
    result = {}
    for field in fields(record):
        value = getattr(record, field.name)
        result[field.name] = list(value) if type(value) is tuple else value
    return result


def _decode(value: object, cls: type) -> dict:
    record = _record(value, {field.name for field in fields(cls)}, cls.__name__)
    result = dict(record)
    for name, count in _TUPLES.items():
        if name not in result or result[name] is None:
            continue
        values = result[name]
        if type(values) is not list or len(values) != count:
            raise ValueError(f'{name} requires a bounded JSON array')
        result[name] = tuple(values)
    return result


def _size(value: dict) -> None:
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                             allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ValueError('Import report must be finite strict UTF-8 JSON data') from error
    if len(encoded) > MAX_REPORT_BYTES:
        raise ValueError('Import report exceeds canonical JSON byte limit')


def report_to_dict(report: ImportReport) -> dict:
    """Return fresh detached JSON containers for an exact validated report."""
    if type(report) is not ImportReport:
        raise ValueError('Codec requires an exact ImportReport')
    value = dict(schema_version=REPORT_SCHEMA_VERSION, source_name=report.source_name,
                 source_sha256=report.source_sha256, coordinates=_fields(report.coordinates),
                 quality=_fields(report.quality), notices=[_fields(n) for n in report.notices])
    _size(value)
    return value


def report_from_dict(value: object) -> ImportReport:
    """Decode schema one with no coercion, migration, file access or geometry import."""
    data = _record(value, _TOP_KEYS, 'Import report')
    if type(data['schema_version']) is not int or data['schema_version'] != REPORT_SCHEMA_VERSION:
        raise ValueError('Unsupported import report schema version')
    notices = data['notices']
    if type(notices) is not list or len(notices) > 200:
        raise ValueError('Notices require a bounded JSON array')
    coordinates = ImportCoordinates(**_decode(data['coordinates'], ImportCoordinates))
    quality = ImportQuality(**_decode(data['quality'], ImportQuality))
    records = tuple(SvgNotice(**_decode(notice, SvgNotice)) for notice in notices)
    report = ImportReport(data['source_name'], data['source_sha256'], coordinates, quality, records)
    _size(data)
    return report
