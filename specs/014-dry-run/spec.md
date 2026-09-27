# Feature Specification: Reviewed XY dry run at a safe machine Z

**Feature Branch**:014-dry-run
**Created**:2026-09-27
**Status**:Implemented and locally validated; final delivery gate pending
**Input**:Roadmap014: Safe-Z / only XY; spindle off. Dependency013. User requests roadmap order.

## User scenarios and testing

### User Story1: Prepare a separate safe-plane job (P1)
An operator with a successful source preflight chooses an explicit machine-frame dry Z and prepares
an XY-only air-cut. The original program is unchanged. The new job first raises Z vertically if
necessary, then follows the source XY paths at the chosen plane with spindle/coolant start removed.
Independent test: source/digest/geometry unchanged; derived source contains only the initial upward
Z move, identical XY endpoints/arcs, no output-start or S words, and passes its own preflight.

Acceptance:
1. Given complete allowed preflight and dryZ>=initial machine Z/safeZ inside the declared envelope,
   preparation creates a separately named immutable source/report with original identity and line mapping.
2. Given inch/incremental/arc/helical source, the projected XY path preserves source motion order,
   modes and feed semantics while helical Z variation becomes a planar arc at the chosen height.
3. Given unknown semantics, programmed pause/toolchange, missing review, a downward initial move,
   unrepresentable number, envelope failure or no planar movement, preparation rejects before transport.

### User Story2: Review and transfer the derived job (P1)
The operator explicitly opens dry preparation from preflight, enters a blank-by-default dryZ,
and reviews original/derived identity, mapping, bounds and nominal time before transferring.
Independent test: editing/closing original preflight or dryZ clears pending derived results; slow
obsolete worker results cannot be transferred; preparation close joins or retains its owner.
Acceptance:
1. A successful current preflight offers Dry run; no height is inferred or defaulted.
2. New derived identity, chosen machine Z, bounds/time and source-line provenance are visible.
3. Transfer is explicit and uses the existing Machine panel with fresh equipment confirmation.
   Preparation never opens a port or starts motion.

### User Story3: Execute with the established controller (P1)
The derived job runs through the existing reviewed mechanical sender. Its initial position/G54
and output-off evidence are rechecked. Pause/resume/stop/error/close retain established behavior.
Independent test: Fake writes only the derived reviewed blocks in order, first Z-only movement
precedes any XY, output-start never appears, failures never fall back to the original cutting job.
Acceptance:
1. Explicit Start verifies matching live state; the original machining source cannot be substituted.
2. Progress identifies the dry source; its displayed source-line numbers refer to the derived preview
   whose lineage identifies original lines and generated preparation lines.
3. Stop/disconnect/close remains priority, with physical-stop uncertainty and no automatic restart.

## Requirements
- FR001 Require exact complete allowed current source preflight and immutable source binding.
- FR002 Require finite explicit machine dryZ within envelope, at or above initial machine Z and
  declared safeZ. Never insert a downward positioning move or derive fixture clearance silently.
- FR003 Support the existing interpreted subset/pure G54 translation. Preserve XY geometry,
  units/distance/plane/feed/order and arc/helical XY projection; remove every original motion Z.
- FR004 Remove M3/M4/M7/M8 and all S words. Retain/insert M5/M9; no output-start is emitted.
  Programmed pauses/tool changes/unsupported semantics block; no silent unknown-command removal.
- FR005 Generate a separate immutable source with original digest/setup identity, explicit dryZ,
  derived digest and a mapping of every emitted line to original line or generated preamble.
- FR006 Analyze and prepare the exact derived source through existing preflight/PreparedJob.
  Its bounds/time/endpoint must be reported independently. Reject no-XY jobs or failed preparation.
- FR007 Show original and derived identity, selected plane, bounded line preview/provenance,
  bounds and nominal time; clearly distinguish dry source progress from original source lines.
- FR008 Source/report/height changes or closure cancel/invalidate pending work and transfer;
  admitted active jobs remain the sealed snapshot already started.
- FR009 Run preparation off GUI/serial owner with bounded cooperative cancellation and retained
  ownership on close timeout. Memory remains bounded by existing source/line caps.
- FR010 Reuse one controller/transport and existing Start/ACK/pause/resume/stop/admission path;
  no new sender, automatic execution, second output mapping or separate geometry transform.
- FR011 Prove pure transform and Fake/Qt/desktop behavior without physical ports; preserve all
  existing mechanical, laser, manual and preflight tests and architecture limits.

## Key entities
Dry-run result: original source/report identity, explicit dry plane, derived PreparedJob and
immutable source-line lineage. Derived source uses existing SourceSnapshot/PreflightReport.
No persistence, queue, arbitrary transform mode or project-format change.

## Success criteria
- SC001 Analytic linear/arc/helical and unit/mode cases preserve XY geometry within1e-6mm before
  existing controller precision guards; source bytes/setup remain unchanged.
- SC002 Every forbidden setup/semantics emits zero transport bytes; every executable derived job
  contains zero output-start/S/original-Z words and a first purely vertical upward move if needed.
- SC003 Current-generation binding/cancellation prevents stale transfer; owned preparation cancels
  and joins within2s for the bounded worker or retains the panel/object.
- SC004 Fake/Qt complete,pause,resume,stop and close scenarios use the existing sender without
  original-source fallback; full Windows/architecture/desktop/final-head CI pass.
- SC005 Operator can prepare/review/transfer/start a dry run with all inputs explicit, no new
  hardware connection or hidden clearance assumption introduced.

## Scope and hazards
This first dry run is one fixed-height XY projection, not a simulation or collision guarantee.
Machine Z means the same frame as the envelope/safeZ. Clearance is operator-declared, not measured.
A low initial position is raised vertically before XY; the operator still verifies retract clearance.
ACK means queued acceptance; GRBL preserves planner order so later XY follows the earlier retract.
Existing source watchdog, numeric precision, G54/zeroG92/TLO and mechanical-only rules still apply.
Physical spindle stopping/interlocks/E-stop cannot be inferred from Fake or parser-state readback.
Source M0/M1 remains unsupported; no probe/dry spindle/axis selector framework is added.
