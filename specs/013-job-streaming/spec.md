# Feature Specification: ACK-tracked mechanical CNC job streaming

**Feature Branch**: `013-job-streaming`
**Created**: 2026-09-27
**Status**: Implemented and locally validated; final delivery gate pending
**Input**: Roadmap13: ACK streaming, pause/resume/stop and progress, with FakeGRBL failures;
user instructed completion in roadmap order. Dependencies011 and012.

## User Scenarios & Testing

### User Story 1 - Start exactly the reviewed CNC job (Priority: P1)
The operator loads a successful offline preflight result into the Machine panel and explicitly
starts that immutable job. The panel confirms the declared setup against fresh controller state,
then shows progress as source blocks are acknowledged. A last ACK alone does not mean finished.

**Why this priority**: Sending different text or using a different origin defeats preflight.
**Independent test**: A small simulated CNC job sends only its reviewed blocks in order, with at
most one unacknowledged block; mismatched source/setup/controller state sends no job block.

**Acceptance Scenarios**:
1. Given the exact reviewed text/setup and fresh idle GRBL, when Start is pressed, then preparation
   verifies empty startup blocks, mechanical CNC mode, G54/zero temporary/tool offsets and the
   declared initial position before any job block is sent.
2. Given a changed source/setup, stale state, active manual move, nonempty startup block, laser
   mode, mismatched origin/position or unsupported streaming block, then Start is rejected visibly.
3. Given sequential ACKs interleaved with status reports, then source-line progress advances only
   for the owning block; errors or duplicate/unsolicited ACKs stop further job transmission.
4. Given all source blocks acknowledged, then completion requires a new idle report at the expected
   endpoint and verified output-off state. Controller queue acceptance is not physical completion.

### User Story 2 - Pause deliberately and resume explicitly (Priority: P1)
The operator can pause an active job without losing its source-line correlation, then explicitly
resume the same job. The panel distinguishes decelerating from paused; pause does not promise
spindle/coolant power is off.

**Why this priority**: Feed hold and resume must not race ahead of queued intent or imply a safe stop.
**Independent test**: Simulated hold/resume around pending ACKs stops new block feeding immediately,
retains the correct next block, and resumes exactly once only after a fresh stopped hold/idle state.

**Acceptance Scenarios**:
1. Given an active stream, when Pause is pressed, then new feeding stops and feed hold is requested
   promptly; decelerating status cannot be shown as paused.
2. Given a paused job and fresh permitted state, when Resume is clicked, then only that job resumes.
   Old clicks, double clicks, reconnects or controller status changes never resume automatically.
3. Given ACK/status traffic while paused, then correlation remains intact and no job block is sent
   until explicit resume. Programmed pause/tool-change behavior outside this bounded slice is blocked.

### User Story 3 - Stop, faults and closure remain truthful (Priority: P1)
The operator can stop/abort from every job phase or disconnect/close the application. The pending
source is discarded, no automatic retry occurs, and failed delivery or uncertain physical stopping
remains visible with the final acknowledged count/source line.

**Why this priority**: A stopped UI must not leave undisclosed queued machine work.
**Independent test**: Simulated stop, error, cable loss, reset, alarm, timeout and close at every
phase suppress later blocks, attempt the bounded stop path and preserve diagnostic uncertainty.

**Acceptance Scenarios**:
1. Given preparation/running/pausing/paused/completing, when Stop/Abort/close arrives, then it takes
   priority over any pending block and invalidates the active job; no automatic resume/retry follows.
2. Given verified empty startup blocks, stop can request reset to flush queued activity; otherwise
   fallback avoids unverified startup execution and warns about possible safety-door parking.
3. Given loss/timeout/partial write/ambiguous ACK, then further job bytes stop, coordinates/job
   readiness are invalidated and the final result says stopping could not be physically verified.
4. Given an active worker on close, then ownership is joined or the window remains alive; reconnect
   starts a new session and cannot inherit pending job blocks or user confirmation.

### Edge Cases
- Interleaved status/push/query/ACK traffic; duplicate ACKs within one received chunk; ACK after
  cancel/reset/timeout; writes accepted only partially; response waits during dwell/queued motion.
- Real-time bytes embedded in comments, non-ASCII/control bytes, numeric spelling, source line
  mapping, overlong controller blocks and comment-only/empty lines.
- Inch/absolute/incremental modes and known G54 mapping; rotated/mirrored offline Placement cannot
  be streamed unchanged as if GRBL applied it. It must already be baked into source before this slice.
- Live G92/TLO, coordinate changes, programmatic pauses/tool changes, source after program end and
  output commands without explicit compatible equipment/spindle settings.
- Starting during jog/zero/query/another job; repeated UI actions, stale preflight and window reuse.
- Hold deceleration versus stopped hold, pause while an ACK is pending, resume after alarm/door/reset,
  stale status and stop during final output-off verification.

## Requirements

### Functional Requirements
- **FR-001**: Prepare an immutable execution snapshot from the exact source and setup that passed
  current preflight. Preserve digest and source-line mapping; remove only validated comments/blank
  content without changing numeric spelling or motion semantics. Reject oversized/unsupported blocks.
