# Implementation Plan: Reviewed Excellon merge

Branch022-merge-excellon | Date2026-09-27 | [Spec](spec.md)

## Summary
Review2..64 selected current Excellons, preserve drills and straight slots, remove exact duplicate
operations visibly, reject all incompatible footprint overlaps and publish a separate guarded result.

## Technical Context
Pinned Python3.13/PyQt6/Shapely; no dependency changes. Core owns strict physical tools, merge records
and bounded analytic overlap/deduplication; bridge snapshots legacy tools and validates identity;
UI presents fixed selected owners, map/duplicates/conflicts and explicit creation. Source MM/IN is
normalized once; destination conversion once. No persistent schema or new defaults source.
Limits:64 sources,1000 input tools,1000 input operations,1000 output operations,200 detailed conflicts;
finite coordinates/positive diameters<=1e9mm. Exact equality only; no diameter averaging/snapping.

## Constitution Check
All eight gates YES before and after design:
1. Core stdlib/Shapely only; bridge host access; UI input/presentation; dependency direction unchanged.
2. A short Plugins menu hook only; legacy aggregate growth remains below+50.
3. Shared ExcellonTool/factory has SVG, Geometry and merge callers; no generic registry/dependency.
4. Explicit source/output units and current destination defaults; no new project format.
5. Tests precede immutable records, capsule geometry, snapshots, factory refactor and UI behavior.
6. No machine/laser operation. Explicit review, conflict block, stale guards and publication tests.
7. Independent extension of MikroCAM; no external code or new license obligations.
8. Three stories, <=40tasks.

## Structure
core/excellon_tools.py: ExcellonTool physical drills/slots and validation of final footprints.
core/excellon_merge_models.py: source/tool/reference/map/duplicate/conflict/review records.
core/excellon_merge.py: exact deduplication, sequential tool map and bounded analytic conflicts.
bridge/excellon.py: shared creator with slot-capable entry; old create_excellon_tools API adapts.
bridge/excellon_merge.py: strict source extraction/hash, current membership and exact review guards.
ui/excellon_merge.py: parent-owned modal fixed-source review; short appMain Plugins entry.
tests/test_excellon_merge*.py, test_excellon_tools.py and existing factory/SVG/Geometry regressions.
tests/smoke_excellon_merge.py plus smoke_app integration; docs/EXCELLON_MERGE.md.

## Complexity Tracking
No exceptions. Input caps make pairwise capsule checks explicit and bounded. Empty sources/tools are
rejected clearly rather than silently dropped. Slot handling is required to preserve accepted inputs;
curved slots and approximate tool fusion remain out of scope.
