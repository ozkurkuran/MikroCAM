# Implementation Plan: Read-only GRBL connection

**Branch**: `010-machine-connect-grbl` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

## Summary
Add an explicit read-only connection panel backed by a pure GRBL controller and injected
Serial/Fake transports. Show truthful mm machine/work XYZ only with valid unit/offset evidence.
Keep I/O and Qt separated, close owned resources, and expose no raw command or motion surface.

## Technical Context
- CPython 3.13 x64 / Windows 11; existing PyQt6 UI, stdlib controller and parser.
- Existing `pyserial==3.5` (BSD-3-Clause) is reused; no requirements or license addition.
- Tests: pytest, pytest-qt, deterministic FakeGRBL and mocked serial boundary; no real port opens.
- Persistence: none. No profile, project-format, registry, plugin framework or feature flag.
- Poll interval 250ms; status stale after 2s; settings response timeout 3s; serial read 50ms,
  write timeout 500ms. One outstanding status request and one read-settings transaction.
- Bound an incoming line at 512 bytes and one read at 4096 bytes; reject oversized/incomplete
  accumulation without allocating unbounded text. At most one pending settings transaction.

## Constitution Check
| Gate | Answer / evidence |
| --- | --- |
| I: new logic/layers | Yes. Pure `machine` imports stdlib/core only. Pyserial lives in one bridge leaf; Qt in UI. |
| II: legacy limit | Yes. Only a small lazy menu action in appMain, comfortably below aggregate +50. |
| III/VII: concrete abstractions/deps | Yes. Transport Protocol has SerialIO and FakeGRBL. Pyserial is already pinned/licensed. |
| IV: units/state/format | Yes. Wire units normalize once at the GRBL boundary. No duplicate placement transform or new persistence. |
| V: tests first/headless | Yes. Parser, lifecycle and transport tests precede code; Qt tests use fake I/O and settings sandbox. |
| VI: safety | Yes. Read-only allowlist and hazard analysis; disconnect from every state, no motion/emission introduced. |
| VII: external code | Yes. Independent implementation from official protocol documentation; no FlatCAM-Plus code or broad legacy port. |
| Feature size | Yes. Three stories, 28 tasks. |

## Project Structure
```text
mikrocam/machine/
  __init__.py             # inert
  models.py               # frozen snapshots and explicit lifecycle/machine state
  grbl.py                 # bounded strict wire parsing, units and coordinate evidence
  transport.py            # small stdlib Protocol, no backend registry
  fake.py                 # deterministic GRBL read-only simulator
  controller.py           # single-owner connection/poll/settings/freshness lifecycle
mikrocam/bridge/
  serial_transport.py     # existing pyserial adapter and side-effect-free port enumeration
  machine.py              # concrete controller construction for the UI
mikrocam/ui/
  machine_worker.py      # owned QThread and immutable snapshot signal boundary
  machine_panel.py       # widgets, explicit actions, singleton dock/shutdown wiring
```
No hardware dependency enters core or machine; using the bridge integration boundary avoids
changing the constitution or weakening the import guard. Do not copy ToolLevelling's probing
serial workflow, auto-wake/reset, port-opening scan or fake-success development branch.

## Ownership and Concurrency
The controller and its transport have one owner: the worker thread. The GUI requests stop via
a thread-safe event/interruption flag; it never calls controller or serial methods concurrently.
The worker closes in `finally` and emits its final immutable snapshot. The panel holds the
QThread until it has actually finished, joins with a bounded deadline, and does not destroy a
running thread if a driver violates its timeout. App shutdown must use the existing orderly
shutdown pattern. A simulated stalled read respects its configured bound and proves close timing.
No blocking serial calls or widget reads occur on the wrong thread.

## Implementation Strategy
1. Freeze the small state/transport/wire contract and test pure report validation, mm conversion
   and missing-offset behavior. Unknown state remains UNKNOWN with the original text.
2. Implement FakeGRBL and lifecycle against the exact read-only allowlist. Validate timeout,
   reset, short writes, malformed frames and freshness before adapting real pyserial.
3. Add a tested thin worker and panel, then the lazy menu hook. Verify all integration against
   fake I/O, ten lifecycle cycles, full suite and actual desktop CAM smoke.
4. Document serial-open reset caveat and the meaning of read-only Disconnect; no physical
   controller/machine success is claimed without a separate real-hardware observation.

## Complexity Tracking
No constitution exception. All new modules <=600 lines/functions <=80 lines; split along the
concrete responsibilities above if needed. No new runtime dependency and no transport registry.
