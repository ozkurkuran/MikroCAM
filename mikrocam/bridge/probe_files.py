"""Offline bounded map persistence with atomic same-directory replacement."""
import os
from pathlib import Path
import tempfile

from mikrocam.core.probe_codec import MAX_MAP_BYTES, dumps_map, loads_map
from mikrocam.core.probe_map import ProbeMap


def save_probe_map(path: Path | str, value: ProbeMap) -> None:
    """Commit a complete JSON file atomically; failures preserve the prior file."""
    contents = dumps_map(value).encode('utf-8')
    destination = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=destination.parent,
                                         prefix='.probe-map-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_probe_map(path: Path | str) -> ProbeMap:
    """Load and validate at most 1MiB, without altering a file or controller."""
    with Path(path).open('rb') as stream:
        contents = stream.read(MAX_MAP_BYTES + 1)
    if len(contents) > MAX_MAP_BYTES:
        raise ValueError('Probe map file exceeds 1MiB')
    try:
        text = contents.decode('utf-8')
    except UnicodeError as error:
        raise ValueError('Probe map file requires strict UTF8') from error
    return loads_map(text)
