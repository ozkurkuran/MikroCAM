"""SVG drill review and atomic legacy Excellon creation at the host unit boundary."""
from pathlib import Path
import hashlib

from mikrocam.core.drill_groups import group_drill_selection
from mikrocam.core.svg_drills import DrillReview, detect_svg_drills
from mikrocam.core.svg_models import MAX_SVG_BYTES
from .svg_import import load_svg_file
from .excellon import create_excellon_tools


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
    return create_excellon_tools(app, tools, name)
