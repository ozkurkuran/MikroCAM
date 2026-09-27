"""Bounded manufacturing source review and sequenced normal host publication."""
from collections.abc import Iterator
from dataclasses import dataclass
from hashlib import sha256
import math
import os
from pathlib import Path
from shapely import get_coordinates, get_num_coordinates
from shapely.geometry.base import BaseGeometry
from mikrocam.core.manufacturing_models import (MAX_MANUFACTURING_FILES, MAX_MANUFACTURING_BYTES,
    MAX_MANUFACTURING_TOTAL_BYTES, ManufacturingFile, ManufacturingAssignment,
    ManufacturingReview, ManufacturingReport)
from mikrocam.core.manufacturing_codec import report_to_dict, report_from_dict
from mikrocam.importers.manufacturing_classify import inspect_manufacturing_bytes
from mikrocam.importers.gerber_statements import gerber_statements
from mikrocam.importers.manufacturing_lines import excellon_lines


def _error(error: object) -> str:
    return str(error).encode('utf-8', errors='replace')[:500].decode('utf-8', errors='ignore') or 'Import failed'


def _path(path: str) -> str:
    if type(path) is not str or not path or len(path.encode('utf-8')) > 4096:
        raise ValueError('Manufacturing path requires bounded nonempty text')
    return str(Path(path).resolve())


def _bytes(path: str) -> bytes:
    source = Path(path)
    if not source.is_file():
        raise ValueError('Source must be a local regular file')
    with source.open('rb') as stream:
        data = stream.read(MAX_MANUFACTURING_BYTES + 1)
    if not 1 <= len(data) <= MAX_MANUFACTURING_BYTES:
        raise ValueError('Manufacturing source requires 1..16MiB')
    return data


def _inspect(path: str) -> ManufacturingFile:
    try:
        data = _bytes(path)
        return ManufacturingFile(path, data, inspect_manufacturing_bytes(data, Path(path).name))
    except (OSError, ValueError) as error:
        return ManufacturingFile(path, b'', None, _error(error))


def inspect_manufacturing_files(paths: tuple[str, ...]) -> tuple[ManufacturingFile, ...]:
    """Keep failed rows and distinct same-name files; deduplicate canonical paths only."""
    if type(paths) is not tuple or not 1 <= len(paths) <= MAX_MANUFACTURING_FILES:
        raise ValueError('Select 1..64 manufacturing file paths')
    canonical = tuple(_path(path) for path in paths)
    result, seen, size = [], set(), 0
    for path in canonical:
        key = os.path.normcase(path)
        if key in seen:
            continue
        seen.add(key)
        source = _inspect(path)
        size += len(source.source_bytes)
        if size > MAX_MANUFACTURING_TOTAL_BYTES:
            raise ValueError('Manufacturing set exceeds the total 64MiB limit')
        result.append(source)
    return tuple(result)


def _fresh(review: ManufacturingReview) -> ManufacturingReview:
    if type(review) is not ManufacturingReview:
        raise ValueError('Manufacturing import requires a validated review')
    files = list(review.files)
    for assignment in review.assignments:
        expected = review.files[assignment.source_index]
        try:
            current = _inspect(_path(expected.path))
            if current != expected or current.error:
                raise ValueError('Source bytes or inspection changed')
        except Exception as error:
            raise ValueError('Manufacturing source changed or is unavailable. Inspect and review again.') from error
        files[assignment.source_index] = current
    return ManufacturingReview(tuple(files), review.assignments)


def review_manufacturing_files(files: tuple[ManufacturingFile, ...],
                               assignments: tuple[ManufacturingAssignment, ...]) -> ManufacturingReview:
    """Confirm explicit compatible assignments only against fresh source evidence."""
    return _fresh(ManufacturingReview(files, assignments))


def _guard(source: ManufacturingFile) -> None:
    try:
        if sha256(_bytes(source.path)).hexdigest() != source.inspection.source_sha256:
            raise ValueError('Source changed')
    except Exception as error:
        raise ValueError('Manufacturing source changed. Inspect and review again.') from error


