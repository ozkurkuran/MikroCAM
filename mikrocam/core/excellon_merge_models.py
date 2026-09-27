"""Immutable, bounded inventory and evidence for an ephemeral Excellon merge."""
from dataclasses import dataclass
import re
from .excellon_tools import ExcellonTool


def _text(value: str, label: str, *, source: bool = False) -> None:
    if type(value) is not str or not value:
        raise ValueError(f'{label} requires nonempty text')
    try:
        size = len(value.encode('utf-8'))
    except UnicodeEncodeError as error:
        raise ValueError(f'{label} requires strict UTF-8') from error
    if size > 256 or (source and (value != value.strip() or not value.isprintable())):
        raise ValueError(f'{label} requires bounded' + (' trimmed printable' if source else '') + ' text')


def _integer(value: int, minimum: int, maximum: int, label: str) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{label} requires an integer from {minimum} to {maximum}')


def _records(values: tuple, cls: type, minimum: int, maximum: int, label: str) -> None:
    if type(values) is not tuple or not minimum <= len(values) <= maximum or any(type(v) is not cls for v in values):
        raise ValueError(f'{label} requires {minimum}..{maximum} immutable {cls.__name__} records')


def _operations(tools: tuple[ExcellonTool, ...]) -> int:
    return sum(len(tool.drills_mm) + len(tool.slots_mm) for tool in tools)


@dataclass(frozen=True)
class MergeSourceTool:
    tool_id: str
    tool: ExcellonTool

    def __post_init__(self) -> None:
        _text(self.tool_id, 'Source tool ID')
        if type(self.tool) is not ExcellonTool:
            raise ValueError('Source tool requires an immutable ExcellonTool')


@dataclass(frozen=True)
class MergeSource:
    source_name: str
    source_units: str
    source_sha256: str
    tools: tuple[MergeSourceTool, ...]

    def __post_init__(self) -> None:
        _text(self.source_name, 'Source name', source=True)
        if type(self.source_units) is not str or self.source_units not in ('MM', 'IN'):
            raise ValueError('Source requires explicit MM or IN units')
        if type(self.source_sha256) is not str or re.fullmatch('[0-9a-f]{64}', self.source_sha256) is None:
            raise ValueError('Source requires lowercase SHA256')
        _records(self.tools, MergeSourceTool, 1, 1000, 'Source tools')
        if len({item.tool_id for item in self.tools}) != len(self.tools):
            raise ValueError('Source tool IDs must be unique')
        if _operations(tuple(item.tool for item in self.tools)) > 1000:
            raise ValueError('Source exceeds 1000 operations')


@dataclass(frozen=True)
class OperationRef:
    source_name: str
    tool_id: str
    kind: str
    index: int

    def __post_init__(self) -> None:
        _text(self.source_name, 'Source name', source=True)
        _text(self.tool_id, 'Tool ID')
        if type(self.kind) is not str or self.kind not in ('drill', 'slot'):
            raise ValueError('Operation kind must be drill or slot')
        _integer(self.index, 0, 999, 'Operation index')


@dataclass(frozen=True)
class MergeToolMap:
    source_name: str
    source_tool: str
    output_tool: int

    def __post_init__(self) -> None:
        _text(self.source_name, 'Source name', source=True)
        _text(self.source_tool, 'Source tool ID')
        _integer(self.output_tool, 1, 1000, 'Output tool')


@dataclass(frozen=True)
class MergeDuplicate:
    retained: OperationRef
    removed: OperationRef

    def __post_init__(self) -> None:
        if type(self.retained) is not OperationRef or type(self.removed) is not OperationRef:
            raise ValueError('Duplicate evidence requires immutable operation references')


@dataclass(frozen=True)
class MergeConflict:
    first: OperationRef
    second: OperationRef
    reason: str

    def __post_init__(self) -> None:
        if type(self.first) is not OperationRef or type(self.second) is not OperationRef:
            raise ValueError('Conflict evidence requires immutable operation references')
        if type(self.reason) is not str or self.reason not in ('same-centre', 'overlap'):
            raise ValueError('Conflict reason must be same-centre or overlap')


@dataclass(frozen=True)
class ExcellonMergeReview:
    sources: tuple[MergeSource, ...]
    tools: tuple[ExcellonTool, ...]
    tool_map: tuple[MergeToolMap, ...]
    duplicates: tuple[MergeDuplicate, ...]
    conflicts: tuple[MergeConflict, ...]
    conflict_count: int

    def __post_init__(self) -> None:
        _records(self.sources, MergeSource, 2, 64, 'Sources')
        if len({source.source_name for source in self.sources}) != len(self.sources):
            raise ValueError('Source names must be unique')
        if sum(len(source.tools) for source in self.sources) > 1000 or sum(
                _operations(tuple(item.tool for item in source.tools)) for source in self.sources) > 1000:
            raise ValueError('Input exceeds 1000 tools or operations')
        _records(self.tools, ExcellonTool, 1, 1000, 'Output tools')
        if _operations(self.tools) > 1000:
            raise ValueError('Output exceeds 1000 operations')
        _records(self.tool_map, MergeToolMap, 0, 1000, 'Tool map')
        _records(self.duplicates, MergeDuplicate, 0, 1000, 'Duplicates')
        _records(self.conflicts, MergeConflict, 0, 200, 'Conflicts')
        _integer(self.conflict_count, 0, 499500, 'Conflict count')
        if len(self.conflicts) != min(self.conflict_count, 200):
            raise ValueError('Conflict details must contain the first min(count, 200) records')
