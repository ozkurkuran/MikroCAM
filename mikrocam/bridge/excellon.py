"""Shared atomic legacy Excellon construction from validated physical drill tools."""
from collections.abc import Callable
import re

from shapely.geometry import Point

from mikrocam.core.drill_groups import DrillTool, validate_drill_tools
from mikrocam.core.excellon_tools import ExcellonTool, validate_excellon_tools


def create_excellon_tools(app: object, tools: tuple[DrillTool, ...], name: str, *,
                          source_guard: Callable[[], None] | None = None) -> object:
    """Retain the drill-only API while sharing one slot-capable construction path."""
    validate_drill_tools(tools)
    operations = tuple(ExcellonTool(tool.diameter_mm, tool.centers_mm, ()) for tool in tools)
    return create_excellon_operations(app, operations, name, source_guard=source_guard)


def create_excellon_operations(app: object, tools: tuple[ExcellonTool, ...], name: str, *,
                               source_guard: Callable[[], None] | None = None) -> object:
    """Finish geometry and local source export before a factory publishes the object."""
    validate_excellon_tools(tools)
    if (type(name) is not str or not 1 <= len(name) <= 256 or name != name.strip()
            or not name.isprintable()):
        raise ValueError('Excellon name requires 1..256 trimmed printable characters')
    if source_guard is not None and not callable(source_guard):
        raise ValueError('Excellon source guard must be a no-argument callable')
    units = getattr(app, 'app_units', None)
    if type(units) is not str or units not in ('MM', 'IN'):
        raise ValueError('Drill creation requires explicit MM or IN host units')
    factor = 1. if units == 'MM' else 1. / 25.4
    initialized, failures = [], []

    def initialize(obj: object, app_obj: object) -> str | None:
        try:
            if source_guard is not None:
                source_guard()
            if getattr(obj, 'units', None) != units or getattr(app_obj, 'app_units', None) != units:
                raise ValueError('Factory object units must match the current host units')
            obj.tools = {index: {'tooldia': tool.diameter_mm * factor,
                                 'drills': [Point(x * factor, y * factor) for x, y in tool.drills_mm],
                                 'slots': [(Point(start[0] * factor, start[1] * factor),
                                            Point(end[0] * factor, end[1] * factor))
                                           for start, end in tool.slots_mm], 'solid_geometry': []}
                         for index, tool in enumerate(tools, 1)}
            if obj.create_geometry() == 'fail':
                raise ValueError('Excellon geometry creation failed')
            if not obj.solid_geometry or any(g.is_empty or not g.is_valid for g in obj.solid_geometry):
                raise ValueError('Excellon geometry is empty or invalid')
            source = app.f_handlers.export_excellon(name, None, local_use=obj, use_thread=False)
            if type(source) is not str or not source.strip() or source == 'fail':
                raise ValueError('Excellon source export failed')
            if re.search(r'(?m)^T\d+(?:F[\d.]+)?(?:S[\d.]+)?C0(?:\.0+)?\s*$', source):
                raise ValueError('Export precision rounds a tool diameter to zero; change export units or source tooling')
            if source_guard is not None:
                source_guard()
            obj.source_file = source
            initialized.append(obj)
            return None
        except Exception as error:
            failures.append(str(error))
            return 'fail'

    try:
        obj = app.app_obj.new_object('excellon', name, initialize)
    except Exception as error:
        raise ValueError(f'Excellon factory failed: {error}') from error
    if len(initialized) != 1 or obj is not initialized[0]:
        detail = failures[0] if failures else 'Excellon factory did not publish the initialized object'
        raise ValueError(f'Could not create drill object: {detail}')
    return obj
