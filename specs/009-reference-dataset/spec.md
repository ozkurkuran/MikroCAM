# Feature Specification: PCB reference dataset

**Branch**: `009-reference-dataset` | **Created**: 2026-09-27 | **Status**: Specified

**Input**: Roadmap 9: 10–20 authentic PCB references from KiCad, EasyEDA, Altium,
Eagle and Proteus; actual unchanged reference outputs and tolerant comparison.

## User Scenarios & Testing

### User Story 1 - Trust reference inputs (Priority: P1)
As a maintainer I can trace every board/file to immutable source and original distribution
terms, so regression evidence is reproducible and redistributable.
**Why this priority**: Untraceable or unlicensed samples cannot provide durable evidence.
**Independent Test**: Audit 10–20 distinct designs, all five tool origins, hashes and notices
offline. A changed input byte, duplicate design or missing required notice fails admission.
**Acceptance Scenarios**:
1. Every board has evidenced tool origin, original project/revision, source locations and license notices.
2. Copper, drill, outline, drill-map, native and original archive inputs have explicit roles; drawings are not parsed as drills.
3. Unknown redistribution permission or provenance prevents admission; renaming layers does not create new boards.

### User Story 2 - Preserve actual baseline behavior (Priority: P1)
As a maintainer I can reproduce both unchanged reference applications' real parsing and
CAM outputs, including failures, so current results cannot manufacture their own expectations.
**Why this priority**: Independent baselines distinguish inherited behavior from regressions.
**Independent Test**: Capture an admitted design twice with identical source/runtime/config;
normalized successful results agree. Retain both references even when they disagree.
**Acceptance Scenarios**:
1. Parsing, isolation and CNC use explicit fixed settings and verified unchanged source.
2. Each requested stage records real success, error or unsupported status with context;
   no repaired/substituted current output or empty fabricated success.
3. Geometry is normalized once to mm; ordered parsed CNC paths and original G-code are retained when available.

### User Story 3 - Explain selected-baseline differences (Priority: P2)
As a maintainer I explicitly select a reference and tolerances and receive a report that
distinguishes matches, measured differences and unavailable evidence.
**Why this priority**: Numerical tolerance must not hide topology, units or path-order errors.
**Independent Test**: Matching captures pass; an introduced hole/displacement/reversed path
fails; corruption, missing stages and repeated baseline errors are indeterminate.
**Acceptance Scenarios**:
1. Geometry type/component/ring counts and explicit absolute distance/area tolerances all pass.
2. CNC path metadata, count, order, vertex count and direction remain significant.
3. Only entirely comparable matching stages produce success. Errors/unsupported stages are never silently skipped.
4. Reports identify board/file/stage and evidence; tests/comparison never replace expected records.

### Edge Cases
Duplicate keys/IDs, traversal or escaping symlinks, corruption, absent units, nonfinite/Z/M/
invalid geometry, input/config mismatch, empty output and incomplete subprocess results
must report their context. Both references may differ; that does not authorize widening tolerances.

## Requirements

- **FR-001**: Admit 10–20 distinct authentic designs covering all five named origin tools with evidence;
  additional evidenced origins such as DipTrace/Fritzing/gEDA are allowed.
- **FR-002**: Preserve immutable source references, original bytes, SHA256, role and license/notice evidence for every file.
- **FR-003**: Retain actual outputs separately from both pinned unchanged applications; verify source before capture.
- **FR-004**: Capture Gerber/Excellon parsing, isolation and CNC using explicit fixed parameters,
  isolated subprocesses/settings, runtime evidence, no GUI and no hardware access.
- **FR-005**: Store schema-1 captures with explicit per-stage statuses, normalized finite valid 2D mm
  geometry, ordered parsed CNC paths and raw generated G-code where available; normalize units once.
- **FR-006**: Preserve actual failures/timeouts/unavailable stages, never substitute current output;
  repeated failures remain indeterminate rather than matching.
- **FR-007**: Repeated identical captures reproduce normalized successful outputs or record observed variation explicitly.
- **FR-008**: Require explicit baseline and finite nonnegative absolute distance/area tolerances; no automatic update/widening.
- **FR-009**: Compare geometry type/component/ring counts, Hausdorff distance and symmetric-difference area;
  ordered paths compare metadata/count/order/vertex count/direction and corresponding coordinates.
  Drill tool IDs, diameters, multiplicity and ordered drill/slot coordinates remain significant.
- **FR-010**: Strictly validate schemas/checksums/units/source/config linkage; reject duplicates, unsafe
  paths, corruption, nonfinite/nonplanar/invalid values and missing requested stages.
- **FR-011**: Report match/difference/indeterminate per stage; distinguish all-match, measured
  difference and indeterminate/invalid process outcomes. Baselines stay read-only in normal tests.
- **FR-012**: Test introduced mismatches, normalization, provenance corruption and meaningful failure
  cases before core implementation; maintain architecture/size gates without new dependencies or legacy/UI edits.

### Key Entities
Admitted board/input, source/license evidence, fixed configuration, baseline identity,
stage capture, geometry/ordered path, tolerances and comparison report.

## Success Criteria
- **SC-001**: 10–20 distinct admitted designs cover all five origins; every file's hash and license evidence verify offline.
- **SC-002**: Both references have an actual recorded outcome for every requested stage, with successes and failures auditable.
- **SC-003**: Identical declared captures reproduce successful normalized outputs, or documented variation prevents a reproducibility claim.
- **SC-004**: Deliberate geometry/path/unit regressions are detected; invalid or unavailable evidence never produces all-match.
- **SC-005**: One offline comparison produces a complete report without changing references, settings or machine state.

## Scope, Assumptions and Hazards
Candidate admission is pending; baseline API/configuration/IN/repeat probes have resolved
headless feasibility and are documented in research.md. Formal codec/config freeze precedes capture. The requirement
is 10–20 admitted designs, not a promised candidate count. Missing audited coverage is unmet scope.
Truthfully captured baseline failures satisfy evidence collection but are not comparable successes.
Raw G-code is audit evidence; comparison uses captured ordered parsed paths plus explicit machining
config. No new G-code interpreter, controller simulation or future preflight feature.
No product UI, legacy/baseline patches, CAD regeneration, geometry repair, new dependency,
hardware I/O or automatic golden update. Evidence hazards are wrong source/unit attribution,
lost ordering and failure-as-success; explicit provenance/config/tolerances/statuses address them.
