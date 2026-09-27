"""Immutable bounded manufacturing source evidence and confirmed file assignments."""

from dataclasses import dataclass
from hashlib import sha256
import re

MAX_MANUFACTURING_FILES = 64
MAX_MANUFACTURING_BYTES = 16777216
MAX_MANUFACTURING_TOTAL_BYTES = 67108864
FORMATS = ("gerber", "excellon")
ROLES = ("F.Cu", "B.Cu", "PTH", "NPTH", "Edge.Cuts", "Other")


def _text(value: str, limit: int, label: str, *, name: bool = False) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{label} requires nonempty text")
    try:
        valid = len(value.encode("utf-8")) <= limit
    except UnicodeError as error:
        raise ValueError(f"{label} requires strict UTF8") from error
    if not valid or name and (value != value.strip() or not value.isprintable()):
        raise ValueError(
            f"{label} requires bounded"
            + (" trimmed printable" if name else "")
            + " text"
        )


def _enum(value: str, values: tuple[str, ...], label: str) -> None:
    if type(value) is not str or value not in values:
        raise ValueError(f"Unsupported {label}")


def _integer(value: int, low: int, high: int, label: str) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} requires integer {low}..{high}")


def _records(values: tuple, cls: type, low: int, high: int, label: str) -> None:
    if (
        type(values) is not tuple
        or not low <= len(values) <= high
        or any(type(v) is not cls for v in values)
    ):
        raise ValueError(
            f"{label} requires {low}..{high} immutable {cls.__name__} records"
        )


def validate_assignment(kind: str, role: str) -> None:
    """Validate a confirmed format/role pair without silently inventing a role."""
    _enum(kind, FORMATS, "format")
    _enum(role, ROLES, "role")
    if kind == "excellon" and role not in ("PTH", "NPTH", "Other"):
        raise ValueError("Excellon permits only PTH, NPTH or Other")


@dataclass(frozen=True)
class ManufacturingEvidence:
    origin: str
    format_hint: str = "unknown"
    role_hint: str = "unknown"
    units_hint: str = "unknown"
    detail: str = ""

    def __post_init__(self) -> None:
        _enum(self.origin, ("contents", "metadata", "filename"), "evidence origin")
        _enum(self.format_hint, FORMATS + ("unknown",), "format hint")
        _enum(self.role_hint, ROLES + ("unknown",), "role hint")
        _enum(self.units_hint, ("MM", "IN", "unknown"), "units hint")
        _text(self.detail, 512, "Evidence detail")


@dataclass(frozen=True)
class ManufacturingInspection:
    source_name: str
    source_sha256: str
    byte_count: int
    format_hint: str
    role_hint: str
    units_hint: str
    evidence: tuple[ManufacturingEvidence, ...]
    issues: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.source_name, 256, "Source name")
        if (
            type(self.source_sha256) is not str
            or re.fullmatch("[0-9a-f]{64}", self.source_sha256) is None
        ):
            raise ValueError("Source identity requires lowercase SHA256")
        _integer(self.byte_count, 1, MAX_MANUFACTURING_BYTES, "Source byte count")
        _enum(self.format_hint, FORMATS + ("unknown",), "format hint")
        _enum(self.role_hint, ROLES + ("unknown",), "role hint")
        _enum(self.units_hint, ("MM", "IN", "unknown"), "units hint")
        _records(self.evidence, ManufacturingEvidence, 0, 32, "Evidence")
        if type(self.issues) is not tuple or len(self.issues) > 20:
            raise ValueError("Issues require a bounded immutable tuple")
        for issue in self.issues:
            _text(issue, 512, "Issue")


@dataclass(frozen=True)
class ManufacturingFile:
    path: str
    source_bytes: bytes
    inspection: ManufacturingInspection | None
    error: str = ""

    def __post_init__(self) -> None:
        _text(self.path, 4096, "File path")
        if type(self.source_bytes) is not bytes or type(self.error) is not str:
            raise ValueError("File requires immutable bytes and text error")
        if self.inspection is None:
            if self.source_bytes != b"":
                raise ValueError("Failed file cannot retain source bytes")
            _text(self.error, 512, "File error")
        elif type(self.inspection) is ManufacturingInspection:
            if (
                self.error
                or not 1 <= len(self.source_bytes) <= MAX_MANUFACTURING_BYTES
                or (
                    len(self.source_bytes) != self.inspection.byte_count
                    or sha256(self.source_bytes).hexdigest()
                    != self.inspection.source_sha256
                )
            ):
                raise ValueError("Successful source bytes and inspection disagree")
        else:
            raise ValueError("File inspection must be immutable facts or None")


@dataclass(frozen=True)
class ManufacturingAssignment:
    source_index: int
    kind: str
    role: str
    output_name: str

    def __post_init__(self) -> None:
        _integer(self.source_index, 0, 63, "Source index")
        validate_assignment(self.kind, self.role)
        _text(self.output_name, 256, "Output name", name=True)


@dataclass(frozen=True)
class ManufacturingReview:
    files: tuple[ManufacturingFile, ...]
    assignments: tuple[ManufacturingAssignment, ...]

    def __post_init__(self) -> None:
        _records(self.files, ManufacturingFile, 1, MAX_MANUFACTURING_FILES, "Files")
        if len({v.path for v in self.files}) != len(self.files):
            raise ValueError("File paths must be unique")
        if sum(len(v.source_bytes) for v in self.files) > MAX_MANUFACTURING_TOTAL_BYTES:
            raise ValueError("Reviewed source set exceeds 64MiB")
        _records(self.assignments, ManufacturingAssignment, 1, 64, "Assignments")
        if len({v.source_index for v in self.assignments}) != len(self.assignments):
            raise ValueError("Selected indices must be unique")
        if len({v.output_name.casefold() for v in self.assignments}) != len(
            self.assignments
        ):
            raise ValueError("Output names must be unique case-insensitively")
        if any(
            v.source_index >= len(self.files)
            or self.files[v.source_index].inspection is None
            for v in self.assignments
        ):
            raise ValueError("Assignments must reference successful files")


@dataclass(frozen=True)
class ManufacturingReport:
    inspection: ManufacturingInspection
    kind: str
    role: str
    parsed_units: str
    units_origin: str

    def __post_init__(self) -> None:
        if type(self.inspection) is not ManufacturingInspection:
            raise ValueError("Report requires immutable source inspection")
        validate_assignment(self.kind, self.role)
        _enum(self.parsed_units, ("MM", "IN"), "parsed units")
        _enum(self.units_origin, ("explicit", "parser"), "units origin")
        if (
            self.units_origin == "explicit"
            and self.inspection.units_hint != self.parsed_units
        ):
            raise ValueError("Explicit units must match inspected source marker")
        if self.inspection.units_hint == "unknown" and self.units_origin != "parser":
            raise ValueError("Unknown source units require parser origin")
