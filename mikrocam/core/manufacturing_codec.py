"""Strict schema-one historical manufacturing evidence without paths or source bytes."""

from dataclasses import asdict, fields
import json
from .manufacturing_models import (
    ManufacturingEvidence,
    ManufacturingInspection,
    ManufacturingReport,
)

REPORT_SCHEMA_VERSION = 1
MAX_REPORT_BYTES = 65536


def _record(value: object, cls: type, *, schema: bool = False) -> dict:
    keys = {field.name for field in fields(cls)}
    if schema:
        keys.add("schema_version")
    if type(value) is not dict or value.keys() != keys:
        raise ValueError(f"{cls.__name__} requires exact schema keys")
    return dict(value)


def _size(value: dict) -> None:
    try:
        size = len(
            json.dumps(
                value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        )
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise ValueError("Manufacturing report requires strict UTF8 JSON") from error
    if size > MAX_REPORT_BYTES:
        raise ValueError("Manufacturing report exceeds 64KiB canonical JSON")


def report_to_dict(report: ManufacturingReport) -> dict:
    """Encode an exact report as newly detached JSON containers."""
    if type(report) is not ManufacturingReport:
        raise ValueError("Codec requires exact ManufacturingReport")
    report.__post_init__()
    report.inspection.__post_init__()
    for evidence in report.inspection.evidence:
        evidence.__post_init__()
    value = asdict(report)
    value["schema_version"] = REPORT_SCHEMA_VERSION
    value["inspection"]["evidence"] = list(value["inspection"]["evidence"])
    value["inspection"]["issues"] = list(value["inspection"]["issues"])
    _size(value)
    return value


def report_from_dict(value: object) -> ManufacturingReport:
    """Decode strict schema one; optional missing owner fields belong to the bridge."""
    data = _record(value, ManufacturingReport, schema=True)
    version = data.pop("schema_version")
    if type(version) is not int or version != REPORT_SCHEMA_VERSION:
        raise ValueError("Unsupported manufacturing schema")
    inspection = _record(data["inspection"], ManufacturingInspection)
    evidence = inspection["evidence"]
    issues = inspection["issues"]
    if (
        type(evidence) is not list
        or len(evidence) > 32
        or type(issues) is not list
        or len(issues) > 20
    ):
        raise ValueError("Evidence/issues require bounded JSON arrays")
    inspection["evidence"] = tuple(
        ManufacturingEvidence(**_record(v, ManufacturingEvidence)) for v in evidence
    )
    inspection["issues"] = tuple(issues)
    data["inspection"] = ManufacturingInspection(**inspection)
    report = ManufacturingReport(**data)
    _size(value)
    return report
