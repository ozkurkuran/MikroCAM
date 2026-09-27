# Feature Specification: Bounded jog and G54 work zero

**Feature Branch**: `011-jog-and-work-zero`
**Created**: 2026-09-27
**Status**: Specified
**Input**: Roadmap 11: Jog, XY/Z/XYZ work zero, G54 and movement locks during a job.
User directs completing roadmap slices in order after the read-only GRBL connection.

## User Scenarios & Testing

### User Story 1 - Move one deliberate increment (Priority: P1)
An operator moves one axis by a selected small increment to position a CNC tool. Each click
requests one bounded move; holding a key or pressing again while busy does not queue moves.
Spindle/laser and coolant outputs are commanded off before any jog is admitted.

**Why this priority**: Manual positioning is needed before setting a PCB work origin.
**Independent Test**: FakeGRBL accepts each +/- axis increment, reports the resulting position,
and proves no repeated move, mode change or emission-start command is sent.

**Acceptance Scenarios**:
1. **Given** a connected, fresh, verified Idle machine, **when** an axis direction is clicked,
   **then** one selected mm increment is requested at the selected bounded mm/min feed.
2. **Given** active or unknown machine/operation state, **when** a jog is attempted,
   **then** it is rejected without motion and the panel explains the lock.
3. **Given** a permitted request, **when** output-off preparation fails or is unverifiable,
   **then** no jog is sent and the operation fails visibly.
4. **Given** a jog is accepted, **when** the controller only acknowledges it,
   **then** the operation stays busy until a fresh terminal status and position verify completion.
5. **Given** inch reporting or inch/absolute parser modes, **when** a jog completes,
   **then** the requested increment is still mm and existing parser distance/unit modes remain intact.

### User Story 2 - Establish an explicit G54 work origin (Priority: P1)
An operator explicitly selects G54 and sets the current XY, Z or XYZ work coordinate to zero.
The panel states that zeroing changes stored G54 offsets and identifies exactly which axes
will change. Unselected axes and other coordinate systems are preserved.

**Why this priority**: The operator needs a verified work origin before later job execution.
**Independent Test**: Simulated G54 offsets, temporary offsets and tool-length offset yield the
expected selected-axis zero, while omitted axes remain unchanged and other systems are intact.

**Acceptance Scenarios**:
1. **Given** a different active work system, **when** Use G54 is explicitly selected,
   **then** G54 is selected and verified; opening/connecting does not change the work system.
2. **Given** verified G54 and Idle, **when** Set G54 zero XY/Z/XYZ is pressed,
   **then** only those axes are zeroed and success requires read-back plus fresh coordinates.
3. **Given** an error, lost reply or mismatched read-back, **when** zeroing cannot be verified,
   **then** the result is indeterminate, controls lock and the persistent write is never replayed.
4. **Given** an active job or unsafe state, **when** selecting/zeroing is attempted,
   **then** the operation is rejected before any coordinate-system write.

### User Story 3 - Cancel and close without leaving owned motion (Priority: P1)
An operator can cancel an owned jog, abort controller activity, or disconnect/close. Motion
requests cannot remain queued behind a cancellation. The panel distinguishes verified stop,
unverified stop and disconnected communication.

**Why this priority**: Introducing motion requires an explicit tested stop path from every state.
**Independent Test**: Fake faults, delayed replies, external running states and repeated Qt
lifecycles prove cancel/abort priority, command locks and truthful stop results without hardware.

**Acceptance Scenarios**:
1. **Given** an owned jog, **when** Cancel jog is pressed, **then** cancellation preempts other
   requests, no further move is sent and completion waits for a fresh stopped report.
2. **Given** any connected state, **when** Abort is pressed, **then** a controller abort is
   attempted, pending requests/evidence are invalidated and no automatic resume/unlock occurs.
3. **Given** owned motion, **when** disconnect or close is requested, **then** cancellation is
   attempted before closing; failure to verify stop is shown explicitly and cannot become success.
4. **Given** lost communication or stale status during owned motion, **when** a deadline expires,
   **then** a best-effort abort is attempted, further actions lock and positions become unavailable.
5. **Given** a queued GUI action, **when** machine state changes before it is processed,
   **then** the communication owner rechecks admissibility immediately before transmission.

### Edge Cases
- Repeated clicks, key autorepeat, concurrent cancel and action, shutdown during preparation.
- Partial/late/duplicate ACKs; status interleaved with responses; corrupt/oversized lines.
- Jog acceptance without movement completion, unexpected terminal position, limit error or alarm.
- G54/G92/tool-length composition, nonzero omitted axes, inch reporting and report quantization.
- Reset/banner during every phase; port loss, short write, close failure and failed abort delivery.
- External Run/Hold/Jog/Door/Home/Check/Sleep/Alarm and output state changed outside the application.

## Requirements

### Functional Requirements
- **FR-001**: Offer one-axis +/- incremental jog with explicit step and feed; reject nonfinite,
  zero, unsupported axis or out-of-policy values. No continuous/repeating jog or motion queue.
- **FR-002**: Admit manual actions only with an open, verified, fresh Idle session and no active
  transaction/job/operation; recheck gates at the I/O owner, not only in widgets.
