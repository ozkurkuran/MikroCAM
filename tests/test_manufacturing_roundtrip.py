"""Real legacy parsers and normal factory boundary retain exact reviewed source evidence."""

from copy import deepcopy
from contextlib import nullcontext
import json
import logging
from types import SimpleNamespace
import pytest
from shapely import union_all
from mikrocam.bridge.manufacturing_import import (
    inspect_manufacturing_files,
    review_manufacturing_files,
    import_manufacturing_review,
    read_manufacturing_report,
)
from mikrocam.core.manufacturing_models import ManufacturingAssignment


def source(kind, units):
    if kind == "excellon":
        mode = "METRIC" if units == "MM" else "INCH"
        diameter = "2.54" if units == "MM" else ".1"
        position = "X25.4Y50.8" if units == "MM" else "X1.0Y2.0"
        return f"M48\r\n; authored ÿ\r\n{mode},TZ\r\nT1C{diameter}\r\n%\r\nT1\r\n{position}\r\nM30\r\n".encode(
            "latin1"
        )
    header = f"G04 authored ÿ*%TF.FileFunction,Copper,L1,Top*%%FSLAX24Y24*%%MO{units}*%"
    position = "X254000Y508000" if units == "MM" else "X10000Y20000"
    diameter = "2.54" if units == "MM" else ".1"
    if kind == "macro":
        inner = "1.27" if units == "MM" else ".05"
        return (
            header
            + f"%AMRING*1,1,$1,0,0*1,0,$2,0,0*%%ADD10RING,{diameter}X{inner}*%D10*"
            + position
            + "D03*M02*"
        ).encode("latin1")
    end = "X508000Y508000" if units == "MM" else "X20000Y20000"
    return (
        header + f"%ADD10C,{diameter}*%D10*" + position + "D02*" + end + "D01*M02*"
    ).encode("latin1")


def legacy_geometry(create, kind, units, host_units):
    """Independent conventional commands lock the existing parser's geometry behavior."""
    obj = create("excellon" if kind == "excellon" else "gerber", "legacy control")
    if kind == "excellon":
        assert (
            obj.parse_lines(source(kind, units).decode("latin1").splitlines()) is None
        )
        assert obj.create_geometry() != "fail"
    else:
        position = "X254000Y508000" if units == "MM" else "X10000Y20000"
        end = "X508000Y508000" if units == "MM" else "X20000Y20000"
        diameter, inner = ("2.54", "1.27") if units == "MM" else (".1", ".05")
        commands = ["%FSLAX24Y24*%", f"%MO{units}*%"]
        if kind == "macro":
            commands.extend(
                ["%AMRING*1,1,$1,0,0*1,0,$2,0,0*%", f"%ADD10RING,{diameter}X{inner}*%"]
            )
        else:
            commands.append(f"%ADD10C,{diameter}*%")
        commands.extend(["D10*", position + ("D03*" if kind == "macro" else "D02*")])
        if kind == "gerber":
            commands.append(end + "D01*")
        commands.append("M02*")
        assert obj.parse_lines(commands) is None
    if obj.units != host_units:
        obj.convert_units(host_units)
    return union_all(obj.solid_geometry)


@pytest.fixture
def host(qtbot, monkeypatch):
    from appObjects import AppObjectTemplate
    from appObjects.GerberObject import GerberObject
    from appObjects.ExcellonObject import ExcellonObject
    from defaults import AppDefaults

    monkeypatch.setattr(
        AppObjectTemplate, "ShapeCollection", lambda **kwargs: SimpleNamespace()
    )
    options = deepcopy(AppDefaults.factory_defaults)
    options.update(tools_mill_feedrate=321.25, tools_drill_feedrate_z=123.25)
    signal = SimpleNamespace(emit=lambda *args: None)
    app = SimpleNamespace(
        options=options,
        defaults=options,
        app_units="MM",
        decimals=4,
        abort_flag=False,
        use_3d_engine=True,
        call_source="app",
        pool=None,
        log=logging.getLogger("manufacturing-real"),
        inform=signal,
        proc_container=SimpleNamespace(
            update_view_text=lambda *args: None,
            new_text="",
            new=lambda *args: nullcontext(),
        ),
        plotcanvas=SimpleNamespace(
            view=SimpleNamespace(scene=None),
            new_shape_group=lambda: SimpleNamespace(),
            new_shape_collection=lambda **kwargs: SimpleNamespace(),
        ),
    )
    objects, published, conversions = [], [], []

    def create(kind, name):
        obj = (GerberObject if kind == "gerber" else ExcellonObject)(name, app)
        obj.units = app.app_units
        for key, value in app.options.items():
            if key.startswith(kind + "_"):
                obj.obj_options[key[len(kind) + 1 :]] = deepcopy(value)
            elif key.startswith("tools_"):
                obj.obj_options[key] = deepcopy(value)
        objects.append(obj)
        return obj

    def factory(kind, name, initialize, **kwargs):
        obj = create(kind, name)
        if initialize(obj, app) == "fail":
            return "fail"
        # Exactly the normal AppObject.new_object post-initializer unit boundary.
        if app.options["units"].upper() != obj.units.upper():
            conversions.append((obj.units, app.options["units"]))
            obj.convert_units(app.options["units"])
        published.append(obj)
        return obj

    app.app_obj = SimpleNamespace(new_object=factory)
    yield app, create, published, conversions
    for obj in objects:
        obj.deleteLater()