def _material(geometry: object) -> None:
    pending, nodes, points, nonempty = [(geometry, 0)], 0, 0, False
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > 100000 or depth > 64:
            raise ValueError('Manufacturing output exceeds geometry tree limits')
        if type(item) in (list, tuple):
            if len(item) > 100000:
                raise ValueError('Manufacturing output has too many geometry nodes')
            pending.extend((child, depth + 1) for child in item)
            continue
        if not isinstance(item, BaseGeometry):
            raise ValueError('Manufacturing parser returned non-geometry material')
        points += int(get_num_coordinates(item))
        if points > 1000000:
            raise ValueError('Manufacturing output exceeds one million coordinates')
        if item.has_z or item.has_m or not item.is_valid:
            raise ValueError('Manufacturing parser returned invalid or nonplanar material')
        if any(not math.isfinite(v) or abs(v) > 1e9 for xy in get_coordinates(item) for v in xy):
            raise ValueError('Manufacturing output coordinates exceed finite bounds')
        nonempty = nonempty or not item.is_empty
    if not nonempty:
        raise ValueError('Manufacturing source produced no material')


def _parse(obj: object, source: ManufacturingFile, assignment: ManufacturingAssignment) -> str:
    if assignment.kind == 'gerber':
        result = obj.parse_lines(gerber_statements(source.source_bytes))
        if result not in (None, 'drill'):
            raise ValueError(f'Gerber parser reported {result!r}; object not published')
    else:
        lines = excellon_lines(source.source_bytes)
        if obj.parse_lines(lines) is not None:
            raise ValueError('Excellon parser failed; object not published')
        if obj.create_geometry() == 'fail':
            raise ValueError('Excellon geometry failed; object not published')
        used = [tool for tool in obj.tools.values() if tool.get('drills') or tool.get('slots')]
        if not used:
            raise ValueError('Excellon source has no drills or slots')
        for tool in used:
            _material(tool.get('solid_geometry'))
    _material(obj.solid_geometry)
    if getattr(obj, 'units', None) not in ('MM', 'IN'):
        raise ValueError('Manufacturing parser requires explicit MM or IN result units')
    return obj.units


def _create(app: object, source: ManufacturingFile, assignment: ManufacturingAssignment) -> object:
    units = getattr(app, 'app_units', None)
    if type(units) is not str or units not in ('MM', 'IN'):
        raise ValueError('Manufacturing import requires MM or IN host units')
    initialized, failures = [], []

    def initialize(obj: object, app_obj: object) -> str | None:
        try:
            _guard(source)
            if getattr(app_obj, 'app_units', None) != units:
                raise ValueError('Host units changed during manufacturing import')
            parsed_units = _parse(obj, source, assignment)
            origin = 'parser' if source.inspection.units_hint == 'unknown' else 'explicit'
            report = ManufacturingReport(source.inspection, assignment.kind, assignment.role, parsed_units, origin)
            obj.source_file = source.source_bytes.decode('latin1')
            obj.manufacturing_source = report_to_dict(report)
            _guard(source)
            if getattr(app_obj, 'app_units', None) != units:
                raise ValueError('Host units changed during manufacturing import')
            initialized.append(obj)
            return None
        except Exception as error:
            failures.append(_error(error))
            return 'fail'

    result = app.app_obj.new_object(assignment.kind, assignment.output_name, initialize, autoselected=False)
    if len(initialized) != 1 or result is not initialized[0]:
        raise ValueError(failures[0] if failures else 'Factory did not publish the initialized object')
    return result


@dataclass(frozen=True)
class ManufacturingReceipt:
    source_index: int
    owner: object | None
    error: str


def import_manufacturing_review(app: object, review: ManufacturingReview) -> Iterator[ManufacturingReceipt]:
    """Precheck all sources, then stop on the first failed file while retaining successes."""
    fresh = _fresh(review)
    for assignment in fresh.assignments:
        try:
            owner = _create(app, fresh.files[assignment.source_index], assignment)
        except Exception as error:
            yield ManufacturingReceipt(assignment.source_index, None, _error(error))
            break
        yield ManufacturingReceipt(assignment.source_index, owner, '')


def read_manufacturing_report(owner: object) -> ManufacturingReport | None:
    """Load optional historical source-role evidence without external files."""
    value = getattr(owner, 'manufacturing_source', None)
    return None if value is None else report_from_dict(value)
