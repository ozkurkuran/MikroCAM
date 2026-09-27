"""Report ownership cannot mutate source/material or leak a prior import's success."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from mikrocam.bridge.import_report import read_import_report, store_import_report
from mikrocam.bridge.svg_import import import_svg_bytes
from mikrocam.ui.svg_import import import_svg_geometry


SOURCE = (b'<svg width="10mm" height="20mm" viewBox="0 0 10 20">'
          b'<path d="M1 1L4 1L1 5"/></svg>')


def owner():
    return SimpleNamespace(source_file='original', solid_geometry=['untouched'],
                           obj_options={'parameter': 2}, tools={1: {'parameter': 3}},
                           import_report=None)


def app():
    messages = []
    return SimpleNamespace(log=SimpleNamespace(error=messages.append, warning=messages.append),
                           inform=SimpleNamespace(emit=messages.append)), messages


def test_store_only_changes_owning_report_and_read_does_not_reimport(monkeypatch):
    import mikrocam.bridge.svg_import as svg
    value = owner()
    before = deepcopy(vars(value))
    result = import_svg_bytes(SOURCE, 'first.svg', flip=False)
    store_import_report(value, result)
    monkeypatch.setattr(svg, 'import_svg_bytes', lambda *a, **kw: pytest.fail('unexpected reimport'))
    report = read_import_report(value)
    assert report.source_name == 'first.svg'
    assert report.quality.open_paths == 1 and report.quality.closed_paths == 0
    assert report.quality.bounds_mm == pytest.approx((1., 1., 4., 5.), abs=1e-6)
    assert value.import_report['schema_version'] == 1
    assert {k: v for k, v in vars(value).items() if k != 'import_report'} == {
        k: v for k, v in before.items() if k != 'import_report'}


def test_reports_are_independent_and_decoding_is_immutable():
    first, second = owner(), owner()
    store_import_report(first, import_svg_bytes(SOURCE, 'first.svg', flip=False))
    store_import_report(second, import_svg_bytes(SOURCE, 'second.svg', flip=True))
    report = read_import_report(first)
    second.import_report['source_name'] = 'edited.svg'
    assert read_import_report(first) == report
    assert read_import_report(second).coordinates.flipped
    with pytest.raises(AttributeError):
        report.source_name = 'changed'


def test_absent_old_record_is_unavailable_and_corrupt_new_record_is_explicit():
    assert read_import_report(SimpleNamespace()) is None
    assert read_import_report(owner()) is None
    value = owner()
    for payload in ({'schema_version': 999}, [], 'invalid', False):
        value.import_report = payload
        with pytest.raises(ValueError):
            read_import_report(value)


def test_builder_failure_leaves_previous_report_untouched():
    value = owner()
    value.import_report = {'previous': True}
    previous = value.import_report
    with pytest.raises(ValueError):
        store_import_report(value, None)
    assert value.import_report is previous


def test_adapter_success_attaches_exact_result_and_failure_preserves_previous(tmp_path):
    path = tmp_path / 'report.svg'
    path.write_bytes(SOURCE)
    value = owner()
    application, messages = app()
    shapes = import_svg_geometry(path, 'geometry', 'IN', True, application, report_owner=value)
    assert shapes and read_import_report(value).coordinates.flipped
    assert read_import_report(value).quality.bounds_mm == pytest.approx((1., 15., 4., 19.), abs=1e-6)
    previous = value.import_report
    path.write_bytes(b'<svg><invalid')
    assert import_svg_geometry(path, 'geometry', 'MM', False, application, report_owner=value) is None
    assert value.import_report is previous
    assert any('[ERROR_NOTCL]' in message for message in messages)


def test_invalid_host_units_do_not_publish_success_report(tmp_path):
    path = tmp_path / 'report.svg'
    path.write_bytes(SOURCE)
    value = owner()
    application, _ = app()
    assert import_svg_geometry(path, 'geometry', 'unknown', True, application, report_owner=value) is None
    assert value.import_report is None
