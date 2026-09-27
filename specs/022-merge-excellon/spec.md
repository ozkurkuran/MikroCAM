# Feature Specification: Reviewed Excellon merge

**Feature Branch**: `022-merge-excellon`
**Created**: 2026-09-27
**Status**: Ready for planning
**Input**: Roadmap 22: duplicate centres, overlap checks, rebuilt tool map and preserved sources.

## User Scenarios & Testing

### User Story 1 - Review selected drill sources together (Priority: P1)
An operator selects two or more current Excellon objects and reviews a combined physical drill and
slot inventory, with each input tool mapped to the proposed output tool. Millimetre and inch sources
retain their physical positions and diameters.
**Why this priority**: A correct combined inventory precedes any destructive manufacturing decision.
**Independent Test**: Review two authored objects with mixed units, repeated tool identifiers and
both round holes and slots; verify dimensions, operation counts and source-to-output tool mapping.
**Acceptance Scenarios**:
1. Current drills, slot endpoints, diameters and units determine the inventory, even if cached drawing
   geometry or original source text differs.
2. Equal physical diameters share a sequential output tool; different diameters remain distinct.
3. Empty or malformed inputs produce a clear message; no source data is changed.

### User Story 2 - Inspect duplicates and conflicting footprints (Priority: P2)
The operator sees exact duplicate operations removed once and incompatible overlaps that prevent
creation. A same-centre hole with a different diameter remains a conflict rather than silently
choosing a tool. Equivalent reversed slots are duplicates.
**Why this priority**: Concatenating files can repeat drilling or hide incompatible tooling.
**Independent Test**: Review duplicate holes, reversed duplicate slots, nearby holes, drill/slot and
slot/slot intersections; only exact equivalent operations collapse and all other overlaps block.
**Acceptance Scenarios**:
1. Identical physical hole/diameter or slot/endpoints/diameter combinations retain their first
   representative and disclose every removed operation's source.
2. Coincident centres with different diameters and other overlapping footprints block creation;
   nonoverlapping or exactly tangent footprints remain eligible.
3. No nonzero merge tolerance, position snapping or diameter averaging is applied implicitly.

### User Story 3 - Publish a separate complete merged Excellon (Priority: P3)
After reviewing a valid inventory, the operator names and creates a separate Excellon object with
normal destination defaults. Source objects, tool settings and original text remain intact.
**Why this priority**: A reviewed merge must export and survive project persistence reliably.
**Independent Test**: Create a mixed-unit merge, export/reparse holes and slots, save/reopen the
project, and compare all sources and final operations. Change a source after review to reject creation.
**Acceptance Scenarios**:
1. Only a reviewed conflict-free result can be created, with rebuilt sequential tool identifiers.
2. Renamed, edited, removed or replaced source objects invalidate review before publication.
3. Factory or local export failure publishes no partial object; source objects remain unchanged.
4. Export/reparse retains centres, endpoints and diameters within configured output precision;
   normal project persistence retains source data and merged operations.

### Edge Cases
Repeated input selection, conflicting same-centre tools, reversed and zero-length slots, mixed
units, empty tools/sources, stale geometry caches, nonplanar/nonfinite points, malformed collections,
large inputs, tangent footprints, source mutation during export, and exporter precision.

## Requirements

### Functional Requirements
- **FR-001**: Review between two and 64 explicitly selected distinct current Excellon objects.
- **FR-002**: Use current source units and authoritative per-tool diameters, drills and slots;
  retain source/tool identity and convert physical units once at each boundary.
- **FR-003**: Rebuild a deterministic sequential output tool map using exact equal physical
  diameters. Preserve all distinct diameters and slot endpoint orientation of retained operations.
- **FR-004**: Remove exact equivalent duplicate operations with a visible source mapping and count;
  do not collapse merely nearby centres, similar diameters or short slots.
- **FR-005**: Detect same-centre incompatibilities and all other round-hole/slot footprint overlaps;
  block creation while any conflict exists, with bounded actionable details. Tangency is allowed.
- **FR-006**: Require explicit creation after displaying sources, output tools, duplicate removals
  and conflicts. Make destination defaults clear without inheriting arbitrary source settings.
- **FR-007**: Revalidate source membership, names, units and authoritative content before destination
  initialization and before publication; a stale or altered review must be rejected.
- **FR-008**: Preserve every source's tools, geometry, settings, units and source text on success and
  failure. Complete normal local export before publishing the separate result.
- **FR-009**: Bound source/tool/operation counts and conflict reporting; reject invalid, nonfinite,
  nonplanar or degenerate operations without silent repair. Do not add a project format or dependency.
- **FR-010**: Verify analytic duplicates/overlaps, source guards, MM/IN export/reparse, slot persistence
  and an actual desktop selected-source merge flow alongside all prior delivered behavior.

### Key Entities
- Source snapshot: current identity, units, authoritative operations and change fingerprint.
- Operation: physical round hole or straight slot with a positive tool diameter and source tool.
- Merge review: output tools, input-to-output map, removed duplicates and blocking conflicts.

## Success Criteria
- **SC-001**: Every retained output operation corresponds to a current selected source operation;
  physical dimensions match within 1e-6 mm before exporter quantization.
- **SC-002**: All exact duplicate fixtures collapse once with traceable source mapping, while distinct
  nearby operations are retained or reported as conflicts without silently moving or resizing them.
- **SC-003**: All tested incompatible footprints prevent creation; tangent fixtures remain accepted.
- **SC-004**: Source mutation, identity replacement and output failure never publish a stale or partial
  merge. Sources compare unchanged after successful creation and normal project roundtrip.
- **SC-005**: Export/reparse and actual desktop journeys pass at configured output precision; full
  regression, architecture checks and final-head Windows CI pass before delivery.

## Assumptions
This workflow adds reviewed merging alongside the existing legacy merge. It does not perform
machining, repair sources, add circular/curved slots, infer plating/layer meaning, snap positions or
average diameters. Sources with overlapping intended operations must be corrected separately.
Exact equality is evaluated after physical unit normalization; numerical differences remain visible
as distinct operations or conflicts. Optional approximate fusion can be a later evidenced need.
