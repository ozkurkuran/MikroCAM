# Feature Specification: Read-only G-code preflight

**Feature Branch**: `012-gcode-preflight`
**Created**: 2026-09-27
**Status**: Ready for planning
**Input**: Roadmap12: bounds, units/modes, missing feed, unsafe rapid, Z range and duration estimate; reuse Placement. User: roadmap ne diyorsa onu yap.

## User Scenarios & Testing

### User Story 1 - Understand the actual programmed motion (Priority: P1)
An operator selects a CNC job or opens a G-code file and receives a line-numbered analysis of
its supported movements. Units and absolute/incremental modes are interpreted explicitly;
unsupported or ambiguous programs cannot receive a successful result.

**Why this priority**: Limits and timing are meaningless if the movement interpretation is wrong.
**Independent test**: Small mm/inch and absolute/incremental programs yield known endpoints,
linear and circular extents; invalid modes/words produce a blocked report with their source lines.

**Acceptance Scenarios**:
1. Given explicit units/modes and a supplied initial position, when straight or XY circular/helical
   moves are analyzed, then their complete extents include interior arc extrema and the start point.
2. Given missing or conflicting modes, malformed comments/numbers, unsupported commands or unknown
   coordinate changes, when analyzed, then the report is blocked without silently skipping movement.
3. Given an empty/oversized program, when analyzed, then a bounded explanatory failure is returned.

### User Story 2 - Check the declared machine and work setup (Priority: P1)
The operator supplies machine XYZ travel bounds, the initial program position, work placement,
Z translation and a minimum safe rapid height. The report identifies out-of-bounds paths, absent
or invalid cutting feed and unsafe rapid movement before anything is sent to a machine.

**Why this priority**: Wrong placement or travel assumptions can cause a collision.
**Independent test**: Analytic programs inside/outside declared bounds and safe Z produce expected
line-specific findings under translation, rotation and mirroring.

**Acceptance Scenarios**:
1. Given rotated/mirrored placement, when analyzed, then travel checks use the transformed complete
   path rather than source extents or only endpoints.
2. Given a rapid with horizontal displacement whose lowest Z is below safe height, or a downward
   Z-only rapid below that height, then the report is blocked. Upward Z-only retreat may start below it.
3. Given a cutting move with missing/nonpositive feed or any path outside declared XYZ limits,
   then the report is blocked and identifies the triggering line and reason.
4. Given missing/invalid setup, then analysis cannot display a successful result; no machine
   dimensions, work zero or initial position are inferred from geometry or silent defaults.

### User Story 3 - Review a useful, honest report (Priority: P2)
The operator sees source identity, interpreted bounds, movement counts, warnings/errors and a
nominal duration estimate. Analysis runs without freezing the UI and can be cancelled. Replacing
source/setup invalidates an earlier result. This feature never transmits or edits G-code.

**Why this priority**: A readable report makes the checks usable and prevents stale-result trust.
**Independent test**: File and selected-job workflows show the same result for identical text,
react to source/setup changes, stay responsive, and leave source objects/files unchanged.

**Acceptance Scenarios**:
1. Given feed and optional explicit per-axis rapid rates, then moving time and dwell are estimated
   with stated assumptions. Unknown rapid rates or operator pauses make total time unavailable.
2. Given a blocked/uninterpretable program, then no complete bounds or total duration is claimed;
   any displayed interpreted prefix is labeled partial.
3. Given cancellation, replaced input or panel closure during analysis, then stale results cannot
   overwrite the current report and owned background work is joined or retained safely.
4. Given a successful report, then it states that checks cover the declared setup and supported
   dialect, not physical clearance, controller compatibility or permission to run a machine.

### Edge Cases
- Adjacent/repeated words, comment-contained commands, Unicode/control bytes, missing delimiters,
  nonfinite/huge values and modal conflicts; source line numbers survive blank lines/comments.
- G94 inch feeds and mid-program unit changes; feed retained in physical mm/min until another F
  word. Inverse-time G93 is outside this subset and blocked.
- Full-circle center arcs, clockwise/counterclockwise major/minor arcs, helix Z change, impossible
  radii and planes other than XY; transformed interior extrema at arbitrary rotation/mirroring.
