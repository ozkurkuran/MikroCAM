# Implementation Plan: Mechanical CNC job streaming
Branch013-job-streaming;2026-09-27. Dependencies011/012 merged. Three stories,39 tasks.
Python3.13, existing pinned PyQt6/pyserial3.5; no new dependency or persistent format.

## Approach
Prepare an immutable CNC snapshot off the communication owner by independently recomputing
the reviewed preflight. Preserve original numeric spelling/source lines. One concrete JobControl
collaborates with existing MachineController; all bytes pass through its one transport.
One ordinary command outstanding; process the complete received batch before another block.
Status polling continues out-of-band. Live startup/settings/modal/parameter/position evidence gates
the first source block. Mechanical equipment confirmation is per Start; no laser operation.
Only pure translation matching actual G54 can stream. Existing Placement remains authoritative.
Pause/resume/stop use typed worker intents and thread-safe priority flags checked before writes.
Hold:1 is deceleration; Hold:0 stopped. Explicit resume never resumes Door/alarm. Stop clears host
queue and best-effort resets only with empty-startup proof; otherwise safety-door fallback warns
about parking/uncertainty. A lost cable cannot deliver a physical stop.

## Files and ownership
core/cnc_job.py and gcode_lexer.py: immutable preparation/canonicalization.
machine/job_models.py,job_control.py,job_preparation.py: concrete observations/proof/state.
machine/controller.py,manual_control.py,models.py: arbitration and retained failures.
machine/transport.py,fake.py and bridge/serial_transport.py: separate validated job boundary.
ui/job_controls.py,job_prepare_worker.py,machine_worker.py,machine_panel.py,preflight_panel.py:
thin transfer/prepare/confirm/start/progress and owned cancellation/shutdown.
tests/test_job_*.py; tests/smoke_job.py via existing desktop smoke.
Sol owns pure preparation or thin UI; root state machine/integration; Luna protocol audit.
Each file has one owner. Contracts are in contracts/streaming.md.

## Constitution Check
| Gate | Result |
| --- | --- |
| I layers | Yes: core pure; machine stdlib/core; bridge serial; UI Qt at top |
| II legacy | Yes: existing hooks reused; no planned legacy growth |
| III simplicity | Yes: one job/concrete collaborator, existing real/Fake; no queue framework |
| IV truth | Yes: existing Placement/mm/preflight; no alternate mapping/persistence |
| V tests first | Yes: domain/fault tests precede implementation; no physical hardware |
| VI safety | Yes: live proof, mechanical-only scope, priority stop/hold, truthful uncertainty |
| VII license | Yes: protocol facts only, no copied GRBL/FlatCAM-Plus implementation |
| VIII slicing | Yes:3 stories/39 tasks, modules<=600/functions<=80, public hints |

## Validation and complexity
Source binding/policy/limits, deterministic exact ACK ownership/all phase faults, long ACK waits,
pause/final proof, ten Qt cycles, full pytest/import/growth, desktop Fake and final-head Windows CI.
No constitution exception. Finite duration-derived source watchdog excludes explicit holds;
it is a conservative watchdog, not a physical timing guarantee. Queries3s/status freshness2s.