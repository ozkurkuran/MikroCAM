"""Actual Geometry constructors, DXF exporter/parser and historical PDF serialization."""

from copy import deepcopy
import io
import json
import logging
from types import SimpleNamespace
import pytest
from shapely import union_all
from mikrocam.bridge.pdf_import import (
    load_pdf_review,
    create_pdf_geometry,
    read_pdf_report,
)
from mikrocam.core.pdf_models import PdfOptions


def authored_pdf():
    from reportlab.pdfgen.canvas import Canvas

    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=(288, 144), pageCompression=1, invariant=1)
    canvas.rect(1, 1, 4, 4, stroke=0, fill=1)
    canvas.showPage()
    canvas.rect(72, 36, 72, 36, stroke=0, fill=1)
    canvas.showPage()
    canvas.save()
    return stream.getvalue()


@pytest.fixture
def host(qtbot, monkeypatch):
    from appObjects import AppObjectTemplate
    from appObjects.GeometryObject import GeometryObject
    from defaults import AppDefaults

    monkeypatch.setattr(
        AppObjectTemplate, "ShapeCollection", lambda **kwargs: SimpleNamespace()
    )
    options = deepcopy(AppDefaults.factory_defaults)
    options.update(tools_mill_feedrate=321.25, tools_mill_cutz=-0.321)
    app = SimpleNamespace(
        options=options,
        defaults=options,
        app_units="MM",
        decimals=4,
        use_3d_engine=True,
        call_source="app",
        pool=None,
        log=logging.getLogger("pdf-roundtrip"),
        plotcanvas=SimpleNamespace(
            view=SimpleNamespace(scene=None),
            new_shape_group=lambda: SimpleNamespace(),
            new_shape_collection=lambda **kwargs: SimpleNamespace(),
        ),
    )
    instances = []

    def create(name):
        obj = GeometryObject(name, app)
        obj.units = app.app_units
        obj.tools = {
            1: {
                "tooldia": 0.2,
                "data": {"tools_mill_feedrate": 321.25, "tools_mill_cutz": -0.321},
                "solid_geometry": [],
            }
        }
        instances.append(obj)
        return obj

    def factory(kind, name, initialize, **kwargs):
        assert kind == "geometry"
        obj = create(name)
        return "fail" if initialize(obj, app) == "fail" else obj

    app.app_obj = SimpleNamespace(new_object=factory)
    yield app, create
    for obj in instances:
        obj.deleteLater()


@pytest.mark.parametrize("units", ["MM", "IN"])
def test_real_geometry_dxf_reparse_and_latin1_report_roundtrip(tmp_path, host, units):
    import ezdxf
    from appParsers.ParseDXF import getdxfgeo
    from camlib import to_dict, dict2obj

    app, create = host
    app.app_units = units
    app.options["units"] = units
    original_options = deepcopy(app.options)
    data = authored_pdf()
    path = tmp_path / "authored.pdf"
    path.write_bytes(data)
    review = load_pdf_review(
        path, PdfOptions(1, crop_mm=(12.7, 0, 76.2, 50.8), flip=True)
    )
    obj = create_pdf_geometry(app, path, review, "PDF vectors")
    factor = 1 if units == "MM" else 25.4
    material = union_all(obj.solid_geometry)
    assert material.bounds == pytest.approx(
        tuple(v / factor for v in (12.7, 25.4, 38.1, 38.1)), abs=1e-6
    )
    assert material.area * factor**2 == pytest.approx(322.58, abs=1e-6)
    assert obj.source_file.encode("latin1") == data and path.read_bytes() == data
    assert obj.tools[1]["data"] == {
        "tools_mill_feedrate": 321.25,
        "tools_mill_cutz": -0.321,
    }
    assert (
        obj.tools[1]["solid_geometry"] == obj.solid_geometry
        and app.options == original_options
    )
    dxf = obj.export_dxf()
    stream = io.StringIO()
    dxf.write(stream)
    parsed = ezdxf.read(io.StringIO(stream.getvalue()))
    contours = union_all(getdxfgeo(parsed))
    assert contours.bounds == pytest.approx(material.bounds, abs=1e-6)
    assert contours.length * factor == pytest.approx(76.2, abs=1e-6)
    payload = json.loads(
        json.dumps(obj.to_dict(), default=to_dict), object_hook=dict2obj
    )
    path.unlink()
    restored = create("restored")
    restored.from_dict(payload)
    assert read_pdf_report(restored) == review.result.report
    assert restored.source_file.encode("latin1") == data
    assert union_all(restored.solid_geometry).equals_exact(material, 1e-12)
    assert (
        restored.pdf_import is not obj.pdf_import
        and restored.tools["1"]["data"] == obj.tools[1]["data"]
    )
    assert app.options == original_options
