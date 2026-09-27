"""Each source keeps one normal factory publication with accurate failure outcomes."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import pytest
from shapely.geometry import box
from mikrocam.bridge.manufacturing_import import (inspect_manufacturing_files, review_manufacturing_files,
    import_manufacturing_review, read_manufacturing_report)
from mikrocam.core.manufacturing_models import ManufacturingAssignment
from test_manufacturing_files import sources, GERBER


def review_for(tmp_path):
    paths = sources(tmp_path)
    files = inspect_manufacturing_files(paths)
    assignments = (ManufacturingAssignment(0, 'gerber', 'F.Cu', 'top'),
                   ManufacturingAssignment(1, 'excellon', 'PTH', 'holes'))
    return review_manufacturing_files(files, assignments)


class Host:
    def __init__(self, units='MM', fail_index=None, mode=None):
        self.app_units, self.fail_index, self.mode = units, fail_index, mode
        self.options = {'feed':231, 'depth':-.1}
        self.app_obj = SimpleNamespace(new_object=self.factory)
        self.calls, self.published = [], []
        self.before = None

    def factory(self, kind, name, initialize, **kwargs):
        index = len(self.calls)
        self.calls.append((kind, name))
        host = self
        class Owner:
            def __init__(self):
                self.kind, self.units, self.obj_options = kind, 'MM', {'name':name}
                self.tools = {1: {'data':deepcopy(host.options), 'drills':[], 'slots':[], 'solid_geometry':[]}}
                self.solid_geometry = []
                self.source_file = ''
            def parse_lines(self, lines):
                self.lines = tuple(lines)
                self.solid_geometry = [box(1, 2, 3, 4)]
                self.tools[1]['solid_geometry'] = list(self.solid_geometry)
                if kind == 'excellon':
                    from shapely.geometry import Point
                    self.tools[1]['drills'] = [Point(2, 3)]
                if index == host.fail_index:
                    return host.mode
                return None
            def create_geometry(self):
                return 'fail' if host.mode == 'geometry-fail' and index == host.fail_index else None
        obj = Owner()
        if self.before:
            self.before(index, obj)
        if self.mode == 'exception' and index == self.fail_index:
            raise RuntimeError('factory failed')
        result = initialize(obj, self)
        if result == 'fail':
            return result
        if self.mode == 'different' and index == self.fail_index:
            return object()
        self.published.append(obj)
        return obj


def test_normal_sequential_sources_defaults_and_reports_preserved(tmp_path):
    review = review_for(tmp_path)
    app = Host()
    receipts = tuple(import_manufacturing_review(app, review))
    assert len(receipts) == 2 and all(not result.error for result in receipts)
    assert app.calls == [('gerber', 'top'), ('excellon', 'holes')]
    for receipt, source, role in zip(receipts, review.files, ('F.Cu', 'PTH')):
        assert receipt.owner in app.published
        assert receipt.owner.source_file.encode('latin1') == source.source_bytes == Path(source.path).read_bytes()
        assert receipt.owner.tools[1]['data'] == app.options == {'feed':231, 'depth':-.1}
        report = read_manufacturing_report(receipt.owner)
        assert report.role == role and report.units_origin == 'explicit'
    assert receipts[0].owner.lines[-1] == 'M02*'


@pytest.mark.parametrize('mode', ['fail', 'defective', 'unexpected', 'exception', 'different'])
def test_first_failure_stops_pending_rows_and_never_publishes_partial(mode, tmp_path):
    review = review_for(tmp_path)
    app = Host(fail_index=0, mode=mode)
    receipts = tuple(import_manufacturing_review(app, review))
    assert len(receipts) == 1 and receipts[0].source_index == 0 and receipts[0].owner is None
    assert receipts[0].error and not app.published and len(app.calls) == 1


@pytest.mark.parametrize('mode', ['fail', 'defective', 'geometry-fail'])
def test_later_failure_preserves_prior_success(tmp_path, mode):
    review = review_for(tmp_path)
    app = Host(fail_index=1, mode=mode)
    receipts = tuple(import_manufacturing_review(app, review))
    assert len(receipts) == 2 and receipts[0].owner is app.published[0]
    assert receipts[1].error and len(app.published) == 1


def test_all_selected_sources_checked_before_any_publication(tmp_path):
    review = review_for(tmp_path)
    Path(review.files[1].path).unlink()
    app = Host()
    with pytest.raises(ValueError, match='[Ii]nspect|[Rr]eview'):
        tuple(import_manufacturing_review(app, review))
    assert not app.calls


def test_source_changed_inside_factory_rejected(tmp_path):
    review = review_for(tmp_path)
    app = Host()
    app.before = lambda index, obj: Path(review.files[index].path).write_bytes(b'changed')
    receipts = tuple(import_manufacturing_review(app, review))
    assert len(receipts) == 1 and receipts[0].error and not app.published


def test_old_or_invalid_stored_report():
    assert read_manufacturing_report(SimpleNamespace()) is None
    assert read_manufacturing_report(SimpleNamespace(manufacturing_source=None)) is None
    with pytest.raises(ValueError):
        read_manufacturing_report(SimpleNamespace(manufacturing_source={}))


def test_guard_catches_source_change_after_parser_assignments(tmp_path):
    review = review_for(tmp_path)
    app = Host()
    def before(index, obj):
        original = obj.parse_lines
        def changed(lines):
            result = original(lines)
            Path(review.files[index].path).write_bytes(b'changed after parse')
            return result
        obj.parse_lines = changed
    app.before = before
    receipts = tuple(import_manufacturing_review(app, review))
    assert receipts[0].error and not app.published


@pytest.mark.parametrize('material', [[], [None], [box(0, 0, 0, 0)], [[[[None]]]]])
def test_empty_or_invalid_parser_material_is_not_published(tmp_path, material):
    review = review_for(tmp_path)
    app = Host()
    def before(index, obj):
        def parse(lines):
            obj.solid_geometry = material
            return None
        obj.parse_lines = parse
    app.before = before
    receipts = tuple(import_manufacturing_review(app, review))
    assert receipts[0].error and not app.published


def test_current_host_unit_change_inside_parse_is_rejected(tmp_path):
    review = review_for(tmp_path)
    app = Host()
    def before(index, obj):
        original = obj.parse_lines
        def changed(lines):
            result = original(lines)
            app.app_units = 'IN'
            return result
        obj.parse_lines = changed
    app.before = before
    receipts = tuple(import_manufacturing_review(app, review))
    assert receipts[0].error and not app.published
