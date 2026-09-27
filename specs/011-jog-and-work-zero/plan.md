# Implementation Plan: Bounded jog and G54 work zero

**Branch**: `011-jog-and-work-zero` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

## Summary
Extend the existing single-owner GRBL controller with typed finite jog, explicit G54 selection
and verified axis-zero operations. Keep output-off preparation, one command transaction, causal
status/read-back verification and priority cancel/abort in the domain. UI sends bounded intent.

## Technical Context
- Existing Windows x64/CPython3.13, stdlib machine domain, pyserial bridge and PyQt6 UI.
- No new dependency, persistent application format, machine profile or generic queue framework.
- Standard GRBL1.1 XYZ; 0.1/1/10mm steps, 100/300/600mm/min feeds; hard caps10mm and600mm/min.
- Existing250ms polling/2s status freshness/512byte frames/4096byte reads remain.
- One ordinary command ACK at a time, 3s timeout; realtime polls/cancel/abort are separate.
- Jog completion deadline30s; cancel verification2s; UI shutdown waits at most4s before
  retaining a live worker. Serial calls retain50ms read and500ms write bounds.
- Report/read-back tolerance0.005mm, explicitly covering three-axis inch-report quantization;
  application command values remain exact decimal mm requests, not rounded controller reports.
- All validation uses FakeGRBL/mock serial. Physical travel/output-off behavior is not claimed.

## Constitution Check
| Gate | Answer / evidence |
| --- | --- |
| I: layers | Yes. Protocol/state/validation in machine, serial in bridge, Qt in UI. |
| II: legacy | Yes. Reuse010 menu/shutdown integration; no new legacy motion logic. |
| III/VII: abstraction/dependencies | Yes. Existing Transport real/fake pair, no dependency or generic command bus. |
| IV: one authority | Yes. Wire reports normalize once to mm; no placement clone or application persistence. |
| V: tests first | Yes. Domain encoders/parser/gates/transactions/cancel tests precede code, no hardware/Qt. |
| VI: safety | Yes. Hazard analysis, output-off preparation, state gates, bounded cancel/abort and loss-of-link uncertainty. |
| VII: provenance | Yes. Independent official-protocol implementation, no external application source port. |
| feature size | Yes. Three stories; task budget at most40. |

## Project Structure
```text
mikrocam/machine/
  manual_models.py        # frozen intents, operation phase/result and G54/modal evidence
  manual_protocol.py      # bounded command encoders and strict $G/$# evidence parsers
  manual_control.py       # concrete manual-operation collaborator owned by MachineController
  controller.py           # sole I/O owner; frame dispatch/query sequence/session invalidation
  models.py               # immutable published manual observation alongside existing DRO
  fake.py                 # deterministic jog/G54/output-off/cancel/abort simulator
mikrocam/bridge/serial_transport.py # allow only bounded supported command grammar
mikrocam/ui/
  machine_worker.py       # one bounded intent slot plus priority stop/cancel events
  machine_controls.py     # thin translated jog/G54/cancel/abort controls
  machine_panel.py        # wire controls to worker and immutable observation
```
Split helpers only along these concrete responsibilities; modules<=600/functions<=80.

## Operation and Acknowledgement Ownership
`MachineController` remains the only transport owner. A concrete manual-operation helper owns
one immutable requested action and its phase, never an unbounded queue. Settings acquisition
must complete before actions are admitted. Every line ACK has exactly one current command
owner. A next command is scheduled only after processing the whole received chunk, so duplicate
ACKs in that chunk cannot acknowledge an unsent next phase. Unexpected/late ACKs, incomplete
read-back and ambiguous writes taint manual control until an explicit reconnect.

Each valid status report records the sequence of the outstanding query it answers. Verification
requires a query issued after the triggering ACK/cancel; a previously outstanding query/status
cannot complete a new phase. Existing single-outstanding status logic drains that reply first.
Unsolicited position reports may update DRO but do not prove action completion. Recheck live
Idle/current units/positions and the absence of another transaction immediately before writes.

## Jog Flow
Validate axis/distance/feed first, then reserve the sole operation slot. Send `M5 M9` and await
ACK; query `$G`, require a complete successful response with M5 and M9. Require a fresh queried
Idle position after that verification before sending one `$J=G21 G91 <axis><distance> F<feed>`.
Capture its expected endpoint from that fresh mm position. ACK means accepted, not complete;
require a later causal Idle report at the expected endpoint before completion. Any forbidden
state, malformed evidence, timeout or reset fails/locks the operation. No next jog is queued.

Accessory `A:` absence is not treated as proof that outputs are off: the official field is
intermittent and can be compiled out. Accepted explicit M5/M9 plus modal read-back is controller
command evidence, not physical power feedback. No emission-start command exists in the grammar.

Before every manual action, read `$N` and require both unique `$N0=`/`$N1=` rows to be empty
and ACKed. This is an admission check, not a startup-block editor. Keep that session proof for
abort selection; invalidate it on reset, corrupt framing and disconnect. This extra phase also
precedes G54 selection and zeroing. Nonempty/unknown records reject the operation without writes.

## G54 Flow
Use G54 is an explicit separate action: fresh Idle -> `G54` ACK -> `$G` verifies G54 -> fresh
status. It does not zero anything. Zero XY/Z/XYZ requires active G54 verified by `$G`, plus a
completed `$#` read containing G54, G92 and TLO. Capture fresh MPos and work coordinates.
Send exactly one `G10 L20 P1` with only the chosen zero-valued axes. Do not alter parser units,
distance mode, G92, TLO or other work systems. On ACK invalidate cached WCO immediately.
A new completed `$#` read must show selected G54 axes equal to MPos-G92-(TLO on Z), with omitted
G54 axes unchanged; then a causal status with fresh WCO must show selected work axes zero and
omitted work coordinates unchanged within0.005mm. No auto-retry of the persistent G10 write.

## Cancellation, Abort and Worker Closure
Cancel jog uses only realtime0x85, preempts queued intents and waits for a causal nonmoving
Idle/Door report; Door stays locked. A missing/invalid cancel result after2s invokes best-effort
abort0x18 only with verified empty startup-block evidence and retains stop-unverified evidence.
Abort from any connected state invalidates pending operations/positions/units. It sends0x18
only with that proof; otherwise it sends safety-door0x84 with an explicit stop-unverified and
possible-controller-parking diagnostic. It requires explicit recovery and never resumes,
unlocks or homes. Stale status/I/O/ACK failure during an owned action attempts abort before
closing when the channel permits a write. If it cannot be delivered/verified, show that fact.

Disconnect/close during motion invokes this bounded cancellation path in the I/O owner rather
than ending its loop before stop attempts. Idle read-only disconnect retains010 semantics.
A thread-safe intent slot holds at most one action; cancellation/abort/disconnect invalidate
that slot before action processing. GUI state changes do not bypass the domain's last-moment
gate. Retain/join a thread that violates its timeout rather than destroying it.

## Validation and Delivery
Pure tests cover all state gates, exact typed commands, units/offset composition, every phase's
fault/reset/late-ACK/cancel behavior and no write replay. Qt tests cover intent priority, no
repeat, output/position diagnostics and ten lifecycles. Extend real desktop smoke with FakeGRBL
jog/G54/cancel only, preserve CAM flow, then full suite/architecture/Windows CI and exact-head PR.

## Complexity Tracking
No exception planned. The manual helper is a concrete responsibility split, not a new backend
interface or framework. Physical interlock/stop limits are disclosed; no disconnected software
can claim successful physical stopping.
