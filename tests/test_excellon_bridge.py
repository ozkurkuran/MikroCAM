"""Shared creation validates tools and rechecks source before publication."""
from copy import deepcopy

import pytest

from mikrocam.bridge.excellon import create_excellon_tools
from mikrocam.core.drill_groups import DrillTool
from test_svg_drill_bridge import Host


TOOLS = (DrillTool(5.08, ((76.2, 25.4),)), DrillTool(2.54, ((25.4, 50.8),)))


@pytest.mark.parametrize(('units', 'factor'), [('MM', 1.), ('IN', 1. / 25.4)])
def test_shared_factory_preserves_tools_order_defaults_and_converts_once(units, factor):
    app = Host(units)
    defaults, options = deepcopy(app.defaults), deepcopy(app.options)
    obj = create_excellon_tools(app, TOOLS, 'shared-holes')
    assert app.published == [obj]
    assert obj.tools[1]['tooldia'] == pytest.approx(5.08 * factor)
    assert obj.tools[1]['drills'][0].coords[0] == pytest.approx((76.2 * factor, 25.4 * factor))
    assert obj.tools[2]['tooldia'] == pytest.approx(2.54 * factor)
    assert all(tool['data'] == defaults for tool in obj.tools.values())
    assert app.defaults == defaults and app.options == options and obj.source_file.startswith('M48')


def test_source_guard_runs_before_any_destination_write_and_after_local_export():
    app = Host()
    calls = []
    def guard():
        obj = app.initialized
        calls.append(('guard', len(calls)))
        if len(calls) == 1:
            assert obj.tools == {'old': {}} and obj.source_file == ''
            assert app.calls == [('factory', 'excellon', 'guarded')]
        else:
            assert obj.solid_geometry and obj.source_file == ''
            assert app.calls[-1] == ('export', 'MM')
        assert not app.published
    result = create_excellon_tools(app, TOOLS, 'guarded', source_guard=guard)
    assert len(calls) == 2 and app.published == [result]


@pytest.mark.parametrize('reject_at', [1, 2])
def test_source_change_at_either_guard_prevents_publication(reject_at):
    app = Host()
    calls = []
    def guard():
        calls.append(True)
        if len(calls) == reject_at:
            raise ValueError('Source changed; analyse again')
    with pytest.raises(ValueError, match='Source changed'):
        create_excellon_tools(app, TOOLS, 'guarded', source_guard=guard)
    assert not app.published and app.initialized.source_file == ''
    if reject_at == 1:
        assert app.initialized.tools == {'old': {}}
        assert app.calls == [('factory', 'excellon', 'guarded')]
    else:
        assert app.calls[-1] == ('export', 'MM')


@pytest.mark.parametrize('tools', [(), [], (object(),),
                                 (DrillTool(2, ((0, 0),)), DrillTool(1, ((0, 0),)))])
def test_invalid_tools_rejected_before_any_factory_io(tools):
    app = Host()
    with pytest.raises(ValueError):
        create_excellon_tools(app, tools, 'invalid')
    assert not app.calls


def test_noncallable_guard_rejected_before_factory():
    app = Host()
    with pytest.raises(ValueError):
        create_excellon_tools(app, TOOLS, 'invalid', source_guard=True)
    assert not app.calls


@pytest.mark.parametrize('failure', ['factory', 'units', 'geometry', 'geometry-exception',
                                     'export', 'empty-export', 'none-export', 'export-exception'])
def test_shared_factory_failure_never_publishes(failure):
    app = Host(failure=failure)
    with pytest.raises(ValueError):
        create_excellon_tools(app, TOOLS, 'failed')
    assert not app.published


def test_factory_must_return_exact_initialized_object():
    app = Host()
    original = app.new_object
    def wrong_return(*args):
        original(*args)
        return object()
    app.app_obj.new_object = wrong_return
    with pytest.raises(ValueError, match='initialized object'):
        create_excellon_tools(app, TOOLS, 'wrong-return')
