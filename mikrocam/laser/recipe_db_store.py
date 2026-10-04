"""Recipe-database file store: atomic replacement guarded by the loaded revision."""
from hashlib import sha256
import os
from pathlib import Path
import tempfile
import uuid

from mikrocam.core.laser_recipe_db import LaserRecipeDatabase
from mikrocam.core.laser_recipe_db_json import MAX_DATABASE_BYTES, database_from_json, database_to_json


class StaleDatabaseError(ValueError):
    """The file changed after loading; saving would discard another writer's data."""


def new_id() -> str:
    """A random catalog identifier; the core only validates identifiers."""
    return uuid.uuid4().hex


def write_text_atomic(path: str | Path, text: str) -> None:
    """Replace a UTF-8 LF text file through a flushed same-directory temporary file."""
    target = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', delete=False,
                                         dir=target.parent, prefix=f'.{target.name}.', suffix='.tmp') as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read(path: Path) -> bytes | None:
    try:
        with path.open('rb') as stream:
            data = stream.read(MAX_DATABASE_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(data) > MAX_DATABASE_BYTES:
        raise ValueError(f'recipe database exceeds the {MAX_DATABASE_BYTES} byte size limit')
    return data


def _revision(data: bytes | None) -> str | None:
    return None if data is None else sha256(data).hexdigest()


def load_database(path: str | Path) -> tuple[LaserRecipeDatabase, str | None]:
    """Read the database and its revision; a missing file is an empty, uncreated database."""
    data = _read(Path(path))
    if data is None:
        return LaserRecipeDatabase(), None
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as error:
        raise ValueError(f'recipe database is not UTF-8 text: {error}') from error
    return database_from_json(text), _revision(data)


def save_database(path: str | Path, database: LaserRecipeDatabase, expected_revision: str | None) -> str:
    """Write only when the file still has the revision that was loaded; return the new one."""
    target = Path(path)
    if _revision(_read(target)) != expected_revision:
        raise StaleDatabaseError('recipe database file changed since it was loaded; reload it before saving')
    text = database_to_json(database)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(target, text)
    return _revision(text.encode('utf-8'))
