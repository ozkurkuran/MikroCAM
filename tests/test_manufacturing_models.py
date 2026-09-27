from dataclasses import replace, FrozenInstanceError
from hashlib import sha256
import pytest
from mikrocam.core.manufacturing_models import *


def inspection(**kwargs):
    return replace(
        ManufacturingInspection(
            "board.gbr",
            sha256(b"data").hexdigest(),
            4,
            "gerber",
            "F.Cu",
            "MM",
            (
                ManufacturingEvidence(
                    "contents", "gerber", "unknown", "MM", "MO marker"
                ),
            ),
        ),
        **kwargs,
    )


def file(path="board.gbr"):
    return ManufacturingFile(path, b"data", inspection())


@pytest.mark.parametrize(
    "changes",
    [
        {"origin": "other"},
        {"format_hint": "svg"},
        {"role_hint": "top"},
        {"units_hint": "mm"},
        {"detail": ""},
        {"detail": "é" * 257},
        {"detail": "\ud800"},
    ],
)
def test_evidence_invalid(changes):
    with pytest.raises(ValueError):
        replace(ManufacturingEvidence("metadata", detail="TF role"), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"source_name": ""},
        {"source_name": "é" * 129},
        {"source_sha256": "A" * 64},
        {"byte_count": True},
        {"byte_count": 0},
        {"byte_count": 16777217},
        {"format_hint": "svg"},
        {"role_hint": "top"},
        {"units_hint": "mm"},
        {"evidence": []},
        {"evidence": (object(),)},
        {"evidence": (ManufacturingEvidence("contents", detail="x"),) * 33},
        {"issues": []},
        {"issues": ("",)},
        {"issues": ("é" * 257,)},
        {"issues": ("x",) * 21},
    ],
)
def test_inspection_invalid(changes):
    with pytest.raises(ValueError):
        inspection(**changes)


@pytest.mark.parametrize(
    "args",
    [
        ("", b"data", inspection(), ""),
        ("é" * 2049, b"data", inspection(), ""),
        ("a", bytearray(b"data"), inspection(), ""),
        ("a", b"changed", inspection(), ""),
        ("a", b"", None, ""),
        ("a", b"data", None, "failed"),
        ("a", b"data", inspection(), "failed"),
        ("a", b"", None, "é" * 257),
    ],
)
def test_file_invalid(args):
    with pytest.raises(ValueError):
        ManufacturingFile(*args)


@pytest.mark.parametrize(
    "args",
    [
        (True, "gerber", "F.Cu", "a"),
        (64, "gerber", "F.Cu", "a"),
        (0, "unknown", "F.Cu", "a"),
        (0, "excellon", "F.Cu", "a"),
        (0, "gerber", "unknown", "a"),
        (0, "gerber", "F.Cu", " a"),
        (0, "gerber", "F.Cu", "a\n"),
        (0, "gerber", "F.Cu", "é" * 129),
    ],
)
def test_assignment_invalid(args):
    with pytest.raises(ValueError):
        ManufacturingAssignment(*args)


def test_report_unit_origin_relation_and_valid_assignment_roles():
    assert ManufacturingReport(inspection(), "gerber", "PTH", "MM", "explicit")
    for kind, role in [("gerber", v) for v in ROLES] + [
        ("excellon", v) for v in ("PTH", "NPTH", "Other")
    ]:
        validate_assignment(kind, role)
    for parsed, origin in [("IN", "explicit"), ("MM", "wrong"), ("mm", "parser")]:
        with pytest.raises(ValueError):
            ManufacturingReport(inspection(), "gerber", "F.Cu", parsed, origin)
    with pytest.raises(ValueError):
        ManufacturingReport(
            inspection(units_hint="unknown"), "gerber", "F.Cu", "MM", "explicit"
        )
    assert ManufacturingReport(
        inspection(units_hint="unknown"), "gerber", "F.Cu", "IN", "parser"
    )


def test_review_preserves_order_allows_same_hash_and_name_different_paths():
    assignments = (
        ManufacturingAssignment(1, "gerber", "Other", "second"),
        ManufacturingAssignment(0, "gerber", "F.Cu", "first"),
    )
    value = ManufacturingReview(
        (file("dir1/board.gbr"), file("dir2/board.gbr")), assignments
    )
    assert value.assignments is assignments
    with pytest.raises(FrozenInstanceError):
        value.files = ()


@pytest.mark.parametrize(
    "change",
    [
        "fileslist",
        "empty",
        "duplicatepath",
        "assignmentlist",
        "duplicateindex",
        "badindex",
        "failed",
        "duplicatename",
    ],
)
def test_review_invalid(change):
    files = (file("a"), file("b"))
    assignments = (ManufacturingAssignment(0, "gerber", "F.Cu", "A"),)
    if change == "fileslist":
        files = list(files)
    elif change == "empty":
        assignments = ()
    elif change == "duplicatepath":
        files = (file(), file())
    elif change == "assignmentlist":
        assignments = list(assignments)
    elif change == "duplicateindex":
        assignments = assignments + (
            ManufacturingAssignment(0, "gerber", "Other", "B"),
        )
    elif change == "badindex":
        assignments = (ManufacturingAssignment(2, "gerber", "Other", "B"),)
    elif change == "failed":
        files = (ManufacturingFile("a", b"", None, "failed"), file("b"))
    elif change == "duplicatename":
        assignments = assignments + (
            ManufacturingAssignment(1, "gerber", "Other", "a"),
        )
    with pytest.raises(ValueError):
        ManufacturingReview(files, assignments)


def test_small_patched_source_set_byte_limit_and_file_count(monkeypatch):
    import mikrocam.core.manufacturing_models as module

    assignment = (ManufacturingAssignment(0, "gerber", "Other", "one"),)
    monkeypatch.setattr(module, "MAX_MANUFACTURING_TOTAL_BYTES", 7)
    with pytest.raises(ValueError, match="64MiB"):
        ManufacturingReview((file("a"), file("b")), assignment)
    monkeypatch.setattr(module, "MAX_MANUFACTURING_TOTAL_BYTES", 8)
    assert ManufacturingReview((file("a"), file("b")), assignment)
    monkeypatch.setattr(module, "MAX_MANUFACTURING_FILES", 1)
    with pytest.raises(ValueError):
        ManufacturingReview((file("a"), file("b")), assignment)
