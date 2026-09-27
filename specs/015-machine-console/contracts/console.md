# Console and wire contract

## Models and log API
`machine.console_models.CONSOLE_COMMANDS = ('?', '$$', '$G', '$#', '$N', '$I')`.
`ConsoleRequest(command: str)` is frozen and accepts only an exact allowed string.
`ConsolePhase` has `READY`, `PENDING`, `COMPLETE`, and `FAILED` values, serialized in lowercase.
Frozen `ConsoleObservation` defaults to `phase=READY`, `command=None`, `diagnostic=''`, and
`can_query=False`. Validate the enum and exact command; limit diagnostics to 256 characters and
require boolean eligibility.

`machine.wire_log.WireRecord` is frozen and has these fields:

- `sequence`: integer >=1; `timestamp`: finite, non-boolean float.
- `direction`: `TX`, `RX`, or `IO`; `payload`: bytes <=4096.
- `outcome`: `complete`, `uncertain`, `received`, or `error`.
- `diagnostic`: string <=256 characters; `omitted_bytes`: integer >=0.

Allowed pairs are TX with `complete`/`uncertain`, RX with `received`, and IO with `error` and an
empty payload.

Frozen `WireSnapshot` contains `records: tuple[WireRecord, ...] = ()`, `dropped_entries=0`, and
`dropped_bytes=0`. Validate ordered sequence, at most 512 entries, at most 262,144 retained payload
bytes, and finite/bounded immutable values.

`WireLog(clock=monotonic)` is owner-only and provides `append(direction, payload, outcome,
diagnostic='')`, `snapshot()`, and `reset()` for a new session. `append` bounds large byte payloads to
4096 bytes and records the omitted count; it counts omitted and evicted retained bytes exactly once.
Evict the oldest whole records to satisfy both caps. Empty RX reads produce no entry. The log does
not perform persistent file I/O.

`MachineSnapshot.console` and `.wire` embed immutable observations with empty defaults.

## Controller integration
The controller owns `WireLog` and `ConsoleControl`. Log nonempty raw read chunks before framing.
Oversized or invalid transport results follow existing framing/communication failure rules and do
not create an unbounded log.

Both `_send` and `_send_job` log requested TX after the bounded outcome is known. A complete write
requires an exact integer count (not a boolean); a short count or exception logs an uncertain
outcome and follows the existing failure path. Validation or priority deferral before a transport
call is not a TX attempt. Log local I/O errors. Reset the log only for a new connection; retain
final wire/query evidence after disconnect or error.

`request_console(ConsoleRequest)` reserves owner state only; it performs no I/O under the worker
admission lock. Add `ConsoleRequest` to the existing `MachineWorker.submit` union with the
`console.can_query` gate. Use the same pending-intent slot, with no independent writer or reader.
Manual/job eligibility excludes an active or tainted console. Require fresh verified Idle state and
no manual/job/settings/query operation or session taint; recheck before sending.

The only new wire permission is exact `$I\n`; all other allowed queries already exist. Fake returns
a bounded build-info response for `$I`. Never broaden manual/job grammar to arbitrary text.

## Query ownership
`ConsoleControl` consumes a pending ordinary query's records/ACK before manual ACK handling.
Responses appear as raw log data; make no command-specific state assumptions except for `$$` units.

For `$$`, require exactly one well-formed `$13` row that agrees with existing units before its ACK
can complete. Otherwise invalidate units/positions and quarantine. Missing, duplicate, or malformed
evidence blocks completion.

Allow one ordinary command with a 3-second deadline. Consume the full received batch before success
opens admission. An error, duplicate/unsolicited ACK, reset/alarm/framing/status-stale event, or
transport failure during a query sets `FAILED` and taints the session; clear coordinates/units when
their evidence is lost. Do not invent a stop/reset for a read-only query failure; the existing
explicit Abort remains available. Preserve failed diagnostics through late traffic and disconnect.
Do not retry or admit another query/job/manual action until reconnect.

`?` owns no ordinary ACK. Record `minimum_query = current + 1` and wait for a causally later fresh
report from the existing poll scheduler. Do not send another `?` while one is outstanding. Because
GRBL status replies have no request IDs, a status-poll timeout loses causal attribution; disable
diagnostic console queries until explicit reconnect. The query deadline is 3 seconds.

Priority stop/abort/cancel/close prevents a deferred query write. Disconnect cancels an outstanding
query before closing the transport and preserves its terminal outcome. Retain the existing
communication-worker 4-second budget.

## UI
`ui.console_controls.ConsoleControls` is a thin widget in `MachinePanel`, collapsed initially to
preserve existing controls. Public widgets are `query_combo`, `send_button`, `clear_button`,
`log_view`, and `diagnostic_label`; `query_requested(object)` emits a `ConsoleRequest`.
`set_snapshot(snapshot, worker_available)` updates eligibility and the recent log. Display escaped
bytes with `repr`, plus direction/outcome/time/sequence, omission counters, and query diagnostics.
Do not interpret terminal escapes or render rich text.

**Clear view** hides events through the current sequence; reconnect resets the view for the new
session. Keep failed/disconnected final logs visible. If needed, bound refresh rendering to 200 ms;
never allocate or append unlimited historical text. Do not add persistence or export.