- Simultaneous rapid XYZ near safe Z, initial position outside limits and final source after end.
- Machine/work coordinates, temporary/tool offsets, tool changes, probing/macros/subprograms and
  canned cycles outside the supported subset must fail clearly rather than inherit unknown state.
- Large files, many diagnostics, cancellation and repeated analysis; deleted/edited selected job.

## Requirements

### Functional Requirements
- **FR-001**: Analyze an explicit immutable source snapshot from a UTF-8 G-code file or selected
  CNC job; preserve exact text and line identity and never mutate/send it.
- **FR-002**: Interpret documented units/distance/feed modes, straight moves and XY arcs/helices,
  with explicit initial position and fail-closed handling of unsupported/ambiguous syntax.
- **FR-003**: Normalize once to mm and apply the established Placement authority for XY; use an
  explicit Z translation. Include the entire path when computing machine-space bounds.
- **FR-004**: Require explicit finite setup, ordered XYZ bounds and safe rapid height within Z
  limits. Do not derive hardware limits from job metadata or open a machine connection.
- **FR-005**: Diagnose every interpreted movement outside XYZ limits, missing/nonpositive feed,
  unsafe horizontal rapid and unsafe downward rapid with source line and actionable reason.
- **FR-006**: Report counts, units/modes encountered, source identity/digest, full or partial bounds,
  and bounded line-specific findings with total counts even if displayed samples are capped.
- **FR-007**: Provide nominal feed/rapid/dwell duration only when known; label acceleration,
  controller scheduling and operator wait exclusions. Never display unknown total time as zero.
- **FR-008**: Run analysis away from widgets, support cancellation, reject obsolete results and
  safely join/retain workers on close/application shutdown.
- **FR-009**: Changes to source or setup invalidate displayed approval. Use the exact immutable
  input underlying a result; no cached result can silently apply to a different job/setup.
- **FR-010**: Bound source size, line length, numeric magnitude, work and diagnostic storage;
  invalid/unsupported content blocks success without causing unbounded GUI work or allocations.
- **FR-011**: Retain existing CAM/laser/manual controls and architecture; prove analysis with pure
  analytic tests, actual selected-job/file UI flow and full Windows validation.

### Key Entities
- Source snapshot: source name, exact text and content digest.
- Declared setup: initial program XYZ, XY Placement, Z translation, machine limits, safe rapid Z
  and optional per-axis rapid rates, all explicitly expressed in mm and mm/min.
- Interpreted move: source line, mode, start/end and exact geometric path information.
- Report: complete/partial status, counts/extents, duration availability/assumptions and findings.

## Success Criteria
- **SC-001**: Analytic mm/inch/absolute/incremental linear and arc fixtures agree with expected
  transformed bounds within1e-6mm and nominal duration within1e-6s for well-conditioned fixtures.
- **SC-002**: Every hazardous or unsupported fixture is blocked with correct source line;
  none gains success by dropping unknown syntax, missing setup or arc interior travel.
- **SC-003**: Repeated/cancelled/closed analysis does not send machine bytes or mutate input;
  obsolete results never replace the current UI report.
- **SC-004**: A100000-line supported file completes within10s on the development machine and
  cancellation is observed within1s excluding a single bounded setup/read operation.
- **SC-005**: Pure, bridge, Qt and actual desktop smoke/full Windows checks pass; all unresolved
  physical/controller limitations remain visible in the report and delivery evidence.

## Assumptions and Scope
- Standard three-axis GRBL-oriented subset, fixed G54 program coordinate setup with no live
  machine-state inference. Other WCS/offset changes, probing, tool changes and macros are blocked.
- The operator's supplied placement/initial state and envelope are assumptions, not measurements.
  Initial G92 and tool-length offset are assumed zero; G54/G40/G49 restate that fixed setup.
  Unknown inherited offsets cannot be approved by this offline report.
- No send/run/pause/resume, streaming, automatic G-code repair, machine profiles or new persistent
  project format. Roadmap13 consumes this analysis later; dry-run is14.
- This is geometric/numeric preflight, not tool/stock/fixture collision simulation or laser arming.

## Hazard Analysis
Incorrect interpretation can understate travel: unknown modes fail closed and arcs use full extents.
Wrong setup can make otherwise correct checks irrelevant: require explicit values and show them.
Partial parsing cannot approve the full job. Stale results are invalidated. Duration is nominal,
not measured controller execution time. Successful preflight never guarantees physical clearance.
