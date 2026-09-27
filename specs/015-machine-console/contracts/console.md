# Console and wire contract

## Models and log API
machine.console_models.CONSOLE_COMMANDS=('?','$$','$G','$#','$N','$I').
ConsoleRequest(command:str) frozen, exact allowed string only.
ConsolePhase READY/PENDING/COMPLETE/FAILED with lowercase values.
ConsoleObservation frozen: phase=READY,command=None,diagnostic='',can_query=False.
Validate enum/exact command, diagnostic<=256 and boolean eligibility.

machine.wire_log.WireRecord frozen fields:
sequence:int>=1,timestamp:finite nonbool float,direction:'TX'|'RX'|'IO',
payload:bytes<=4096,outcome:'complete'|'uncertain'|'received'|'error',
diagnostic:str<=256,omitted_bytes:int>=0.
Allowed pairs TX complete/uncertain, RX received, IO error (empty payload).
WireSnapshot frozen: records:tuple[WireRecord,...]=(),dropped_entries=0,dropped_bytes=0.
Validate ordered sequence, entry<=512 and retained payload<=262144, finite/bounded immutable values.
WireLog(clock=monotonic) is owner-only with append(direction,payload,outcome,diagnostic='')->None,
snapshot()->WireSnapshot and reset()->None for a new session. append bounds large byte payload to
4096 with omitted_bytes; counts omitted bytes and evicted retained bytes exactly once. Evict oldest
whole records to satisfy both caps. Empty RX produces no entry. No persistent file or I/O.
MachineSnapshot.console and .wire embed immutable observations with default empty values.

## Controller integration
Controller owns WireLog and ConsoleControl. Log raw nonempty read chunks before framing; unsupported
oversized/invalid transport results fail existing framing/communication rules without unbounded log.
Both _send and _send_job log requested TX after its bounded outcome is known. Complete requires exact
integer count (not bool); short count/exception logs uncertain and propagates existing failure path.
Validation/priority deferral before any transport call is not a TX attempt. Log I/O errors locally.
Reset log only for a new connect; disconnect/error retains final wire/query evidence.

request_console(ConsoleRequest) reserves owner state only; no I/O during worker admission lock.
Existing MachineWorker.submit union adds ConsoleRequest with console.can_query gate. Same pending
intent slot, no independent writer/reader. Manual/job eligibility excludes active/tainted console.
Fresh verified Idle and no manual/job/settings/query or any taint required; recheck before send.
Only new wire permission is exact $I LF; all other allowed queries already exist. Fake returns a
bounded build-info response for $I. Never broaden manual/job grammar to arbitrary text.

## Query ownership
ConsoleControl pending ordinary query consumes its own records/ACK before manual ACK handling.
Responses are visible as raw log data; no command-specific state assumptions except $$ units.
For $$ require one well-formed $13 row agreeing with existing units before its ACK can complete;
otherwise invalidate units/positions and quarantine. Missing/duplicate/malformed evidence blocks.
One ordinary command,3s deadline, full received batch consumed before success opens admission.
Error/duplicate/unsolicited acknowledgement, reset/alarm/framing/status-stale or transport failure
during query sets FAILED and tainted; coordinates/units become unavailable where evidence was lost.
No stop/reset is invented for a read-only query failure; existing explicit Abort remains available.
Preserve failed diagnostic through late traffic/disconnect; no retry, new query/job/manual until reconnect.
? owns no ordinary ACK: record minimum status query sequence=current+1, wait for existing poll
scheduler's causal fresh report. Do not send duplicate ? while one is outstanding. Deadline3s.
Priority stop/abort/cancel/close prevents deferred query write. Disconnect cancels outstanding query
before transport close and preserves terminal outcome. Existing communication worker budget4s remains.

## UI
ui.console_controls.ConsoleControls is a thin widget in MachinePanel, collapsed initially to
preserve existing controls. Public query_combo,send_button,clear_button,log_view,diagnostic_label;
query_requested(object) emits ConsoleRequest. set_snapshot(snapshot,worker_available) updates
eligibility and recent log. Display plain escaped bytes (repr), direction/outcome/time/sequence,
omission counters and query diagnostic. No terminal escape interpretation/rich text.
Clear view hides events through current sequence without touching owner state; reconnect resets
the view for the new session. Failed/disconnected final log stays visible. Refresh rendering can
be bounded to200ms if needed; never allocate/append unlimited historical text. No persistence/export.