# Feature Specification: Review a manufacturing file set

**Feature Branch**: `024-manufacturing-import-wizard`
**Created**: 2026-09-27
**Status**: Ready for planning
**Input**: Roadmap24: multiple-file drop and layer classification, including F.Cu, B.Cu, PTH
and Edge.Cuts, following the import reporting work.

## User Scenarios & Testing

### User Story 1 - Collect and inspect a bounded file set (Priority: P1)

An operator drops several board production files into one import dialog or selects them together.
The dialog lists each file and its inferred format and layer purpose before anything is created.
**Why this priority**: A mixed manufacturing set must be reviewed as a set rather than opened blindly.
**Independent Test**: Drop/select a top copper, bottom copper, plated drill and outline set; verify
four distinct rows, source identity, classification evidence and no created objects.
**Acceptance Scenarios**:
1. Local Gerber and Excellon files are inspected without changing the files or existing project.
2. Repeated paths are not imported twice. Distinct files with the same basename remain distinguishable.
3. Unknown, unavailable, oversized or unsupported files have explicit errors or unresolved rows.
4. Files are bounded individually and as a set; folders, remote URLs and archives are not expanded.

### User Story 2 - Resolve layer assignments explicitly (Priority: P2)

The operator sees embedded metadata and filename hints, resolves conflicts, selects files to import,
and can correct format and layer assignments. F.Cu, B.Cu, PTH, NPTH and Edge.Cuts remain distinct.
**Why this priority**: A plausible filename alone must not silently override conflicting source facts.
**Independent Test**: Use files with metadata/filename disagreement, mixed drilling and ambiguous
names. Verify unresolved choices block the selected row until an explicit compatible assignment.
**Acceptance Scenarios**:
1. Recognized embedded layer metadata and filename hints are shown as separate evidence.
2. Conflicting evidence, unsupported roles and uncertain drill plating remain explicit. Unknown
   drills are never silently labelled plated; inner copper is never labelled top or bottom.
3. The operator may assign a compatible role, use an explicit Other role, or exclude a file.
4. Changing source or assignments invalidates the reviewed import action. Layer assignment does
   not mirror, translate, combine or otherwise change geometry.

### User Story 3 - Import the reviewed set and retain its results (Priority: P3)

The operator explicitly imports selected resolved rows. Each successful file becomes a normal CAM
object with the reviewed source and layer details; the dialog reports success or failure per file.
**Why this priority**: Reviewed classifications need to remain useful after creating and saving objects.
**Independent Test**: Import a mixed set, verify normal objects/defaults/geometry, save and reopen
without the input files, and verify source/layer evidence. Include one parsing failure in the set.
**Acceptance Scenarios**:
1. Import starts only after review, with at least one selected resolved file and unchanged sources.
2. Successfully created rows stay visible as successes and cannot be accidentally imported again
   by repeating the same action. A parser-reported failure or defective result never appears as
   success or publishes an object.
3. A file failure is shown clearly. Earlier successful files remain available and later pending
   files remain identifiable; there is no destructive rollback of existing or completed objects.
4. Normal parser/factory unit conversion and defaults are retained. No automatic alignment or
   bottom-layer mirroring is added. Original files and existing objects remain unchanged.
5. Per-object source and reviewed layer evidence survive project save/reopen without external files.

### Edge Cases

Empty selection, duplicate paths, duplicate names in different directories, duplicate content,
conflicting embedded metadata, conflicting filename hints, unknown drill plating, nonplated versus
plated drills, inner copper, unsupported metadata roles, changed or deleted sources, oversized sets,
mixed valid/invalid files, parser partial failure, units and existing object name collisions.

## Requirements

### Functional Requirements

- **FR-001**: Provide one multiple-file drop/selection dialog with explicit inspect, review and import steps.
- **FR-002**: Read a bounded set of local regular files and retain source names, byte lengths and content
  identities. Detect repeated paths without silently discarding distinct same-name files.
- **FR-003**: Propose Gerber/Excellon format and layer roles from recognized embedded metadata and
  conservative filename hints. Expose the evidence and any disagreement.
- **FR-004**: Distinguish F.Cu, B.Cu, PTH, NPTH and Edge.Cuts; retain an explicit Other role and unresolved
  state. Neither missing plating evidence nor inner copper may be guessed into a named outer layer.
- **FR-005**: Let the operator select/exclude rows and confirm compatible format/role assignments.
  Selected unresolved or erroneous rows prevent the reviewed import action.
- **FR-006**: Revalidate selected source identities before import and guard each file through object
  initialization. Parameter/source changes require review again.
- **FR-007**: Create separate normal Gerber or Excellon objects with existing parser/factory defaults
  and units, preserving exact original source bytes and reviewed layer evidence.
- **FR-008**: Report per-file import outcomes; do not publish parser-reported defective/failed objects, claim whole-set
  success after a failure, repeat completed rows, or delete previously created/existing objects.
- **FR-009**: Persist an optional versioned per-object source/layer report; older objects remain valid
  and malformed reports cannot display stale classification facts.
- **FR-010**: Verify classification conflicts, bounds, changed source, parser/factory failure, physical
  MM/IN host behavior and actual desktop multi-file import/project persistence alongside prior features.

### Key Entities

- File inspection: local source identity, format/role proposals and bounded evidence.
- Reviewed assignment: selected file, explicit format/role and output name.
- Import outcome: pending, imported or failed row and resulting object identity/error.
- Stored layer report: original source identity and confirmed classification at import time.

## Success Criteria

- **SC-001**: Analytic and licensed real file sets produce separate rows and correctly distinguish
  the four requested roles, with NPTH and unknown/conflicting cases explicitly handled.
- **SC-002**: Every ambiguous selected fixture requires explicit resolution; classification leaves
  original geometry coordinates and physical units unchanged.
- **SC-003**: Source/choice changes and malformed/oversized input cannot bypass review or create a
  false successful result; completed rows are preserved without accidental duplicate publication.
- **SC-004**: Valid mixed sets create normal usable objects; exact source and layer evidence survive
  project reopen after source deletion, with application defaults and existing objects preserved.
- **SC-005**: Focused/full regression, actual desktop drop/review/import/persistence, import-boundary
  and growth checks, and final-head Windows CI pass before delivery.

## Assumptions

This slice covers Gerber and Excellon production files, one file per object. Other formats retain
their existing import flows. Layer names describe source purpose; they do not define placement,
machine settings or job ordering. The bounded wizard has per-file outcomes rather than an atomic
transaction that deletes successful imports when another file fails. Archive/jobset/transfer-package
handling belongs to later roadmap slices. No new runtime dependency or project format is required.