- **FR-002**: Keep one connection/communication owner and one ordinary block ACK owner; no second
  serial writer, arbitrary UI wire text, background auto-start or unbounded command queue.
- **FR-003**: Recheck fresh Idle, units, no competing operation, empty startup blocks, mechanical
  CNC mode, active G54, zero G92/TLO and exact initial-position/offset assumptions at Start.
- **FR-004**: Stream only setups whose declared XY mapping is a pure translation matching G54,
  with matching Z offset; reject rotation/mirroring unless already applied to the source itself.
  Never silently transform execution differently from the reviewed source.
- **FR-005**: Require explicit per-job mechanical spindle/equipment confirmation; no laser emission
  support or substitute ARM/interlock checkbox. Output-containing source needs explicit valid spindle
  speed and compatible controller configuration; failed proof blocks before job transmission.
- **FR-006**: Show preparing/running/pausing/paused/completing/completed/aborted/failed observations,
  source identity, acknowledged/total blocks, current source line and retained terminal diagnostic.
- **FR-007**: Advance only the matching ACK after the received batch has been processed; no later
  block may be sent in response to an ambiguous/duplicate ACK or an unprocessed priority signal.
- **FR-008**: Treat full acknowledgement separately from completion; require a causal fresh idle
  endpoint and accepted/read-back output-off state before success. Stop unknowns remain explicit.
- **FR-009**: Pause stops feeding immediately and requests feed hold; paused needs fresh stopped
  hold/idle proof. Resume is a separate explicit action gated by the same session/job and fresh state.
- **FR-010**: Stop/abort/close preempts all job phases, flushes queued activity when possible, never
  replays a doubtful block and leaves uncertainty visible across disconnect and UI disposal.
- **FR-011**: A stale status, alarm, reset, controller error, malformed evidence, ambiguous ACK,
  partial write or broken connection blocks further motion/output commands and locks the session.
- **FR-012**: Preserve manual controls and their ownership/read-only behavior; manual action controls
  are locked while a job is active or the session is tainted. Reconnect requires explicit new Start.
- **FR-013**: Bound preparation memory/cancellation, wire blocks, deadlines and worker close; status
  polling and priority intents continue during potentially long source-block acknowledgement waits.
- **FR-014**: Validate complete send/pause/resume/stop/error/close scenarios with a deterministic
  simulator plus full Windows/architecture/desktop regressions, without opening physical hardware.

### Key Entities
- Prepared job: immutable reviewed source/setup, bounded executable blocks with original line IDs,
  total count, expected endpoint and execution-policy evidence.
- Start intent: prepared job, current UI/session binding and explicit mechanical equipment confirmation.
- Job observation: phase/progress/source/current line/terminal reason and stop uncertainty.
- Controller preparation evidence: current startup blocks, settings, modal state, offsets and position.

## Success Criteria
- **SC-001**: Every simulated allowed job sends exactly its reviewed executable blocks in order;
  every forbidden admission sends zero job blocks. No doubtful write is replayed.
- **SC-002**: ACK progress is monotonic and exact; completion cannot occur from ACKs alone or a
  pre-trigger status report. Endpoint/outputs must be freshly verified.
- **SC-003**: Pause/stop intent is processed at the next bounded owner opportunity and checked
  immediately before each next job write; close completes within4s for compliant transport or retains it.
- **SC-004**: All phase/fault simulations preserve terminal failure/stop uncertainty and block queued
  post-stop actions; ten Qt job/close cycles have no surviving owner or obsolete-session delivery.
- **SC-005**: Existing manual/CAM/laser/preflight workflows, full tests, size/import/growth checks,
  actual desktop simulator flow and final-head Windows CI pass; no hardware success is inferred.

## Assumptions and Scope
- Standard GRBL1.1 mechanical CNC with explicit operator-declared spindle configuration and verified
  laser mode disabled. Laser emission requires a separate future ARM/interlock/source/recipe design;
  setting laser mode off does not identify physical wiring, hence the equipment confirmation.
- One source job at a time; ordinary send/response protocol, no character-counting/burst sender.
  No queue/scheduled jobs, probing, console, homing/unlock, automatic retry/recovery or persistence.
- No geometric rewrite: use already generated source matching verified G54. This intentionally
  restricts streaming relative to the broader offline Placement analysis offered in012.
- Source M0/M1 or tool changes are outside this first execution subset; operator pause/resume is
  provided by the panel. Unknown runtime assumptions cannot be converted into silent defaults.
- Machine/fixture envelope is operator-declared; software/controller evidence does not measure
  clearance, spindle power or physical stopping. Physical E-stop/interlocks remain required.

## Hazard Analysis
Wrong source/origin can invalidate limits: bind immutable bytes/setup and query live G54/position.
Spindle/laser ambiguity: explicitly scope mechanical equipment, verify controller mode/settings and
reject laser use; preflight alone never arms output. Feed hold can keep spindle/coolant energized,
so Pause is not an emission-safe stop. Reset can lose position and run startup macros; prove empty
startup records first, otherwise avoid reset and report possible safety-door parking. Cable loss
cannot deliver a stop; lock the job/session and retain stop-unverified status. Never auto-resume,
unlock or resend after failure. A bounded stop path complements physical E-stop and guarding.
