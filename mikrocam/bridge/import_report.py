"""Optional versioned import evidence at the legacy object boundary."""
from mikrocam.core.import_report import ImportReport, build_import_report
from mikrocam.core.import_report_codec import report_from_dict, report_to_dict
from mikrocam.core.svg_models import SvgImportResult


def store_import_report(owner: object, result: SvgImportResult) -> None:
    """Publish a complete summary without modifying source, geometry or tool options."""
    payload = report_to_dict(build_import_report(result))
    owner.import_report = payload


def read_import_report(owner: object) -> ImportReport | None:
    """Read historical data only; missing old/non-SVG metadata is not success evidence."""
    payload = getattr(owner, 'import_report', None)
    return None if payload is None else report_from_dict(payload)
