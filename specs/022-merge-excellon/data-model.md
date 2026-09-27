# Data model: Excellon merge

All records frozen dataclasses with exact immutable tuple membership, strict nonboolean finite
numbers, positive diameter<=1e9mm, XY tuples with absolute values<=1e9mm, strict UTF8 bounded text.
Source names are nonempty trimmed printable UTF8<=256bytes, tool IDs nonempty UTF8<=256bytes.

`ExcellonTool(diameter_mm, drills_mm:tuple[Point2D,...], slots_mm:tuple[tuple[Point2D,Point2D],...])`
in core/excellon_tools.py. Total1..1000 operations per tool, slot endpoints distinct; empty either
kind allowed, both empty rejected. Record validates shape only, so reviews can retain conflicts.
`validate_excellon_tools(tools)` checks exact nonemptytuple<=1000tools/1000totalops and no overlaps.
`operation_distance(start,end,other_start,other_end)` private or public typed helper can use Shapely
Point for drill and LineString for slot; analytic distance, no buffer tessellation.

core/excellon_merge_models.py:
- `MergeSourceTool(tool_id:str, tool:ExcellonTool)`.
- `MergeSource(source_name:str, source_units:str, source_sha256:str, tools:tuple[MergeSourceTool,...])`:
  exactMM/IN,64lowerhex,1..1000unique tool IDs,<=1000ops.
- `OperationRef(source_name:str, tool_id:str, kind:str, index:int)`:kind drill/slot, index0..999.
- `MergeToolMap(source_name:str, source_tool:str, output_tool:int)`:output1..1000.
- `MergeDuplicate(retained:OperationRef, removed:OperationRef)`.
- `MergeConflict(first:OperationRef, second:OperationRef, reason:str)`:reason same-centre/overlap.
- `ExcellonMergeReview(sources:tuple[MergeSource,...], tools:tuple[ExcellonTool,...],
  tool_map:tuple[MergeToolMap,...], duplicates:tuple[MergeDuplicate,...],
  conflicts:tuple[MergeConflict,...], conflict_count:int)`.
  Sources2..64unique names,totalinputtools/ops<=1000; outputtools1..1000,totalops<=1000;
  map<=1000,duplicates<=1000,conflicts<=200,count0..499500 andlen(conflicts)=min(count,200).
  Shape validation only; trusted bridge regenerates full review before publication. No Qt/host refs.

The immutable review is ephemeral and not inserted into project persistence. The dialog alone
retains actual owner identities. Destination stores normal tools/drills/slots/source_file.
