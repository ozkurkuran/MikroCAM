"""Independent bridge grammar, source-coordinate and pre-allocation regressions."""
import pytest
from mikrocam.bridge.svg_paths import element_paths
from mikrocam.bridge.svg_import import import_svg_bytes
from mikrocam.core.svg_models import SvgElement, SvgPaint

def paths(text, tolerance=0.005):
    return element_paths(SvgElement('path', 'path', (('d', text),), (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), SvgPaint()), tolerance)

@pytest.mark.parametrize('compact,expanded', [('M0 0A5 5 0 0110 0', 'M0 0 A5 5 0 0 1 10 0'), ('M0 0a5 5 0 10-10-0', 'M0 0 a5 5 0 1 0 -10 0'), ('M.5.5L1.5-.5', 'M.5 .5 L1.5 -.5'), ('m10 10 2 3 4 5h-1v2', 'M10 10 L12 13 L16 18 L15 18 L15 20'), ('M0 0C1 2 3 2 4 0S7-2 8 0', 'M0 0C1 2 3 2 4 0C5-2 7-2 8 0'), ('M0 0Q2 4 4 0T8 0', 'M0 0Q2 4 4 0Q6-4 8 0'), ('M0 0q2 4 4 0t4 0', 'M0 0Q2 4 4 0Q6-4 8 0')])
def test_compact_relative_and_smooth_commands_match_explicit_local_geometry(compact, expanded):
    assert paths(compact) == paths(expanded)

def test_multiple_move_close_preserve_disconnected_topology_and_relative_origin():
    result = paths('M0 0L2 0L2 2Z m10 0 l1 0 0 1z M30 4l2 0')
    assert len(result) == 3
    assert tuple((path.closed for path in result)) == (True, True, False)
    assert result[0].points == ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 0.0))
    assert result[1].points == ((10.0, 0.0), (11.0, 0.0), (11.0, 1.0), (10.0, 0.0))
    assert result[2].points == ((30.0, 4.0), (32.0, 4.0))

def test_zero_radius_arc_is_line_and_same_endpoint_arc_emits_no_extra_vertices():
    assert paths('M0 0A0 3 20 0 1 2 3')[0].points == ((0.0, 0.0), (2.0, 3.0))
    assert paths('M0 0L1 0A2 2 0 0 1 1 0')[0].points == ((0.0, 0.0), (1.0, 0.0))

@pytest.mark.parametrize('text', ['L0 0', 'M0', 'M0 0L1', 'M0 0C1 2 3 4 5', 'M0 0A1 1 0 001', 'M0 0A1 1 0 0.0 1 2 2', 'M0 0A1 1 0 2 1 2 2', 'M0 0A-1 1 0 0 1 2 2', 'M0 0,,L1 1', 'M0 0,', 'M0 0Z,', 'M0 0L1 1;', 'M0 0L1 1#comment', 'M0 0L1 1\x00', 'M0 0L1.2.3.4', 'M0 0L1e 1', 'M0 0L' + '1' * 65 + ' 1'])
def test_malformed_path_never_reaches_pinned_parser(text, monkeypatch):
    import mikrocam.bridge.svg_paths as bridge

    def unexpected_parser(_):
        pytest.fail('Invalid syntax reached external path parser')
    monkeypatch.setattr(bridge, 'parse_path', unexpected_parser)
    with pytest.raises(ValueError):
        paths(text)

@pytest.mark.parametrize('text', ['M999999999 0l2 0', 'M0 0Q-999999999 0 1 0T2 0'])
def test_relative_endpoint_or_reflected_control_overflow_rejects(text):
    with pytest.raises(ValueError):
        paths(text)

def test_syntax_budget_is_checked_before_external_parser_allocation(monkeypatch):
    import mikrocam.bridge.svg_paths as bridge
    monkeypatch.setattr(bridge, 'MAX_ELEMENT_POINTS', 3)
    assert len(paths('M0 0L1 1L2 2')[0].points) == 3
    monkeypatch.setattr(bridge, 'parse_path', lambda _: pytest.fail('Over-budget syntax reached parser'))
    with pytest.raises(ValueError, match='budget'):
        paths('M0 0L1 1L2 2L3 3')

def test_flattened_point_budget_is_global_across_disconnected_subpaths(monkeypatch):
    import mikrocam.bridge.svg_paths as bridge
    monkeypatch.setattr(bridge, 'MAX_ELEMENT_POINTS', 5)
    assert len(paths('M0 0Q1 4 2 0', tolerance=0.2)[0].points) <= 5
    with pytest.raises(ValueError, match='budget'):
        paths('M0 0Q1 4 2 0 M3 0L5 0', tolerance=0.2)

def test_failure_after_valid_element_has_no_partial_import_result_or_source_mutation():
    source = b'<svg width="10mm" height="10mm" viewBox="0 0 10 10"><rect width="2" height="2"/><path d="M0 0L1"/></svg>'
    before = bytes(source)
    with pytest.raises(ValueError):
        import_svg_bytes(source, 'atomic.svg', flip=False)
    assert source == before
