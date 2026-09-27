"""Read-only acquisition of complete G-code as immutable core source snapshots."""
from collections.abc import Mapping
from os import PathLike
from pathlib import Path

from mikrocam.core.gcode_models import MAX_SOURCE_BYTES, SourceSnapshot


def snapshot_cncjob(obj: object) -> SourceSnapshot:
    """Copy complete CNCJob source; never inspect body G-code or invoke export."""
    if getattr(obj, 'kind', None) != 'cncjob':
        raise ValueError('Select a CNC job with complete source text')
    text = getattr(obj, 'source_file', None)
    options = getattr(obj, 'obj_options', None)
    if not isinstance(text, str) or not text:
        raise ValueError('CNC job has no complete source text')
    if not isinstance(options, Mapping):
        raise ValueError('CNC job has no source name')
    return SourceSnapshot(options.get('name'), text)


def load_gcode_file(path: str | PathLike[str]) -> SourceSnapshot:
    """Read at most the source limit plus one byte; retain decoded text exactly."""
    source_path = Path(path)
    with source_path.open('rb') as handle:
        data = handle.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError('G-code file exceeds the source byte limit')
    try:
        text = data.decode('utf-8-sig', errors='strict')
    except UnicodeDecodeError as error:
        raise ValueError('G-code file must use UTF-8 encoding') from error
    return SourceSnapshot(source_path.name, text)
