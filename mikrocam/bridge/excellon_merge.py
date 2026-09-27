"""Bounded current Excellon snapshots and guarded separate merge publication."""
import hashlib
import math
from typing import Any

from shapely import get_coordinate_dimension
from shapely.geometry import Point

from mikrocam.core.excellon_merge import review_excellon_merge
from mikrocam.core.excellon_merge_models import ExcellonMergeReview, MergeSource, MergeSourceTool
from mikrocam.core.excellon_tools import ExcellonTool
from mikrocam.core.placement import Point2D

from .excellon import create_excellon_operations


def _feed(digest: Any, data: bytes) -> None:
    digest.update(len(data).to_bytes(8, 'big'))
    digest.update(data)


def _label(key: object) -> str:
    if type(key) is int and abs(key) <= 10**18:
        return f'int:{key}'
    if type(key) is str:
        try:
            if key and len(key.encode('utf-8')) <= 240:
                return f'str:{key}'
        except UnicodeError:
            pass
    raise ValueError('Excellon tool identifier must be a bounded integer or nonempty UTF8 text')


def _physical(value: object, factor: float, *, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise ValueError('Excellon dimensions must be finite nonboolean numbers')
    try:
        physical = float(value) * factor
    except OverflowError as exc:
        raise ValueError('Excellon dimension exceeds physical bounds') from exc
    if not math.isfinite(physical) or abs(physical) > 1e9 or positive and physical <= 0:
        raise ValueError('Excellon dimension exceeds supported physical bounds')
    return physical


def _point(point: object, factor: float, digest: Any) -> Point2D:
    if type(point) is not Point or point.is_empty or get_coordinate_dimension(point) != 2 or not point.is_valid:
        raise ValueError('Excellon operations require nonempty valid planar Points')
    coordinates = (_physical(point.x, factor), _physical(point.y, factor))
    _feed(digest, point.wkb)
    return coordinates


def _sequence(tool: dict, key: str, digest: Any) -> list | tuple:
    values = tool.get(key, ())
    if type(values) not in (list, tuple) or len(values) > 1000:
        raise ValueError('Excellon operation sequences must be lists or tuples within 1000 operations')
    _feed(digest, f'{key}:{len(values)}'.encode())
    return values


def _tool(tool: dict, factor: float, digest: Any) -> ExcellonTool:
    if type(tool) is not dict:
        raise ValueError('Excellon tools must contain dictionaries')
    diameter = _physical(tool.get('tooldia'), factor, positive=True)
    _feed(digest, repr(tool['tooldia']).encode())
    drills = _sequence(tool, 'drills', digest)
    slots = _sequence(tool, 'slots', digest)
    if not 1 <= len(drills) + len(slots) <= 1000:
        raise ValueError('Excellon tools require 1..1000 operations')
    physical_drills = tuple(_point(p, factor, digest) for p in drills)
    physical_slots = []
    for pair in slots:
        if type(pair) not in (list, tuple) or len(pair) != 2:
            raise ValueError('Excellon slots require two endpoint Points')
        start, end = (_point(p, factor, digest) for p in pair)
        if start == end:
            raise ValueError('Excellon slots must have distinct endpoints')
        physical_slots.append((start, end))
    return ExcellonTool(diameter, physical_drills, tuple(physical_slots))


def snapshot_excellon(owner: object) -> MergeSource:
    """Read current tool operations without touching cached geometry, files or settings."""
    if getattr(owner, 'kind', None) != 'excellon':
        raise ValueError('Select only Excellon objects')
    options = getattr(owner, 'obj_options', None)
    name = options.get('name') if isinstance(options, dict) else None
    try:
        valid_name = (type(name) is str and bool(name) and name == name.strip()
                      and name.isprintable() and len(name.encode('utf-8')) <= 256)
    except UnicodeError:
        valid_name = False
    if not valid_name:
        raise ValueError('Excellon source requires a trimmed printable bounded UTF8 name')
    units = getattr(owner, 'units', None)
    if type(units) is not str or units not in ('MM', 'IN'):
        raise ValueError('Excellon source units must explicitly be MM or IN')
    tools = getattr(owner, 'tools', None)
    if type(tools) is not dict or not 1 <= len(tools) <= 1000:
        raise ValueError('Excellon source requires 1..1000 tools')
    digest = hashlib.sha256()
    _feed(digest, name.encode('utf-8'))
    _feed(digest, units.encode())
    items, count = [], 0
    for label, tool in sorted((_label(key), value) for key, value in tools.items()):
        _feed(digest, label.encode('utf-8'))
        physical = _tool(tool, 1.0 if units == 'MM' else 25.4, digest)
        count += len(physical.drills_mm) + len(physical.slots_mm)
        if count > 1000:
            raise ValueError('Excellon source exceeds 1000 operations')
        items.append(MergeSourceTool(label, physical))
    return MergeSource(name, units, digest.hexdigest(), tuple(items))


def load_excellon_merge(owners: tuple[object, ...]) -> ExcellonMergeReview:
    """Snapshot exactly the explicitly selected distinct owners and review their operations."""
    if type(owners) is not tuple or not 2 <= len(owners) <= 64 or len({id(o) for o in owners}) != len(owners):
        raise ValueError('Select 2..64 distinct Excellon objects')
    snapshots, tools, operations = [], 0, 0
    for owner in owners:
        source = snapshot_excellon(owner)
        tools += len(source.tools)
        operations += sum(len(t.tool.drills_mm) + len(t.tool.slots_mm) for t in source.tools)
        if max(tools, operations) > 1000:
            raise ValueError('Excellon merge exceeds 1000 tools or operations')
        snapshots.append(source)
    return review_excellon_merge(tuple(snapshots))


def verify_excellon_merge(app: object, owners: tuple[object, ...], review: ExcellonMergeReview) -> None:
    """Recompute the complete review so stale or forged output cannot be published."""
    try:
        if type(review) is not ExcellonMergeReview or type(owners) is not tuple or len(owners) != len(review.sources):
            raise ValueError('Invalid source ownership')
        for owner, source in zip(owners, review.sources):
            if app.collection.get_by_name(source.source_name) is not owner:
                raise ValueError('Source ownership changed')
        if load_excellon_merge(owners) != review:
            raise ValueError('Reviewed operations changed')
    except Exception as exc:
        raise ValueError('Excellon source changed or is unavailable. Analyse again.') from exc


def create_excellon_merge(app: object, owners: tuple[object, ...], review: ExcellonMergeReview,
                          name: str) -> object:
    """Publish a conflict-free separate object under both source guards."""
    if type(review) is not ExcellonMergeReview or review.conflict_count:
        raise ValueError('Resolve all Excellon overlap conflicts before creation')
    return create_excellon_operations(app, review.tools, name,
                                      source_guard=lambda: verify_excellon_merge(app, owners, review))
