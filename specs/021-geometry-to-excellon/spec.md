# Feature Specification: Geometry circles to Excellon

**Feature Branch**: `021-geometry-to-excellon`
**Created**: 2026-09-27
**Status**: Ready for planning
**Input**: Roadmap21: select circles, measure diameters and create diameter-grouped Excellon.

## User Scenarios & Testing

### User Story 1 - Review circles in current Geometry (Priority: P1)
An operator selects a Geometry object and reviews its complete circular boundaries at their current
physical positions. Each candidate shows centre, measured diameter and boundary role so a pad or
outer contour is not silently treated as a manufacturing hole.
**Why this priority**: Correct physical candidates are the prerequisite for a useful drill file.
**Independent Test**: An authored object containing circles, polygon holes, ellipses and open arcs
shows only complete circles, with measured millimetre values and clear origin labels.
**Acceptance Scenarios**:
1. Given a current Geometry object, analysis uses its active geometry and explicit object units.
2. Given transformed circles, centres and diameters reflect the current geometry with no extra flip.
3. Given noncircular, open, invalid or excessive geometry, it is excluded with a reason or the
   bounded analysis fails clearly; it never repairs an ambiguous boundary into a drill candidate.

### User Story 2 - Select intended holes and review tool grouping (Priority: P2)
The operator explicitly selects intended holes and sees the resulting diameter groups before creating
an Excellon object. All candidates start unchecked; circular shape alone does not prove hole intent.
**Why this priority**: Circle recognition is evidence, while drilling intent remains a user decision.
**Independent Test**: Select a subset of known circles and inspect hole counts and representative
diameters; duplicates and conflicting selected overlaps cannot create repeated or overlapping holes.
**Acceptance Scenarios**:
1. Given a completed review, no hole is selected and creation is disabled until selection is valid.
2. Given selected diameters within the existing 0.01mm total-spread grouping tolerance, one tool
   uses their mean diameter; selection order does not change the result.
3. Given duplicate evidence for the same circle, candidates are deduplicated visibly; given selected
   overlapping or concentric different-sized circles, creation is rejected with a useful explanation.

### User Story 3 - Create a new Excellon while preserving source (Priority: P3)
The operator creates a new Excellon from the reviewed selection, preserving the source Geometry
object and all its machining settings. The result can be exported and saved in the normal project.
**Why this priority**: Conversion must produce usable drill data without destroying editable artwork.
**Independent Test**: Create selected holes, export/reparse and save/reopen, checking tool diameters,
centres, source geometry and settings. Editing the source after review prevents stale creation.
**Acceptance Scenarios**:
1. Given a valid unchanged review, creation produces only the selected holes in grouped tools.
2. Given a changed, renamed, removed or replaced source object, creation requires a new analysis.
3. Given an initialization/export failure, no partial Excellon is published and source remains intact.
4. Given millimetre or inch host units, the result retains physical centres and diameters after export
   within the configured output precision and after project save/reopen.

### Edge Cases
Duplicate rings, opposite orientation, concentric boundaries, polygon exteriors/interiors, closed
lines, multipart and tool-specific geometry, stale top-level caches, empty objects, points/open arcs,
ellipses, coarse regular polygons, self-intersection, nonfinite/3D data, extreme coordinates, units,
source edits during review, object replacement/rename, factory defaults and exporter failure.

## Requirements
### Functional Requirements
- **FR-001**: Analyse exactly one current Geometry object and use the same authoritative geometry
  represented by its single-geometry or tool-specific mode, preserving component/ring identity.
- **FR-002**: Recognize only complete bounded planar circular boundaries using an explicit physical
  residual tolerance; do not infer circles from bounding boxes or repair open/noncircular paths.
- **FR-003**: Show source identity, current units, circle centre/diameter in mm, boundary role and
  exclusions; state that an exterior, interior or closed line does not establish drilling intent.
- **FR-004**: Start with no candidates selected and create only explicitly selected candidates.
- **FR-005**: Deduplicate equivalent circle evidence, group by the existing total diameter-spread
  tolerance, and reject selections whose representative tools create duplicate or overlapping holes.
- **FR-006**: Reject stale review if source identity, name, unit mode or authoritative geometry changes.
- **FR-007**: Create a separate complete Excellon with normal factory defaults and normal exporter;
  leave the source object, tools, source text and project settings unchanged on success or failure.
- **FR-008**: Convert object units to physical mm and back to output units exactly once at each boundary;
  no source reparse, extra vertical flip or second placement transform is permitted.
- **FR-009**: Bound input expansion, circle fitting, candidates and notices with actionable failures;
  preserve existing SVG drill behavior when shared mathematical/grouping helpers are reused.
- **FR-010**: Validate analytic geometry, existing references, fake factory failures, physical-unit
  export/reparse and actual desktop review/project roundtrip without manufacturing equipment.

### Key Entities
- **Geometry review**: current object identity, authoritative geometry fingerprint, units and candidates.
- **Circle candidate**: measured centre/diameter, source component/ring role and duplicate evidence count.
- **Tool group**: selected hole centres and one representative diameter within the grouping tolerance.

## Success Criteria
### Measurable Outcomes
- **SC-001**: Analytic accepted circles match centre and diameter within0.01mm in both supported units;
  open arcs, ellipses and coarse polygons fail the documented circularity criteria.
- **SC-002**: Every created drill corresponds to an explicitly selected deduplicated candidate; grouping
  is deterministic and no accepted selection produces duplicate or overlapping drill footprints.
- **SC-003**: Source edits, renames, replacement/removal and unit changes invalidate stale creation in tests.
- **SC-004**: Source geometry/settings remain unchanged through creation/failure; project roundtrip is
  exact and Excellon roundtrip matches configured coordinate/tool output precision.
- **SC-005**: Full regression and actual desktop journeys pass with all prior SVG drill behavior intact,
  and no physical drilling or vendor compatibility is claimed without separate evidence.

## Assumptions
- This is a reviewed conversion of existing Geometry, not automatic drilling inference or file import.
- Circular polygon exteriors, interiors and closed lines may all be proposed with explicit role labels.
- Multi-tool objects use their current tool geometries rather than an unrelated top-level cache.
- No slots, freehand circle repair, interactive canvas editing, merging multiple source objects or
  hardware operation. Excellon merge follows in22.
- Existing circle-fit conservatism and0.01mm grouping policy are reused; no new tolerance preference.
