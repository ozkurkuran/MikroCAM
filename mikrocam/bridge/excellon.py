"""Shared atomic legacy Excellon construction from validated physical drill tools."""
from collections.abc import Callable

from shapely.geometry import Point

from mikrocam.core.drill_groups import DrillTool, validate_drill_tools


def create_excellon_tools(app: object, tools: tuple[DrillTool, ...], name: str, *,
                          source_guard: Callable[[], None] | None = None) -> object:
    """Finish geometry and local source export before a factory publishes the object."""
    validate_drill_tools(tools)
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
                                 'drills': [Point(x * factor, y * factor) for x, y in tool.centers_mm],
                                 'slots': [], 'solid_geometry': []}
                         for index, tool in enumerate(tools, 1)}
            if obj.create_geometry() == 'fail':
                raise ValueError('Excellon geometry creation failed')
            if not obj.solid_geometry or any(g.is_empty or not g.is_valid for g in obj.solid_geometry):
                raise ValueError('Excellon geometry is empty or invalid')
            source = app.f_handlers.export_excellon(name, None, local_use=obj, use_thread=False)
            if type(source) is not str or not source.strip() or source == 'fail':
                raise ValueError('Excellon source export failed')
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
