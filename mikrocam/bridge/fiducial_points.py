"""Read-only fiducial design candidates (mm) from Excellon drills and Gerber flashes."""
import math

from shapely.geometry import Point

from mikrocam.core.placement import Point2D


MAX_CANDIDATES = 1000


def _factor(obj: object) -> float:
    units = getattr(obj, 'units', None)
    if units not in ('MM', 'IN'):
        raise ValueError('Object requires explicit MM or IN units')
    return 1. if units == 'MM' else 25.4


def _xy(point: Point, factor: float) -> Point2D | None:
    if type(point) is not Point or point.is_empty:
        return None
    x, y = point.x * factor, point.y * factor
    return (x, y) if math.isfinite(x) and math.isfinite(y) else None


def _sources(obj: object) -> list[tuple[str, object]]:
    kind = getattr(obj, 'kind', None)
    tools = getattr(obj, 'tools', None)
    if kind not in ('excellon', 'gerber'):
        raise ValueError('Select an Excellon or Gerber object')
    if type(tools) is not dict:
        raise ValueError('Object has no readable tools')
    result = []
    for key, tool in tools.items():
        if type(tool) is not dict:
            continue
        if kind == 'excellon':
            result += [(f'T{key} drill', point) for point in tool.get('drills') or ()]
        else:
            result += [(f'D{key} flash', item.get('follow')) for item in tool.get('geometry') or ()
                       if type(item) is dict]
    return result


def design_points(obj: object) -> tuple[tuple[str, Point2D], ...]:
    """Return labelled candidate centres without modifying the host object."""
    factor = _factor(obj) if obj is not None else None
    if factor is None:
        raise ValueError('Select an Excellon or Gerber object')
    result = []
    for label, point in _sources(obj):
        xy = _xy(point, factor)
        if xy is not None:
            result.append((f'{label} {len(result) + 1}: {xy[0]:.4f}, {xy[1]:.4f}', xy))
        if len(result) >= MAX_CANDIDATES:
            break
    if not result:
        raise ValueError('Object has no drill or flash centres')
    return tuple(result)
