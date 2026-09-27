"""Translate bounded SVG import results into the legacy host's notice channel."""
import builtins
import gettext
from html import escape
from pathlib import Path
from typing import Any

from shapely.geometry.base import BaseGeometry


_ = getattr(builtins, '_', gettext.gettext)


def import_svg_geometry(filename: str | Path, object_type: str | None, units: str,
                        flip: bool, app: Any) -> list[BaseGeometry] | None:
    """Return complete host-unit geometry, or report failure before host mutation."""
    from mikrocam.bridge.svg_import import host_geometry, load_svg_file

    name = Path(filename).name[:256]
    try:
        result = load_svg_file(filename, object_type='geometry' if object_type is None else object_type,
                               flip=flip)
        geometries = host_geometry(result, units)
    except (OSError, ValueError, TypeError, UnicodeError) as error:
        message = _('SVG import failed: {source}: {reason}').format(source=name, reason=str(error)[:512])
        app.log.error(message)
        app.inform.emit('[ERROR_NOTCL] ' + escape(message))
        return None
    for notice in result.notices:
        message = _('SVG import notice: {source}: {reason}').format(source=name, reason=notice.message)
        app.log.warning(message)
        app.inform.emit('[WARNING_NOTCL] ' + escape(message))
    return geometries
