from copy import deepcopy
import json
import pytest
from test_pdf_vector_models import report
from mikrocam.core.pdf_report_codec import report_to_dict, report_from_dict


def test_roundtrip_fresh_detached_json_containers():
    value = report_to_dict(report())
    assert value["schema_version"] == 1
    assert report_from_dict(json.loads(json.dumps(value))) == report()
    value["page"]["media_box"][0] = -1
    assert report().page.media_box[0] == 0
    assert report_to_dict(report())["page"]["media_box"][0] == 0


@pytest.mark.parametrize(
    "change",
    [
        "unknown",
        "missing",
        "future",
        "boolschema",
        "tuplebounds",
        "badpage",
        "badoptions",
        "nonfinite",
        "null",
        "badnotice",
    ],
)
def test_strict_codec_rejects_invalid_records(change):
    value = report_to_dict(report())
    if change == "unknown":
        value["unknown"] = 1
    elif change == "missing":
        value.pop("geometry_sha256")
    elif change == "future":
        value["schema_version"] = 2
    elif change == "boolschema":
        value["schema_version"] = True
    elif change == "tuplebounds":
        value["bounds_mm"] = tuple(value["bounds_mm"])
    elif change == "badpage":
        value["page"]["extra"] = 1
    elif change == "badoptions":
        value["options"].pop("flip")
    elif change == "nonfinite":
        value["matrix_mm"][0] = float("nan")
    elif change == "null":
        value = None
    elif change == "badnotice":
        value["notices"] = [1]
    with pytest.raises(ValueError):
        report_from_dict(value)


def test_utf8_byte_bound_checked_both_directions(monkeypatch):
    import mikrocam.core.pdf_report_codec as module

    value = report_to_dict(report())
    size = len(
        json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
    )
    monkeypatch.setattr(module, "MAX_REPORT_BYTES", size)
    assert report_from_dict(value) == report()
    assert report_to_dict(report()) == value
    monkeypatch.setattr(module, "MAX_REPORT_BYTES", size - 1)
    with pytest.raises(ValueError):
        report_to_dict(report())
    with pytest.raises(ValueError):
        report_from_dict(value)


def test_no_record_or_mapping_subclasses():
    class Mapping(dict):
        pass

    with pytest.raises(ValueError):
        report_from_dict(Mapping(report_to_dict(report())))
    with pytest.raises(ValueError):
        report_to_dict(object())
