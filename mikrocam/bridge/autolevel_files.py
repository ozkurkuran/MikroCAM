"""Atomic separate compensated G-code export; never modifies a source object or transport."""
import os
from pathlib import Path
import tempfile
from mikrocam.core.autolevel import AutoLevelResult


def save_autolevel_gcode(path: Path | str, result: AutoLevelResult, *,
                         protected_paths: tuple[Path | str,...]=()) -> None:
    if type(result) is not AutoLevelResult:
        raise ValueError('Export requires an exact reviewed auto-level result')
    destination=Path(path);temporary=None
    resolved=destination.resolve()
    for original in protected_paths:
        source=Path(original)
        if resolved==source.resolve() or (destination.exists() and source.exists()
                                         and os.path.samefile(destination,source)):
            raise ValueError('Compensated output cannot overwrite an input source or map file')
    contents=result.prepared_job.source.text.encode('ascii')
    try:
        with tempfile.NamedTemporaryFile(mode='wb',dir=destination.parent,prefix='.autolevel-',
                                         suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            stream.write(contents);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,destination)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
