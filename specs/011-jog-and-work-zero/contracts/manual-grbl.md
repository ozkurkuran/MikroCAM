# Manual GRBL contract

## Public domain values and pure functions
`models.py` adds `ManualPhase` and frozen `ManualObservation` before `MachineSnapshot`.
Phase values: READY, PREPARING, MOVING, VERIFYING, CANCELLING, COMPLETE, FAILED, ABORTED.
Observation fields (safe defaults): `phase=READY`, `action=None`, `diagnostic=''`,
`can_jog=False`, `can_zero=False`, `can_select_g54=False`, `can_cancel=False`,
`stop_unverified=False`. MachineSnapshot adds `manual=ManualObservation()`.

`manual_models.py` provides frozen `JogRequest(axis, distance_mm, feed_mm_min)`,
`ZeroRequest(axes)`, empty `SelectG54Request`, `ModalState(work_system, units, distance,
spindle, coolant)`; coolant is an immutable tuple of M7/M8, or exactly ('M9',).
`ParameterRecord(name, value)` contains mm XYZ for G54..G59/G92 or a mm float for TLO.
`StartupRecord(index, block)` has index0/1 and bounded ASCII block text. Construction rejects
invalid/mutable/nonfinite/bool values; exact jog/zero choices are specified in data-model.md.

`manual_protocol.py` exposes:
- `encode_jog(request: JogRequest) -> bytes`: canonical ASCII `$J=G21 G91 X0.1 F100\n`
  (chosen signed axis/distance/feed substituted). No trailing spaces or extra words.
- `encode_zero(request: ZeroRequest) -> bytes`: `G10 L20 P1 X0 Y0\n`, `G10 L20 P1 Z0\n`
  or `G10 L20 P1 X0 Y0 Z0\n` only.
- `validate_command(data: bytes) -> None`: accepts only canonical encoded requests, `?`,
  `$$\n`, `$G\n`, `$#\n`, `$N\n`, `M5 M9\n`, `G54\n`, realtime0x85/0x18/0x84.
  All other bytes, embedded newlines/control bytes, wrong type, unsupported values or lengths
  over80 bytes raise ValueError. This is the shared controller/serial/Fake grammar boundary.
- `parse_modal(line: str) -> ModalState | None`: exact bounded `[GC:...]` query record,
  one work-system/unit/distance/spindle group and valid coolant group; duplicate/conflicting
  required groups or malformed numeric words fail. Unrelated records return None.
- `parse_parameter(line: str, report_units: str) -> ParameterRecord | None`: strict finite
  XYZ/scalar for the eight required G54..G59/G92/TLO rows; once-only mm conversion from mm/inch.
  Malformed recognized rows fail; unrelated messages/parameter rows return None.
- `parse_startup(line: str) -> StartupRecord | None`: strict `$N0=`/`$N1=` record, block<=80
  printable ASCII bytes; unrelated lines return None. A nonempty block is valid parsed data,
  but is rejected by the controller's admission policy, never executed or rewritten.
- `verify_zero(before: tuple[ParameterRecord, ...], after: tuple[ParameterRecord, ...],
  machine_position_mm: XYZ, axes: tuple[str, ...]) -> None`: require complete unique inventories,
  selected newG54=MPos-G92-TLO_z, omittedG54/otherWCS/G92/TLO unchanged, tolerance0.005mm.
  A mismatch/missing/invalid input raises ValueError. No mutation or global fallback.

## Controller and worker
Existing MachineController connect/disconnect/tick/snapshot remains. Add typed
`request_manual(request) -> None`, `cancel_jog() -> None`, `abort() -> None` on its sole
owner thread. No raw send method is exposed to UI. A concrete ManualControl collaborator
owns the operation phases; it must not open/read/close transport independently.
`set_interrupt_check(check)` installs the worker's thread-safe priority-event reader. The
domain checks it again immediately before motion/persistent writes, including after a bounded
read returns. It performs no I/O or GUI access; an already in-flight write remains subject to
the next bounded cancel/abort iteration.

The worker exposes `submit(request) -> bool` for one immutable intent slot, `cancel_jog()`,
`abort()` and existing `stop()`. Thread-safe stop/abort/cancel events take priority over the slot.
`submit` returns False when an intent/operation/stop is already pending. UI disables action
buttons immediately on accepted submission; the domain rechecks all gates before transmission.
I/O and controller construction remain entirely inside run(). Final snapshot is retained and
read only after actual worker join; old-session signals/intents cannot affect a new session.

Read-only connect still sends only settings/status reads. Every explicit manual action first
queries `$N`, then rejects nonempty/missing/duplicate/unacknowledged startup rows. Query `$G`
and `$#` rows belong only to their current ordinary transaction and remain provisional until
ACK. Unexpected ACKs cannot advance an unsent phase. Advance commands only after the full
incoming batch; one line transaction and one realtime status query may be outstanding.

Controller status query sequence must prove verification queries were sent after the relevant
ACK/cancel. Existing in-flight query results cannot satisfy a new phase. Jog requires expected
endpoint plus causal Idle; zero requires full offset read-back plus causal fresh WCO/work zero.
New motions/persistent writes never follow a tainted/ambiguous session without explicit reconnect.

## Stop and error policy
Cancel owned jog with0x85, discard queued requests, wait<=2s for a causal Idle report.
Door may include configured parking and cannot establish verified cancellation.
If it fails, request abort, retain stop-unverified evidence, clear positions and lock actions.
Abort0x18 is allowed only with completed, current-session empty `$N0`/`$N1` evidence; otherwise
send safety-door0x84 and explicitly report possible configured parking and unverified stop.
Never send cycle-start, unlock, home, output-start or startup/settings assignment commands.
Failed serial delivery cannot become a successful stop. Door/Alarm remain locked even if a
cancel terminates movement. A valid reset banner clears old transactions/unit/position/startup
proof and may reacquire read-only settings; it cannot resume manual activity automatically.

Disconnect during owned action follows cancel/abort before close, with a bounded final result.
Idle read-only disconnect has no action writes. Worker join budget4s covers normal cancel2s,
bounded writes/reads and cleanup; a violating worker is retained, not killed/disposed.

## UI and validation
A thin `MachineManualControls` widget owns step/feed selectors, +/-XYZ, Use G54,
Set G54 zero XY/Z/XYZ, Cancel jog and Abort buttons. No text-command field or repeating keys.
Explain persistent zero, output-off preparation, startup-block gate and physical-stop limits.
FakeGRBL records exact bytes and simulates modal state, offsets, jog/ACK/completion, cancellation,
reset and failures. No automated test opens or moves real hardware.
