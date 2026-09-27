"""Fresh source authority and atomic host-unit Geometry construction."""
from copy import deepcopy
from dataclasses import replace
from io import BytesIO
from types import SimpleNamespace
import pytest
from reportlab.pdfgen.canvas import Canvas
from shapely import affinity
from mikrocam.bridge.pdf_import import (inspect_pdf_file, load_pdf_review, create_pdf_geometry,
                                        read_pdf_report)
from mikrocam.core.pdf_models import PdfOptions, PdfGeometryResult, PdfImportReview, geometry_sha256


def source_file(tmp_path):
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=(144, 72), pageCompression=1)
    canvas.rect(10, 20, 30, 10, stroke=0, fill=1)
    canvas.showPage()
    canvas.rect(40, 30, 20, 10, stroke=0, fill=1)
    canvas.save()
    path = tmp_path / 'pages.pdf'
    path.write_bytes(stream.getvalue())
    return path


class Host:
    def __init__(self, units='MM', mode=None, before=None):
        self.app_units, self.mode, self.before = units, mode, before
        self.options = {'feed': 231, 'depth': -0.1}
        self.app_obj = SimpleNamespace(new_object=self.factory)
        self.published = []
        self.calls = 0

    def factory(self, kind, name, initialize):
        self.calls += 1
        assert kind == 'geometry'
        obj = SimpleNamespace(units=self.app_units, tools={1: {'data':deepcopy(self.options),
            'tooldia':.2, 'solid_geometry':[]}}, obj_options={'name':name}, solid_geometry=[])
        if self.before:
            self.before(obj)
        if self.mode == 'exception':
            raise RuntimeError('factory failure')
        if initialize(obj, self) == 'fail':
            return 'fail'
        if self.mode == 'different':
            return object()
        self.published.append(obj)
        return obj


@pytest.mark.parametrize('units', ['MM', 'IN'])
def test_review_create_source_and_normal_defaults_preserved(tmp_path, units):
    path = source_file(tmp_path)
    original = path.read_bytes()
    facts = inspect_pdf_file(path)
    assert len(facts.pages) == 2
    review = load_pdf_review(path, PdfOptions(1))
    app = Host(units)
    obj = create_pdf_geometry(app, path, review, 'page two')
    factor = 1 if units == 'MM' else 1 / 25.4
    assert obj.solid_geometry[0].bounds == pytest.approx(tuple(v * factor for v in review.result.report.bounds_mm))
    assert obj.source_file.encode('latin1') == path.read_bytes() == original
    assert obj.tools[1]['data'] == app.options == {'feed':231, 'depth':-.1}
    assert obj.tools[1]['solid_geometry'] == obj.solid_geometry
    assert not obj.multigeo and read_pdf_report(obj) == review.result.report


@pytest.mark.parametrize('change', ['before', 'initializer', 'deleted', 'renamed'])
def test_changed_source_fails_without_publication(tmp_path, change):
    path = source_file(tmp_path)
    review = load_pdf_review(path, PdfOptions(0))
    app = Host()
    if change == 'initializer':
        app.before = lambda obj: path.write_bytes(path.read_bytes() + b'changed')
    elif change == 'deleted':
        path.unlink()
    elif change == 'renamed':
        new = path.with_name('renamed.pdf')
        path.rename(new)
        path = new
    else:
        path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='[Aa]nalyse again'):
        create_pdf_geometry(app, path, review, 'output')
    assert not app.published


def test_forged_geometry_with_same_source_identity_is_not_trusted(tmp_path):
    path = source_file(tmp_path)
    review = load_pdf_review(path, PdfOptions(0))
    geometry = tuple(affinity.translate(g, 1, 1) for g in review.result.geometry_mm)
    bounds = tuple(v + 1 for v in review.result.report.bounds_mm)
    report = replace(review.result.report, bounds_mm=bounds, geometry_sha256=geometry_sha256(geometry))
    forged = PdfImportReview(review.source_bytes, PdfGeometryResult(report, geometry))
    app = Host()
    with pytest.raises(ValueError, match='[Aa]nalyse again'):
        create_pdf_geometry(app, path, forged, 'forged')
    assert not app.published and app.calls == 0


@pytest.mark.parametrize('name', ['', ' bad', 'bad\n', 'x'*257, '\ud800'])
def test_bad_name_before_factory(tmp_path, name):
    path = source_file(tmp_path)
    review = load_pdf_review(path, PdfOptions(0))
    app = Host()
    with pytest.raises(ValueError):
        create_pdf_geometry(app, path, review, name)
    assert app.calls == 0


@pytest.mark.parametrize('mode', ['exception', 'different', 'wrong-units', 'bad-tools'])
def test_factory_failure_never_reports_success(tmp_path, mode):
    path = source_file(tmp_path)
    review = load_pdf_review(path, PdfOptions(0))
    app = Host(mode=mode)
    if mode == 'wrong-units':
        app.before = lambda obj: setattr(obj, 'units', 'IN')
    if mode == 'bad-tools':
        app.before = lambda obj: setattr(obj, 'tools', {'bad':None})
    with pytest.raises(ValueError):
        create_pdf_geometry(app, path, review, 'failed')
    assert not app.published


def test_optional_stored_report_is_strict_without_file_io():
    assert read_pdf_report(SimpleNamespace()) is None
    assert read_pdf_report(SimpleNamespace(pdf_import=None)) is None
    with pytest.raises(ValueError):
        read_pdf_report(SimpleNamespace(pdf_import={}))


def test_source_mutation_after_writes_caught_by_second_guard(tmp_path):
    path = source_file(tmp_path)
    review = load_pdf_review(path, PdfOptions(0))
    app = Host()
    class MutatingObject:
        units = 'MM'
        tools = {}
        @property
        def pdf_import(self):
            return None
        @pdf_import.setter
        def pdf_import(self, value):
            path.write_bytes(path.read_bytes() + b'changed during initialization')
    def factory(kind, name, initialize):
        obj = MutatingObject()
        result = initialize(obj, app)
        assert result == 'fail'
        return result
    app.app_obj.new_object = factory
    with pytest.raises(ValueError, match='[Aa]nalyse again'):
        create_pdf_geometry(app, path, review, 'changed')
    assert not app.published
