# Feature Specification: SVG drill candidates

**Feature Branch**: `018-svg-drill-detection`
**Created**: 2026-09-27
**Status**: Ready for planning
**Input**: Roadmap 18: Proteus SVG’den drill çıkarıp Excellon oluşturma.

## User Scenarios & Testing

### User Story 1 - Inspect possible holes (Priority: P1)
A PCB operator opens a Proteus-style SVG and reviews circular white openings surrounded by
larger concentric pad artwork, with physical centres and diameters before producing drill data.
**Why this priority**: Artwork is not a drill specification; visible evidence must be reviewed.
**Independent Test**: An authored board with known circles gives the expected physical candidates.
**Acceptance Scenarios**:
1. Given transformed metric or inch SVG artwork, when analysed with the chosen vertical flip,
   then candidates use the same physical coordinates as normal SVG import.
2. Given square, elliptical, open, hidden or isolated white artwork, when analysed,
   then it does not become a confirmed circular-hole candidate.
3. Given no supported holes or malformed input, then the result explains the absence or error
   and creates no object.

### User Story 2 - Create selected drill data (Priority: P2)
The operator selects reviewed candidates and creates a separate Excellon with tools grouped by
physical diameter; original artwork and existing objects are preserved.
**Why this priority**: Reviewed evidence becomes usable mechanical CAM data.
**Independent Test**: Select a subset of two diameter groups and inspect/export/reopen the result.
**Acceptance Scenarios**:
1. Given selected candidates, creation yields exactly their unique centres and stable tool groups.
2. Given no selection, cancel, an invalid output name or failed creation, no partial drill object appears.
3. Given mm or inch application units, exported/reopened centres and diameters agree physically.

### User Story 3 - Resolve ambiguity honestly (Priority: P3)
The operator sees source identity, interpretation rules and any duplicate/conflicting evidence.
Conflicting holes remain unavailable until the source is corrected.
**Why this priority**: Guessing a manufacturing hole from drawing appearance must remain explicit.
**Independent Test**: Repeated equal holes collapse; unequal coincident or overlapping holes are
reported and excluded; reloading another file clears prior candidates and selections.
**Acceptance Scenarios**:
1. Given equal duplicate evidence, one candidate is offered; incompatible overlapping evidence is excluded.
2. Given a changed file or flip choice, previous evidence cannot be used for creation.
3. Given save/reopen of created Excellon, normal drilling and project workflows remain available.

### Edge Cases
Inherited white/currentColor and invisible paint; nested transforms/use; partial arcs and low-sided
polygons; nonuniform scale; very small circles; compound shapes; coincident centres; near grouping
boundaries; negative coordinates; source and generated-geometry limits; cancel and repeated opening.

## Requirements
### Functional Requirements
- **FR-001**: Provide a dedicated SVG drill import/review entry without changing ordinary SVG import.
- **FR-002**: Use actual physical units, all supported source transforms and exactly the selected flip.
- **FR-003**: Offer only single closed, sufficiently circular white filled unstroked openings inside
  larger concentric nonwhite circular pad artwork; do not infer slots or holes from a bounding box alone.
- **FR-004**: Display finite centres, diameters, source identity and the geometric tolerances used.
- **FR-005**: Require explicit candidate selection and creation; state that artwork inference is heuristic.
- **FR-006**: Deduplicate equal evidence, reject conflicting/overlapping holes and group diameters
  deterministically with a stated tolerance; never chain tolerance matches into an unbounded group.
- **FR-007**: Create a complete independent Excellon using only selected candidates; preserve existing
  artwork and objects and use existing unit conversion/export/project behavior.
- **FR-008**: Clear stale evidence after file/flip changes, errors or reopening; cancel has no side effects.
- **FR-009**: Bound source, curve and candidate work; unsupported input fails with actionable feedback.
- **FR-010**: Validate analytic fixtures, project/export round trips and actual desktop workflow; distinguish
  authored Proteus-style evidence from validation of a genuine Proteus export.

### Key Entities
- **Source evidence**: source name/hash, physical frame/flip and resolved visible paint.
- **Drill candidate**: unique centre, physical diameter and contributing opening/pad identifiers.
- **Review**: bounded candidates, notices, selection and source identity.
- **Drill output**: diameter-grouped tools and selected unique centres, owned by a new Excellon.

## Success Criteria
### Measurable Outcomes
- **SC-001**: All analytic positive fixtures recover centres and diameters within 0.02 mm;
  negative fixtures create zero drill candidates.
- **SC-002**: Selection produces exactly the requested unique hole count and repeatable tool groups,
  with no diameter spread above 0.01 mm per tool.
- **SC-003**: Export/reopen and mm/inch boundary tests preserve physical centres and diameters
  within the declared export precision; original objects remain unchanged.
- **SC-004**: Invalid, ambiguous, cancelled or stale review states cannot create a drill object.
- **SC-005**: Full regression suite and desktop import/review/create/save/reopen pass with source provenance recorded.

## Assumptions
- Depends on roadmap 16 physical SVG handling; follows 17 delivery.
- Neo S2 white-opening/pad convention is interpreted conservatively, not proof of drill intent.
- Source files are read independently; edited existing geometry is not reparsed or assumed aligned.
- No authentic licensed Proteus SVG fixture is currently available; authored fixtures test the convention
  and this limitation remains visible in delivery evidence.
- General clipping/compound Illustrator appearance and generic geometry conversion are later slices.
- No machine communication, new permanent project schema or dependency is needed.
