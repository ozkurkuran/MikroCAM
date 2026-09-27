"""Review authoritative host Geometry and guard it through Excellon publication."""
from mikrocam.core.geometry_drill_models import GeometryDrillReview
from mikrocam.core.geometry_drills import group_geometry_selection, review_geometry_sources

from .excellon import create_excellon_tools


def _tool_label(key: object) -> str:
    if type(key) is int and abs(key) <= 10**18:
        return f'tool:int:{key}'
    if type(key) is str:
        try:
            if key and len(key.encode('utf-8')) <= 240:
                return f'tool:str:{key}'
        except UnicodeError:
            pass
    raise ValueError('Geometry tool keys require bounded integer or nonempty text identifiers')


def load_geometry_review(owner: object) -> GeometryDrillReview:
    """Use the same single/per-tool geometry authority as the Geometry renderer."""
    if getattr(owner, 'kind', None) != 'geometry':
        raise ValueError('Select a Geometry object')
    options = getattr(owner, 'obj_options', None)
    name = options.get('name') if isinstance(options, dict) else None
    if type(name) is not str or not name or name != name.strip():
        raise ValueError('Geometry requires an explicit trimmed source name')
    mode = getattr(owner, 'multigeo', None)
    if type(mode) is not bool:
        raise ValueError('Geometry mode must be explicitly single or multi-tool')
    if mode:
        tools = getattr(owner, 'tools', None)
        if type(tools) is not dict or not 1 <= len(tools) <= 10000:
            raise ValueError('Multi-tool Geometry requires bounded per-tool geometry')
        sources = []
        for key, tool in tools.items():
            label = _tool_label(key)
            if type(tool) is not dict or 'solid_geometry' not in tool:
                raise ValueError('Each Geometry tool must contain its authoritative geometry')
            sources.append((label, tool['solid_geometry']))
        sources = tuple(sorted(sources, key=lambda pair: pair[0]))
    else:
        sources = (('geometry', getattr(owner, 'solid_geometry', None)),)
    return review_geometry_sources(sources, name, getattr(owner, 'units', None))


def verify_geometry_review(app: object, owner: object, review: GeometryDrillReview) -> None:
    """Reject removed, replaced, renamed or edited sources before publication."""
    try:
        if type(review) is not GeometryDrillReview or app.collection.get_by_name(review.source_name) is not owner:
            raise ValueError('Source identity changed')
        current = load_geometry_review(owner)
        if current != review:
            raise ValueError('Source content or reviewed measurements changed')
    except Exception as exc:
        raise ValueError('Geometry source changed or is unavailable. Analyse again.') from exc


def create_geometry_drills(app: object, owner: object, review: GeometryDrillReview,
                           indices: tuple[int, ...], name: str) -> object:
    """Create the selected physical drills while retaining and rechecking their source."""
    tools = group_geometry_selection(review, indices)
    return create_excellon_tools(app, tools, name,
                                 source_guard=lambda: verify_geometry_review(app, owner, review))
