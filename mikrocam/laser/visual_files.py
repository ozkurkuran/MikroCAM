"""File-only atomic publication with cancellation; no hardware communication."""
from collections.abc import Callable
import os
from pathlib import Path
import tempfile
from mikrocam.core.laser_paths import check_cancelled


def atomic_write(destination: Path, data: bytes, cancelled: Callable[[], bool] | None = None) -> None:
    check_cancelled(cancelled)
    destination = Path(destination)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.' + destination.name + '.',
                                         suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            for start in range(0, len(data), 1024 * 1024):
                check_cancelled(cancelled)
                stream.write(data[start:start + 1024 * 1024])
            stream.flush()
            os.fsync(stream.fileno())
        check_cancelled(cancelled)
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
