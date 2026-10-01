# Feature Specification: Auto-level Z compensation

**Branch**: `026-autolevel-z-compensation` | **Created**: 2026-10-01
**Input**: Roadmap026; continue after delivered probe grid025.

## User Scenarios & Testing

### US1 - Follow the measured surface (P1)
An operator loads a complete height map and declares the reference surface work Z. Cutting
paths follow the measured board surface with bilinear heights instead of a flat assumed Z.
Independent test: flat, tilted and saddle surfaces yield known compensated depths at corners,
edges and interior points. Incomplete maps and coordinates outside the measured area are rejected.

### US2 - Preserve the placed job and curved paths (P1)
The operator compensates a currently reviewed G-code snapshot with declared placement and
approximation tolerances. Rotated/mirrored paths query the same physical map; circular and
helical paths become bounded straight segments. Original text remains unchanged.
Independent test: mm/inch, absolute/incremental, translation/rotation/mirror and clockwise/
counterclockwise/full-circle/helical programs produce the expected transformed geometry.

### US3 - Review and explicitly use the derived job (P2)
The operator sees the original, map provenance, reference, tolerances, derived travel bounds,
nominal time and a bounded line preview. A separate G-code file can be saved or loaded into
Machine through the current explicit job workflow. Nothing starts automatically. Changing
source, map or parameters invalidates the result; cancellation and closing remain responsive.
Independent test: prepare/save/load into Machine using Fake, reject stale transfer and join
preparation on shutdown without altering original files or sending preparation-time bytes.

## Requirements
- FR001: Require a complete validated map with all finite samples; bilinear interpolation in
  map work-mm coordinates, including outer edges, with no extrapolation or missing-value fill.
- FR002: Require explicit reference surface work Z and bounded positive XY segment/chord/surface
  tolerances. Cutting Z correction is measured height minus reference; preserve map provenance.
- FR003: Use the existing XY placement once, followed by the map's stored G54 work offset;
  preserve machine coordinates through a separate derived fixed-G54 mm/absolute program.
- FR004: Preserve supported units/modes, feeds, dwell, spindle/coolant and program-end meaning;
  unsupported or ambiguous programs fail clearly with source-line context, never skip content.
- FR005: Compensate feed moves only; retain declared rapid paths. Split feed lines at grid-cell
  boundaries and sufficiently often to bound surface-following error and XY segment length.
- FR006: Convert XY circular/helical G2/G3 paths to ordered linear segments with declared
  maximum chord error, preserve direction, sweep/endpoints and linearly varying original Z.
- FR007: Reject the complete feed path when outside the measured area, even between arc samples;
  reject excessive work/output and observe cancellation during bounded segmentation.
- FR008: Revalidate the exact derived job against declared machine XYZ limits, rapid clearance,
  feed and controller precision before it can be transferred. Show errors instead of approval.
- FR009: Bind output to original review, exact map snapshot and parameters; editing/deleting/
  closing/replacing any input or cancellation cannot deliver or transfer a stale result.
- FR010: Run preparation off the GUI thread, keep preview bounded and retain/join owned work on
  close. File I/O remains in the bridge. Preparation/save never connects or sends machine bytes.
- FR011: Save a separate G-code snapshot and transfer it through the existing Machine job
  review/confirmation/start/stop flow. Source objects and input files remain unchanged.
- FR012: Test core behavior before implementation; desktop Fake journey, full suite and
  final-head Windows CI pass before merge. No physical compensation/device claim is made.

## Key Entities
Complete height map; explicit compensation settings; original reviewed source; derived G-code
and fresh report; original-line ancestry; original/map content identity and simulated/measured origin.

## Success Criteria
- SC001: Analytic flat/plane/saddle queries and compensated segment endpoints agree within
  0.00001 mm before controller representation, with no out-of-map query accepted.
- SC002: Every emitted feed chord respects declared XY length and within-cell surface error;
  original arcs respect the declared chord deviation allowance. No G2/G3 remains in output.
- SC003: Hazardous/unsupported, stale, partial, out-of-map or excessive cases never yield a
  usable derived job; original source/map stay equal to their initial snapshots.
- SC004: UI cancellation is observed within 1 s excluding bounded file I/O/native operations;
  previews cap at 200 lines and preparation produces at most 250000 total physical lines.
- SC005: Actual desktop proves map load, prepare, separate save, Fake transfer/completion and
  stale-result invalidation; prior journeys and full Windows checks pass before software delivery.

## Assumptions and Scope
Map coordinates describe the same fixed board/G54 setup the operator declares for the job.
Reference height is explicitly entered, not inferred from a corner or stale machine state.
The existing three-axis mechanical dialect applies. Rapid motion is not surface-followed;
operator chooses safe clearance. Horizontal cutting must begin from a compensated cutting
position; a vertical feed plunge establishes that position after a rapid when needed.
No new probing, interpolation beyond the rectangle, adaptive map, bicubic interpolation,
automatic homing/zero/resume, new project format, tool/fixture collision simulation or laser use.

## Hazard Analysis
Wrong/stale map or reference changes depth: show identities/provenance/reference, require current
review and explicit board/G54 confirmation before save/transfer. Wrong transform can query a
wrong point: use the shared placement and map frame exactly once. Sparse segmentation misses
curvature: bound chord and surface approximation, reject unknown/excessive paths. Warped Z may
leave limits or unsafe rapid paths: independently preflight and precision-check derived output.
Output is prepared offline; machine connection, mechanical confirmation and Start/Stop remain
under existing controller gates. Software cannot establish clamp clearance, probe accuracy,
board registration or physical E-stop effectiveness. Validation uses simulation only.
