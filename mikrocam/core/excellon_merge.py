"""Exact physical Excellon inventory with traceable duplicates and capsule conflicts."""
from .excellon_merge_models import (
    ExcellonMergeReview, MergeConflict, MergeDuplicate, MergeSource, MergeToolMap, OperationRef,
)
from .excellon_tools import ExcellonTool, operation_distance
from .placement import Point2D


Entry = tuple[float, Point2D, Point2D | None, OperationRef]


def _validate(sources: tuple[MergeSource, ...]) -> None:
    if type(sources) is not tuple or not 2 <= len(sources) <= 64 or any(type(s) is not MergeSource for s in sources):
        raise ValueError('Merge requires 2..64 immutable source snapshots')
    if len({s.source_name for s in sources}) != len(sources):
        raise ValueError('Merge source names must be unique')
    if sum(len(s.tools) for s in sources) > 1000 or sum(
            len(t.tool.drills_mm) + len(t.tool.slots_mm) for s in sources for t in s.tools) > 1000:
        raise ValueError('Merge exceeds 1000 input tools or operations')


def _entries(sources: tuple[MergeSource, ...]) -> list[Entry]:
    result = []
    for source in sources:
        for item in source.tools:
            for i, point in enumerate(item.tool.drills_mm):
                ref = OperationRef(source.source_name, item.tool_id, 'drill', i)
                result.append((item.tool.diameter_mm, point, None, ref))
            for i, (start, end) in enumerate(item.tool.slots_mm):
                ref = OperationRef(source.source_name, item.tool_id, 'slot', i)
                result.append((item.tool.diameter_mm, start, end, ref))
    return result


def _deduplicate(entries: list[Entry]) -> tuple[list[Entry], tuple[MergeDuplicate, ...]]:
    seen, retained, duplicates = {}, [], []
    for entry in entries:
        diameter, start, end, ref = entry
        key = (diameter, 'drill', start) if end is None else (diameter, 'slot', tuple(sorted((start, end))))
        if key in seen:
            duplicates.append(MergeDuplicate(seen[key], ref))
        else:
            seen[key] = ref
            retained.append(entry)
    return retained, tuple(duplicates)


def _tools(entries: list[Entry]) -> tuple[ExcellonTool, ...]:
    grouped = {}
    for diameter, start, end, _ in entries:
        drills, slots = grouped.setdefault(diameter, ([], []))
        if end is None:
            drills.append(start)
        else:
            slots.append((start, end))
    return tuple(ExcellonTool(diameter, tuple(drills), tuple(slots))
                 for diameter, (drills, slots) in sorted(grouped.items()))


def _conflicts(entries: list[Entry]) -> tuple[tuple[MergeConflict, ...], int]:
    details, count = [], 0
    for i, (diameter, start, end, ref) in enumerate(entries):
        for other_diameter, other_start, other_end, other_ref in entries[i+1:]:
            distance = operation_distance(start, end, other_start, other_end)
            if distance < (diameter + other_diameter)/2:
                count += 1
                if len(details) < 200:
                    reason = 'same-centre' if end is None and other_end is None and start == other_start else 'overlap'
                    details.append(MergeConflict(ref, other_ref, reason))
    return tuple(details), count


def review_excellon_merge(sources: tuple[MergeSource, ...]) -> ExcellonMergeReview:
    """Preserve selected operations exactly, removing only equivalent repeats."""
    _validate(sources)
    retained, duplicates = _deduplicate(_entries(sources))
    tools = _tools(retained)
    output_ids = {tool.diameter_mm: i for i, tool in enumerate(tools, 1)}
    tool_map = tuple(MergeToolMap(source.source_name, item.tool_id, output_ids[item.tool.diameter_mm])
                     for source in sources for item in source.tools)
    conflicts, count = _conflicts(retained)
    return ExcellonMergeReview(sources, tools, tool_map, duplicates, conflicts, count)
