# Validation: mechanical CNC job streaming
Status: full local suite, desktop and final-head Windows CI passed; merged.
Three stories/39 tasks; all10 quality checks. No new dependencies or legacy feature hooks.

## Requirements and constitution
FR001/004: immutable source/report reanalysis, canonical numeric spelling, pure G54 translation,
79-byte wire cap and float32 drift/extent guards. FR002/007: one controller owner, one ordinary
ACK owner and post-batch scheduling with duplicate/unsolicited/error regression tests.
FR003/005: current empty startup, mechanical settings/speed, G54/modal/zeroG92/TLO and initial
position proof; per-Start mechanical confirmation; no laser emission support.
FR006/008: accepted/source-line progress distinct from physical completion; final M5M9 ACK,
modal output-off readback and causal Idle endpoint. FR009: hold deceleration/stopped states,
explicit same-job resume including a dwell with its ACK still pending.
FR010/011/012: every-phase stop/disconnect, partial writes, reset/alarm/stale/malformed evidence,
no retries, retained uncertainty, manual lock until reconnect on faults.
FR013/014: bounded preparation/cancellation/line/deadline/ownership, ten real Qt sessions and
actual desktop Fake workflow. All5 success criteria exercised without physical hardware.

Eight gates remain yes: correct imports, zero legacy growth, one concrete policy/controller
collaborator, existing mm/Placement/source authority, tests first, explicit physical limits,
primary protocol facts without copied external implementation, three stories/39 tasks.
AST check: largest changed new-package module388lines, function52lines (limits600/80).
Architecture/import/growth checks are included in the full suite.

## Tests first and review findings
Core/model and UI work started with missing-API collection failures. Ninety-eight pure model/
preparation tests cover frozen derived inputs, exact reports, policy/limits and stable linear
spindle-speed inventory. Root domain/transport tests and46 additional adversarial tests cover
thirteen preparation/running/completion/pause stop boundaries, incomplete/duplicate queries,
fragmented/late ACK, source/final-off faults and long held dwell without replay.
Twenty-four UI/worker tests include10 real Qt/Fake job sessions and pending-planner-ACK pause/resume.

Substantive regressions were red before fixes:
-3 cases: first-write position recheck, late WCO drift and priority pause between guard/write.
-4 cases: large absolute float32 rounding, accumulated incremental drift, endpoint and arc envelope.
-2 cases: spontaneous controller Run or changed WCO while host was paused.
-2 cases: hold/resume write loss dropped job evidence; now retained through connection failure.
-1 case: failed live unit evidence could repopulate DRO using old scale; units remain unavailable.
UI regressions caught synchronous source-binding invalidation, closing identity and a stale Pause
exception; source changes now remove pending Start before owner admission under the same brief lock.
Luna re-read current source and found no remaining blocking state-machine issue. Wire payload cap
is deliberately one byte more conservative than stock GRBL.

Initial full run at7b5a5f28:2507passed/1failed/2skipped; failure was an older Fake exact-settings
expectation after intentional addition of $30/$31/$32. Both old exact settings fixtures updated.
Final full local suite at `e8d232073ebdc3217066667e2d0160eac57a30df`:
`python -m pytest -q --junitxml=.venv/streaming-pytest-final.xml`:
**2509passed,2skipped,11warnings,310subtests in200.72s**.
All223 new job tests are included. Ignored logs/XML:.venv/streaming-pytest-final.*.
Existing upstream empty Qt drafts remain skipped; SWIG/Shapely warnings remain.

## Actual desktop
`python tests/smoke_app.py` at `7b5a5f280f56015d5e77b85af97d8e015098f204` exited0.
It used the real MikroCAM desktop/panels/workers and FakeGRBL, never a physical port:
JOB_TRANSFER_COMPLETE_OK4; JOB_PAUSE_RESUME_STOP_OK; JOB_ACTIVE_SHUTDOWN_READY;
JOB_ACTIVE_SHUTDOWN_OK; PREFLIGHT_SHUTDOWN_OK; MACHINE_SHUTDOWN_OK; SHUTDOWN_OK.
Prior CAM/project/laser/manual/preflight journeys also passed. A later domain-only failure-path
unit invalidation fix is covered by the final full suite; UI/desktop workflow code is unchanged.
Root inspected3840x2089 .venv/job-smoke.png: explicit mechanical confirmation, accepted-block
progress, active source identity, manual lock and preflight transfer visible. Desktop log:
.venv/streaming-smoke.log. Existing editor signal/QThreadStorage shutdown warnings persist.

## Limits and delivery
[Operator guide](../../docs/JOB_STREAMING.md) and [wire/lifecycle contract](contracts/streaming.md).
No physical stop, spindle power, collision clearance or PCB result is certified. $32=0 does not
identify connected hardware. Output-off is controller-reported; feed hold can leave outputs on.
A broken cable cannot deliver stop. Numeric checks do not emulate firmware interpolation/steps.
Source ACK watchdog is conservative and may abort unusually slow operation; never replay.
[PR14](https://github.com/ozkurkuran/MikroCAM/pull/14) publishes this feature.
[Final-head Windows CI](https://github.com/ozkurkuran/MikroCAM/actions/runs/36286575852)
passed in6m15s at `564bfcc8f1866a624f44de99d65c6dadce257137`.
PR14 merged as `c76504a2e0e89881148e59ed3674cee93f60a3e1`; all39 tasks complete.