@pytest.mark.parametrize("kind", ["gerber", "macro", "excellon"])
@pytest.mark.parametrize("source_units", ["MM", "IN"])
@pytest.mark.parametrize("host_units", ["MM", "IN"])
def test_actual_compact_x2_macro_drill_parse_conversion_and_serializer(
    tmp_path, host, kind, source_units, host_units
):
    from camlib import to_dict, dict2obj

    app, create, published, conversions = host
    app.app_units = host_units
    app.options["units"] = host_units
    original = deepcopy(app.options)
    data = source(kind, source_units)
    path = tmp_path / ("board-PTH.drl" if kind == "excellon" else "board-F_Cu.gbr")
    path.write_bytes(data)
    files = inspect_manufacturing_files((str(path),))
    assert not files[0].error
    actual_kind = "excellon" if kind == "excellon" else "gerber"
    role = "PTH" if kind == "excellon" else "F.Cu"
    review = review_manufacturing_files(
        files, (ManufacturingAssignment(0, actual_kind, role, "actual parsed"),)
    )
    receipts = tuple(import_manufacturing_review(app, review))
    assert len(receipts) == 1 and not receipts[0].error, receipts
    obj = receipts[0].owner
    assert published == [obj] and obj.units == host_units
    assert len(conversions) == int(source_units != host_units)
    report = read_manufacturing_report(obj)
    assert (
        report.parsed_units == source_units
        and report.units_origin == "explicit"
        and report.role == role
    )
    assert (
        obj.source_file.encode("latin1") == data == path.read_bytes()
        and app.options == original
    )
    assert obj.obj_options["tools_mill_feedrate"] == 321.25
    assert obj.obj_options["tools_drill_feedrate_z"] == 123.25
    factor = 1 if host_units == "MM" else 25.4
    material = union_all(obj.solid_geometry)
    assert material.equals_exact(
        legacy_geometry(create, kind, source_units, host_units), 1e-6
    )
    expected = (
        (24.13, 49.53, 52.07, 52.07)
        if kind == "gerber"
        else (24.13, 49.53, 26.67, 52.07)
    )
    assert tuple(v * factor for v in material.bounds) == pytest.approx(
        expected, abs=0.001 if kind == "gerber" else 1e-6
    )
    if kind == "macro":
        assert len(material.interiors) == 1
    encoded = json.loads(
        json.dumps(obj.to_dict(), default=to_dict), object_hook=dict2obj
    )
    path.unlink()
    restored = create(actual_kind, "restored")
    restored.from_dict(encoded)
    assert (
        restored.source_file.encode("latin1") == data
        and read_manufacturing_report(restored) == report
    )
    assert restored.manufacturing_source is not obj.manufacturing_source
    assert union_all(restored.solid_geometry).equals_exact(material, 1e-12)


@pytest.mark.parametrize("result", ["fail", "defective"])
def test_actual_gerber_parser_reported_failure_cannot_publish(
    tmp_path, host, monkeypatch, result
):
    from appObjects.GerberObject import GerberObject

    app, _create, published, _conversions = host
    original = GerberObject.parse_lines

    def parsed_then_failed(obj, lines):
        assert original(obj, lines) is None
        return result

    monkeypatch.setattr(GerberObject, "parse_lines", parsed_then_failed)
    path = tmp_path / "board-F_Cu.gbr"
    path.write_bytes(source("gerber", "MM"))
    review = review_manufacturing_files(
        inspect_manufacturing_files((str(path),)),
        (ManufacturingAssignment(0, "gerber", "F.Cu", "failed"),),
    )
    receipts = tuple(import_manufacturing_review(app, review))
    assert (
        len(receipts) == 1 and receipts[0].owner is None and result in receipts[0].error
    )
    assert not published and path.read_bytes() == source("gerber", "MM")


def test_four_desktop_sources_have_real_expected_roles_and_material(tmp_path, host):
    from smoke_manufacturing_import import _sources

    app, _create, published, _conversions = host
    rows = _sources(tmp_path)
    files = inspect_manufacturing_files(tuple(str(row[2]) for row in rows))
    assert all(not file.error for file in files)
    assert tuple(file.inspection.role_hint for file in files) == (
        "F.Cu",
        "B.Cu",
        "PTH",
        "Edge.Cuts",
    )
    assignments = tuple(
        ManufacturingAssignment(index, row[1], row[0], "actual " + row[0])
        for index, row in enumerate(rows)
    )
    review = review_manufacturing_files(files, assignments)
    receipts = tuple(import_manufacturing_review(app, review))
    assert len(receipts) == 4 and all(not receipt.error for receipt in receipts), (
        receipts
    )
    assert len(published) == 4
    for row, receipt in zip(rows, receipts):
        owner = receipt.owner
        assert union_all(owner.solid_geometry).bounds == pytest.approx(row[4], abs=1e-6)
        assert owner.source_file.encode("latin1") == row[3] == row[2].read_bytes()
        assert read_manufacturing_report(owner).role == row[0]
