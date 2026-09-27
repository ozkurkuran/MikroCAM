import json
import pytest
from test_manufacturing_models import inspection
from mikrocam.core.manufacturing_models import ManufacturingReport
from mikrocam.core.manufacturing_codec import report_to_dict, report_from_dict


def report():
    return ManufacturingReport(inspection(), "gerber", "F.Cu", "MM", "explicit")


def test_exact_detached_roundtrip():
    data = report_to_dict(report())
    assert (
        data["schema_version"] == 1
        and report_from_dict(json.loads(json.dumps(data))) == report()
    )
    data["inspection"]["evidence"][0]["detail"] = "changed"
    assert (
        report_to_dict(report())["inspection"]["evidence"][0]["detail"] == "MO marker"
    )


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "extra",
        "future",
        "boolversion",
        "evidencekeys",
        "tupleevidence",
        "tupleissues",
        "nan",
        "units",
    ],
)
def test_invalid_schema(change):
    data = report_to_dict(report())
    if change == "missing":
        data.pop("role")
    elif change == "extra":
        data["path"] = "private"
    elif change == "future":
        data["schema_version"] = 2
    elif change == "boolversion":
        data["schema_version"] = True
    elif change == "evidencekeys":
        data["inspection"]["evidence"][0]["extra"] = 1
    elif change == "tupleevidence":
        data["inspection"]["evidence"] = tuple(data["inspection"]["evidence"])
    elif change == "tupleissues":
        data["inspection"]["issues"] = ()
    elif change == "nan":
        data["inspection"]["byte_count"] = float("nan")
    elif change == "units":
        data["parsed_units"] = "IN"
    with pytest.raises(ValueError):
        report_from_dict(data)


def test_exact_canonical_byte_cap(monkeypatch):
    import mikrocam.core.manufacturing_codec as module

    data = report_to_dict(report())
    size = len(
        json.dumps(
            data, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
    )
    monkeypatch.setattr(module, "MAX_REPORT_BYTES", size)
    assert report_to_dict(report()) == data and report_from_dict(data) == report()
    monkeypatch.setattr(module, "MAX_REPORT_BYTES", size - 1)
    with pytest.raises(ValueError):
        report_to_dict(report())
    with pytest.raises(ValueError):
        report_from_dict(data)
