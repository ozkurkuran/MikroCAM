from dataclasses import replace, FrozenInstanceError
import pytest
from shapely.geometry import Polygon, MultiPolygon, LineString
from mikrocam.core.pdf_models import *


def page():
    return PdfPageInfo(0, (0, 0, 100, 100), (0, 0, 100, 100), 0, 1)


def geometry():
    return (Polygon(((1, 1), (3, 1), (3, 2), (1, 2))),)


def report():
    return PdfImportReport(
        "board.pdf",
        "a" * 64,
        1,
        page(),
        PdfOptions(0),
        (100, 100),
        (1, 0, 0, 1, 0, 0),
        (1, 1, 3, 2),
        1,
        1,
        5,
        geometry_sha256(geometry()),
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"index": True},
        {"index": 128},
        {"media_box": [0, 0, 10, 10]},
        {"media_box": (0, 0, 0, 1)},
        {"crop_box": (-1, 0, 100, 100)},
        {"rotation": 45},
        {"rotation": False},
        {"user_unit": 0},
        {"user_unit": 75001},
        {"user_unit": True},
        {"media_box": (0, 0, 1e9, 1e9), "user_unit": 75000},
    ],
)
def test_invalid_page(changes):
    with pytest.raises(ValueError):
        replace(page(), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"page_index": True},
        {"page_index": 128},
        {"box_mode": "auto"},
        {"flip": 1},
        {"crop_mm": (-1, 0, 1, 1)},
        {"crop_mm": (0, 0, 0, 1)},
        {"crop_mm": [0, 0, 1, 1]},
    ],
)
def test_invalid_options(changes):
    with pytest.raises(ValueError):
        replace(PdfOptions(0), **changes)


@pytest.mark.parametrize(
    "operator,operands",
    [
        ("", ()),
        ("é", ()),
        ("x" * 17, ()),
        ("m", []),
        ("m", (True,)),
        ("m", (float("inf"),)),
        ("m", ("é" * 65,)),
        ("m", ([1, 2],)),
        ("m", ((1,) * 65,)),
        ("m", (0,) * 9),
        ("m", (1e9 + 1,)),
    ],
)
def test_invalid_commands(operator, operands):
    with pytest.raises(ValueError):
        PdfCommand(operator, operands)


def test_document_program_and_immutable_records():
    doc = PdfDocumentInfo("board.pdf", "a" * 64, (page(),))
    assert PdfProgram(doc, 0, (PdfCommand("unknown", ()),))
    with pytest.raises(FrozenInstanceError):
        doc.source_name = "changed"
    for pages in ((), [page()], (replace(page(), index=1),)):
        with pytest.raises(ValueError):
            PdfDocumentInfo("board.pdf", "a" * 64, pages)
    with pytest.raises(ValueError):
        PdfProgram(doc, 1, ())
    with pytest.raises(ValueError):
        PdfDocumentInfo("é" * 129, "a" * 64, (page(),))


@pytest.mark.parametrize(
    "changes",
    [
        {"source_sha256": "A" * 64},
        {"page_count": True},
        {"page_count": 0},
        {"options": PdfOptions(1)},
        {"matrix_mm": (1, 0, 0, 0, 0, 0)},
        {"matrix_mm": [1, 0, 0, 1, 0, 0]},
        {"viewport_mm": (0, 1)},
        {"bounds_mm": (0, 0, 0, 1)},
        {"geometry_count": 0},
        {"path_count": 10001},
        {"point_count": 500001},
        {"precision_mm": 0.02},
        {"notices": []},
        {"notices": ("é" * 257,)},
        {"notices": ("notice",) * 201},
    ],
)
def test_invalid_report(changes):
    with pytest.raises(ValueError):
        replace(report(), **changes)


def test_geometry_agreement_and_lossless_source_review():
    from hashlib import sha256

    data = b"%PDF-1.4\n\xff"
    result = PdfGeometryResult(
        replace(report(), source_sha256=sha256(data).hexdigest()), geometry()
    )
    assert PdfImportReview(data, result).source_bytes is data
    for changes in (
        {"point_count": 4},
        {"geometry_count": 2},
        {"bounds_mm": (0, 0, 3, 2)},
        {"geometry_sha256": "b" * 64},
    ):
        with pytest.raises(ValueError):
            PdfGeometryResult(replace(report(), **changes), geometry())
    with pytest.raises(ValueError):
        PdfImportReview(data, PdfGeometryResult(report(), geometry()))


@pytest.mark.parametrize(
    "value",
    [
        (),
        [],
        (LineString(((0, 0), (1, 1))),),
        (MultiPolygon(geometry()),),
        (Polygon(((0, 0), (1, 1), (0, 1), (1, 0))),),
        (Polygon(((0, 0, 1), (1, 0, 1), (1, 1, 1))),),
    ],
)
def test_geometry_rejects_empty_invalid_nonpolygon_or_3d(value):
    with pytest.raises(ValueError):
        geometry_sha256(value)


def test_hash_order_and_ring_coordinate_count():
    second = Polygon(((10, 10), (11, 10), (11, 11)))
    assert geometry_sha256(geometry() + (second,)) != geometry_sha256(
        (second,) + geometry()
    )
    polygon = Polygon(
        ((0, 0), (5, 0), (5, 5), (0, 5)), [((1, 1), (2, 1), (2, 2), (1, 2))]
    )
    assert geometry_facts((polygon,)) == ((0.0, 0.0, 5.0, 5.0), 10)


def test_empty_pdf_string_operand_is_valid_shape():
    assert PdfCommand("unknown", ("",))


def test_geometry_coordinate_budget_precedes_expensive_validity(monkeypatch):
    import mikrocam.core.pdf_models as module

    monkeypatch.setattr(module, "MAX_PDF_POINTS", 4)
    monkeypatch.setattr(
        Polygon,
        "is_valid",
        property(lambda self: pytest.fail("Validate the coordinate budget first")),
    )
    with pytest.raises(ValueError, match="coordinates"):
        geometry_facts(geometry())