- **FR-003**: Jog in mm with explicit incremental semantics without changing existing parser
  unit/distance modes. Preserve the single mm normalization and placement authorities.
- **FR-004**: Before jog, command spindle/laser and coolant off and verify accepted output-off
  mode and fresh Idle state. Verify both controller startup blocks are empty before any manual
  action so the owned-operation abort fallback cannot execute stored motion/output commands.
  Never emit an output-start, emission-arm or startup-block assignment command.
- **FR-005**: Serialize command acknowledgements and read-back phases; acknowledgement alone
  cannot complete movement or zeroing. Timed-out/ambiguous writes are never replayed.
- **FR-006**: Support explicit Use G54 and Set G54 zero XY/Z/XYZ actions; label persistent effects,
  preserve omitted axes/G55-G59 and never select G54 implicitly on connect or panel open.
- **FR-007**: Verify active G54, offset composition and changed values by controller read-back
  and fresh work coordinates before reporting success; invalid/missing evidence fails closed.
- **FR-008**: Provide priority Cancel jog and Abort actions, reachable while other controls are
  locked. A cancel cannot authorize another queued move or automatically resume/unlock.
- **FR-009**: Disconnect/close during owned motion attempts cancel then bounded abort fallback
  before closing; cable loss/timeout produces a visible unverified-stop diagnostic.
- **FR-010**: Keep a single transport owner; UI sends typed bounded intents, never wire text.
  Closing still retains/joins live workers and rejects old-session results.
- **FR-011**: Keep the existing read-only connect/status behavior until an explicit manual action;
  no port is opened and no real hardware is moved during automated validation.
- **FR-012**: Test allowed/forbidden states, ACK/reset/timeouts, stop and persistence effects with
  a simulator; retain existing CAM, architecture and real desktop smoke checks.

### Key Entities
- **Manual request**: axis, signed mm distance and mm/min feed, or explicit G54 operation.
- **Operation observation**: preparing, moving, verifying, cancelling, complete or failed;
  immutable status and diagnostic distinct from reported machine state.
- **G54 evidence**: active coordinate system, stored offsets, temporary/tool offset and mm positions.
- **Stop result**: verified cancellation, abort requested or stop unverified; no physical guarantee.

## Success Criteria
- **SC-001**: All permitted simulated jogs reach their analytic signed endpoint within 0.005 mm;
  all prohibited/repeated requests produce no additional motion command.
- **SC-002**: All XY/Z/XYZ zero cases yield selected-axis zero within 0.005 mm and preserve omitted
  axes/other systems within report precision; errors never claim success or replay a write.
- **SC-003**: Cancel/abort intent is handled by the next bounded worker iteration; simulated close
  with compliant I/O completes within four seconds, or explicitly retains a live worker.
- **SC-004**: Every simulated stale/reset/error/disconnect phase invalidates affected evidence,
  suppresses queued actions and leaves stop uncertainty visible; no emission-start byte is sent.
- **SC-005**: Ten simulated panel action/close cycles, full Windows/CPython 3.13 tests, architecture
  checks and existing desktop CAM smoke pass; no physical hardware success is inferred.

## Assumptions and Scope
- Standard three-axis GRBL 1.1 serial behavior; one exclusive application owner of the port.
- Fixed initial steps 0.1/1/10 mm and feeds 100/300/600 mm/min are application policy caps,
  not machine-travel/fixture clearance guarantees. Initial selection is 0.1 mm and 100 mm/min.
- G54 is the only selectable work system; other systems are preserved. No homing, unlock,
  resume, continuous jog, job streaming, console or profile persistence in this slice.
- Abort is a safety control required by introducing motion, not a general reset configuration UI.
- Real machine envelope/preflight is roadmap12; operators remain responsible for a clear path.

## Hazard Analysis
- Unexpected displacement: finite single-axis increments, bounded feed, no repeat/queue,
  fresh Idle checks and explicit direction labels reduce accidental motion.
- Unwanted emission: output-off preparation is mandatory; this slice cannot issue output-start
  commands. Controller acknowledgements do not measure physical laser/spindle power.
- Wrong origin: zero actions explicitly name persistent G54 effects; read-back verifies selected
  and omitted axes, temporary/tool offsets and fresh coordinates. Writes are never retried blindly.
- Cancellation decelerates rather than guaranteeing an instantaneous physical stop. Abort can
  lose position and clear temporary controller modes; all coordinates are invalidated afterwards.
- Cable loss cannot deliver a stop command. Report stop unverified, lock actions and direct the
  operator to the physical stop/interlock. Software does not replace E-stop, guards or interlocks.
- A controller reset can execute stored startup commands. Reject manual actions unless both
  startup blocks are verified empty; never erase them automatically. Without that evidence,
  Abort uses the safety-door stop instead of reset and explicitly warns that controller-defined
  parking may occur. Neither path claims a measured physical stop. Serial-port opening itself
  may reset the board and execute existing startup blocks before the application can inspect them.
- Never automatically home, unlock or resume after error/reset/reconnect; physical recovery is explicit.
