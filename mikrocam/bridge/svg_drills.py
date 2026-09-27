"""SVG drill review and atomic legacy Excellon creation at the host unit boundary."""
from pathlib import Path
import hashlib

from shapely.geometry import Point

from mikrocam.core.drill_groups import group_drill_selection
from mikrocam.core.svg_drills import DrillReview, detect_svg_drills
from mikrocam.core.svg_models import MAX_SVG_BYTES
from .svg_import import load_svg_file


def load_drill_review(path: Path | str, *, flip: bool = True) -> DrillReview:
    """Load through the established physical importer without retaining raw source data."""
    return detect_svg_drills(load_svg_file(path, flip=flip))


def verify_drill_source(path: Path | str, review: DrillReview) -> None:
    """Reject changed source bytes without reparsing artwork or touching host objects."""
    if type(review) is not DrillReview:
        raise ValueError('Source verification requires an exact DrillReview')
    with Path(path).open('rb') as stream:
        source = stream.read(MAX_SVG_BYTES + 1)
    if len(source) > MAX_SVG_BYTES:
        raise ValueError('SVG source exceeds byte size limit')
    if hashlib.sha256(source).hexdigest() != review.source_sha256:
        raise ValueError('SVG source changed after review; analyse it again')


def create_drill_object(app: object, review: DrillReview, indices: tuple[int, ...],
                        name: str) -> object:
    """Create only selected evidence, completing geometry and source before publication."""
    tools = group_drill_selection(review, indices)
    if (type(name) is not str or not 1 <= len(name) <= 256 or name != name.strip()
            or not name.isprintable()):
        raise ValueError('Excellon name requires 1..256 trimmed printable characters')
    units = getattr(app, 'app_units', None)
    if units not in ('MM', 'IN'):
        raise ValueError('SVG drill creation requires explicit MM or IN host units')
    factor = 1. if units == 'MM' else 1. / 25.4
    initialized = []
    failures = []

    def initialize(obj: object, app_obj: object) -> str | None:
        try:
            if getattr(obj, 'units', None) != units or getattr(app_obj, 'app_units', None) != units:
                raise ValueError('Factory object units must match the current host units')
            # Export uses host units, so convert before geometry/export, never after initialization.
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
    if not initialized or obj is not initialized[0]:
        detail = failures[0] if failures else 'Excellon factory did not publish the initialized object'
        raise ValueError(f'Could not create SVG drill object: {detail}')
    return obj
