# Feature Specification: Read-only machine console and bounded wire diagnostics

**Feature Branch**: 015-machine-console
**Created**:2026-09-27
**Status**: Delivered
**Input**: Roadmap 015: terminal and raw TX/RX log. User requests roadmap order.

## User scenarios and testing
### User Story1: Inspect the real communication stream (P1)
The operator opens Console in the Machine dock and sees the exact requested TX bytes and received
RX chunks, with timestamps and outcomes. Failed/partial writes are visibly uncertain; a request
is not presented as proof of delivery. The recent log stays available after disconnect/failure.
Independent test: scripted fragmented RX and completed/partial/error TX produce ordered immutable
records; bounds evict old data with explicit counters and controls display escaped plain text.
Acceptance:
1. Connect, manual actions, jobs and automatic polling all use the same recorded owner boundary.
2. Empty reads produce no noise; control/non-ASCII bytes cannot execute or alter terminal display.
3. Entry and byte limits bound memory. Clear view is explicit and does not affect the controller.
   A new connection begins a new visible session; disconnect preserves the terminal evidence.

### User Story2: Request supported diagnostic queries without disrupting control (P1)
When the connection has fresh Idle evidence and no other operation, the operator chooses an exact
supported read-only GRBL query. Results appear in the same wire log and a query outcome indicator.
Unsupported text, settings writes, motion/output commands and concurrent queries cannot be sent.
Independent test: each supported query has one ACK owner; job/manual/initial-settings conflicts
reject before writing. Timeout, reset, malformed unit evidence and duplicate ACK quarantine the
session so a late acknowledgement cannot release a later command.
Acceptance:
1. Supported queries are ?, $$, $G, $#, $N and $I. No arbitrary serial/G-code execution entry.
2. Ordinary queries share the existing worker/controller and never overlap another ordinary ACK.
   Status `?` routes through the existing polling schedule and waits for causal fresh evidence. If
   a status poll times out, its late reply cannot be distinguished from a later poll; disable
   diagnostic console queries until explicit reconnect restores attribution.
3. A complete query is acknowledged separately from trusting its printed data as machine state.
   A $$ query must preserve uniquely verified report units; disagreement invalidates coordinates.
4. Failure retains its diagnostic and log, blocks further ordinary operations until reconnect and
   never retries automatically. Stop/abort/disconnect remain priority over pending query intent.

## Requirements
- FR001 Capture exact bounded RX read chunks and all controller TX requests on the one owner.
- FR002 Record sequence/time/direction/outcome; distinguish complete write from partial/error
  uncertainty. Do not claim bytes were delivered just because write was attempted.
- FR003 Bound retained log by entries and payload bytes, expose omitted counters, and escape all
  wire/control text in a plain-text display. No automatic persistent logging or external upload.
- FR004 Preserve terminal log/query outcome after error/disconnect and start a new session on
  explicit reconnect. Clearing the view never performs device I/O or alters the job.
- FR005 Provide exact typed read-only query choices ?, $$, $G, $#, $N, $I; reject all other input.
- FR006 Admit one query only with fresh verified Idle, no active manual/job/settings/query and
  no tainted session. UI eligibility is rechecked by the communication owner before sending.
- FR007 Keep one ordinary ACK owner and process a whole received batch before releasing admission;
  duplicate/unsolicited/error/late ACK must not complete a different operation.
- FR008 Use a finite 3-second query deadline; route `?` through existing causal status polling with
  no duplicate outstanding poll. Because status replies have no request IDs, a status-poll timeout
  disables diagnostic console queries until explicit reconnect. No unbounded response accumulation
  or second serial reader.
- FR009 Treat query timeout, status-poll timeout, reset, framing/read/write failure, unit
  disagreement, or ambiguous ACK as a session fault. Retain evidence and require reconnect before
  further ordinary actions. A status-poll timeout specifically disables diagnostic console queries
  until reconnect because GRBL status replies have no request IDs.
- FR010 Stop/abort/close preempts pending query admission; existing owned worker join/retention
  behavior remains. Diagnostic queries never start motion, reset, home, unlock or output.
- FR011 Reuse existing layers, pins and Machine dock; validate Fake/Qt/desktop and full regression
  behavior without hardware. Existing streaming/dry/manual/preflight paths remain intact.

## Entities
ConsoleRequest: one exact supported command. ConsoleObservation: phase/command/outcome/eligibility.
WireRecord: immutable ordered timestamped direction/payload/write outcome/diagnostic/omitted bytes.
WireSnapshot: bounded retained tuple plus cumulative eviction/omission counters.
No stored profile, persistent log schema, raw command parser or generic terminal framework.

## Success criteria
- SC001 Every bounded simulated RX chunk and TX attempt has an accurate ordered record; partial/
  failed writes are never labeled complete, and no retry is issued.
- SC002 Retention remains <=512 records and <=256 KiB payload, each displayed record <=4096 payload
  bytes; omitted bytes/records are visible rather than silently represented as a complete log.
- SC003 Forbidden/concurrent queries emit zero bytes; supported ordinary queries own exactly one
  acknowledgement, with stale/duplicate/error cases quarantined until explicit reconnect.
- SC004 Console operations use the existing owner and its bounded shutdown; Qt controls keep
  control bytes inert, preserve final evidence and cannot bypass job/manual admission.
- SC005 Full Windows/architecture tests and actual desktop console plus prior workflows pass;
  physical delivery/controller compatibility is not inferred from simulation.

## Scope and hazards
This is a diagnostic terminal with a finite read-only command set. Arbitrary G-code/settings,
homing/unlock/reset/output commands would bypass existing reviewed/typed operation gates and are
outside this slice. Even read-only queries cannot share an untagged ACK stream with a running job.
A query timeout has an ambiguous late reply; reconnect is required instead of guessing/retrying.
Status reports also have no request IDs. After any status-poll timeout, keep console query controls
disabled until explicit reconnect restores causal attribution.
Opening a physical port may still reset equipment through its serial electronics. Raw RX is
transport evidence, not automatically trusted machine state. Logs stay local and bounded.
