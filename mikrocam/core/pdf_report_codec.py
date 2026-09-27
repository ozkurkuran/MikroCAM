"""Strict bounded schema-one historical PDF reports, without source or geometry payloads."""

from dataclasses import asdict, fields
import json
from .pdf_models import PdfImportReport, PdfPageInfo, PdfOptions

REPORT_SCHEMA_VERSION = 1
MAX_REPORT_BYTES = 65536


def _record(value: object, cls: type, *, schema: bool = False) -> dict:
    keys = {field.name for field in fields(cls)}
    if schema:
        keys.add("schema_version")
    if type(value) is not dict or value.keys() != keys:
        raise ValueError(f"{cls.__name__} requires exactly the schema keys")
    return dict(value)


def _size(value: dict) -> None:
    try:
        size = len(
            json.dumps(
                value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        )
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise ValueError("PDF report requires strict UTF-8 JSON") from error
    if size > MAX_REPORT_BYTES:
        raise ValueError("PDF report exceeds 64KiB canonical JSON limit")


def _array(value: object, count: int | None, label: str) -> tuple:
    if type(value) is not list or count is not None and len(value) != count:
        raise ValueError(
            f"{label} requires a JSON array"
            + (f" of {count} values" if count is not None else "")
        )
    return tuple(value)


def report_to_dict(report: PdfImportReport) -> dict:
    """Encode strict facts into fresh JSON containers."""
    if type(report) is not PdfImportReport:
        raise ValueError("PDF codec requires an exact PdfImportReport")
    report.__post_init__()
    report.page.__post_init__()
    report.options.__post_init__()
    value = asdict(report)
    value["schema_version"] = REPORT_SCHEMA_VERSION
    for name in ("viewport_mm", "matrix_mm", "bounds_mm", "notices"):
        value[name] = list(value[name])
    for name in ("media_box", "crop_box"):
        value["page"][name] = list(value["page"][name])
    if value["options"]["crop_mm"] is not None:
        value["options"]["crop_mm"] = list(value["options"]["crop_mm"])
    _size(value)
    return value


def report_from_dict(value: object) -> PdfImportReport:
    """Decode only supported exact schema-one records; missing owner fields belong to the bridge."""
    data = _record(value, PdfImportReport, schema=True)
    if (
        type(data.pop("schema_version")) is not int
        or value["schema_version"] != REPORT_SCHEMA_VERSION
    ):
        raise ValueError("Unsupported PDF report schema version")
    page = _record(data["page"], PdfPageInfo)
    page["media_box"] = _array(page["media_box"], 4, "Media box")
    page["crop_box"] = _array(page["crop_box"], 4, "Crop box")
    options = _record(data["options"], PdfOptions)
    if options["crop_mm"] is not None:
        options["crop_mm"] = _array(options["crop_mm"], 4, "Crop")
    data["page"] = PdfPageInfo(**page)
    data["options"] = PdfOptions(**options)
    for name, count in (("viewport_mm", 2), ("matrix_mm", 6), ("bounds_mm", 4)):
        data[name] = _array(data[name], count, name)
    if type(data["notices"]) is not list or len(data["notices"]) > 200:
        raise ValueError("Notices require a bounded JSON array")
    data["notices"] = tuple(data["notices"])
    report = PdfImportReport(**data)
    _size(value)
    return report
