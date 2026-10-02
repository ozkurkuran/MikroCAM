# Feature Specification: Karakter sayımlı GRBL gönderimi

Feature Branch: 029-streaming-char-counting
Created: 2026-10-02
Status: Specified
Input: “c2, c3 tamamla. ilk aşamada grbl'in tam çalışması önemli.”

## User Scenarios and Testing

### US1 Explicit faster source mode (P1)
Operator selects character-counted sending for a reviewed GRBL 1.1 CNC job. Existing
send-response remains default. Source blocks may be buffered, but preparation and completion
are still independently verified. Independent test: run many short reviewed segments on Fake,
observe bounded concurrent outstanding blocks, ordered acceptance and final verified endpoint.
Acceptance: default starts keep one outstanding source block; explicit mode fills only available
RX space. Missing/malformed capacity evidence refuses source sending in the selected mode.

### US2 Accurate source attribution and faults (P1)
Operator sees which source line was accepted or failed even when several lines are outstanding.
Independent test: fragmented/coalesced ACKs and head error with multiple pending blocks.
Acceptance: only complete oldest-line responses retire bytes; status/push records release none.
Error shows the FIFO head source line, stops further writes, attempts existing safe reset and
quarantines restart. Already-buffered firmware motion is explicitly uncertain, not undone.

### US3 Hold, priority stop and queued completion (P2)
Operator can hold/resume/stop the active stream; queued next jobs never start on source ACK alone.
Independent test: pause between window writes, hold across deadline, resume or Stop at final boundary.
Acceptance: no refill after visible priority; held ACKs may retire old blocks, explicit resume
extends pending deadlines after fresh state proof. Stop/kopma/reset never replay. All final
outputs-off/modal/Idle/endpoint proof remains necessary before completion or next queue entry.

## Edge Cases
Exact-capacity fit and one-byte overflow; maximum source block; unknown/malformed OPT/VER;
coalesced/fragmented/duplicate ACK; status/MSG interleaving; error/alarm/banner/stale/USB;
partial/noninteger write; earliest pending deadline edge; planner saturation; long verified hold;
priority between two writes; full ACKs while machine still Run; final off/modal/Idle proof missing;
queue boundary, source binding changes, no hardware evidence of physical throughput.

## Requirements
- FR001: Send-response MUST remain the default and preserve existing source semantics/tests.
- FR002: Character counting MUST require explicit selection on immutable start intent; selection
  alone must not connect/start. Queued starts must carry the selected mode explicitly.
- FR003: Selected mode MUST verify GRBL 1.1 version and positive reported RX capacity through
  readonly $I evidence before any source, using at most 128 bytes and rejecting missing evidence
  or source blocks larger than the admitted capacity. No EEPROM/settings writes are added.
- FR004: Only source blocks MAY use the bounded window. Every preparation/final query remains
  serialized and final output-off/modal/fresh Idle/endpoint/G54 proof remains unchanged.
- FR005: Outstanding ordinary bytes MUST include exact canonical line terminator bytes. A
  complete block is sent only if its bytes fit; priority is checked before each handoff.
- FR006: One FIFO on the same communication owner MUST map ok/error to the oldest block and
  source line. Status/push/unterminated ACK give zero credit; duplicate unsolicited ACK fails.
- FR007: Each pending block MUST have an ACK deadline; expiry at/after the deadline stops the
  stream even if status stays fresh. No retry/replay on late ACK, partial/uncertain write or reset.
- FR008: Error/alarm/stale/USB/banner MUST stop further source, discard execution authorization,
  retain truthful failure/source attribution and attempt existing stop/reset without claiming
  all buffered motion was prevented. Reconnect must not restart.
- FR009: Hold MUST stop refill, retain byte/FIFO state, allow already-buffered ACKs, and explicit
  verified resume must preserve remaining deadlines. Priority wins between successive writes.
- FR010: All source blocks sent AND all their ACKs accepted are required before serialized final
  verification. Accepted counts are not physical completion; no next queue job starts early.
- FR011: FakeGRBL MUST cover bounded buffered/planner execution in FIFO order, faults, hold and
  endpoint proof without a physical port. Existing default-mode behavior remains protected.
- FR012: UI/docs MUST show selected mode and acceptance meaning, diagnose physical uncertainty,
  preserve existing workflows and state that real GRBL throughput/stopping requires H3 evidence.

## Key Entities
Streaming mode; verified GRBL RX capacity; pending source block with index/wire byte count/
ACK deadline; bounded source window; existing prepared job and source identity; job progress.
No additional communication owner, transport or generic scheduler is introduced.

## Success Criteria
- SC001: In every capacity/ACK/priority test outstanding bytes never exceed verified capacity.
- SC002: Every accepted/error response maps to exactly one correct source block; status and
  fragmented incomplete ACK release zero bytes; faults produce zero later source writes.
- SC003: Default mode has at most one outstanding source; selected mode demonstrates multiple
  outstanding short blocks and completes a >15-motion planner scenario in source order.
- SC004: Every tested stop/fault/reconnect produces zero automatic replay; all final evidence
  gates still prevent premature completion and queue advancement.
- SC005: Existing suites, actual desktop mode/queue journeys and final-head Windows CI pass.

## Assumptions and Scope
New explicit C3 completion instruction supersedes the earlier physical trigger for starting
software work; it does not certify measured throughput or grant hardware access. Scope is
GRBL 1.1 CNC serial, including bounded compilation RX differences up to conservative128;
FluidNC/grblHAL/network/SD remain separate deferred work. No outside firmware code is copied.
The mode is one per explicitly approved job/queue; runtime defaults remain send-response.

## Clarifications
2026-10-02: Existing roadmap defines explicit optional mode and default send-response. User
explicitly asks to complete C3 for GRBL first. Capacity discovered through readonly $I and
bounded to128 is an implementation design; no user-level ambiguity remains.

## Hazard Analysis
| Hazard | Control | Evidence |
| --- | --- | --- |
| RX overflow drops bytes and corrupts commands | Verified capacity, complete-line accounting | Exact-fit/overflow tests |
| Error leaves later blocks already buffered | Cut writes, reset attempt, quarantine and uncertainty | FIFO error/reset tests |
| Hold/Stop arrives during refill | Check priority every handoff; bounded owner cycle | Between-write priority tests |
| Source ACK is mistaken for completed motion | Existing serialized final proof retained | Run/off/modal/Idle tests |
| Unknown/custom firmware gives unsafe budget | Validate version/capacity, reject missing proof | Capability rejection tests |

No software test proves physical stop latency; H3 operator validation remains open.
