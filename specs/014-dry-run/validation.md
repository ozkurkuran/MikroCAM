# Validation: safe-plane XY dry run

Status: delivered and merged; full local suite, actual desktop and final-head Windows CI passed.
Three stories and29 tasks. Dependency013 is merged; no new dependencies or legacy hooks.

## Requirements and constitution
FR001/005: exact original source/report reanalysis, immutable derived source and physical-line
lineage, with separate identities and generated-line markers. FR002/003: finite explicit machine
Z, upward-only first retract, fixed planar XY projection, original unit/distance/feed modes and
analytic helical/full-circle projection. FR004: output starts and S/T are removed only after
original semantics are validated; unknown/programmed-pause input blocks.
FR006: derived setup changes only safeZ and receives independent preflight/PreparedJob proof,
including numeric, duration, envelope and positive-XY checks. FR007/008: bounded200-line preview,
identity/bounds/time, synchronous original/height/close invalidation through pending Start.
FR009/010: owned cancellable worker, shared2s shutdown budget and retention, existing single
MachineController/Transport for execution. FR011 and all5 success criteria are covered by pure,
Fake, Qt, full-suite and actual desktop evidence below.

All eight gates remain yes: pure core/thin Qt UI, zero legacy growth, one concrete fixed-plane
policy, existing mm/Placement authority, tests first, explicit physical limits, existing MIT
source assessment without external code copy, three stories/29 tasks. Largest changed module
350lines; largest function48lines, within600/80.

## Tests first and audit
Core, execution and UI started with missing-module/API collection failures.
31 pure core tests cover strict setup/report/type/resource bounds, source preservation, source-name
safety, exact decimal generated Z, modes carried by removed Z-only lines, dwell, ordinary arcs,
helixes and explicit full circles.10 execution tests exercise the existing sender, correct G54/Z
mapping, initial vertical clearance, no output starts, live mismatches without source fallback,
pause/resume/stop and active close.14 Qt tests cover worker ownership, generation/cancel,
bounded preview/lineage, pending-Start invalidation, reused docks and retained/shared-budget close.

Luna's review added specific regressions for G20/G91/G1/F carried by a removed Z-only move,
G4P1S100 retaining dwell, full-circle planar travel and unsafe filename characters in generated
comments. Header uses a digest rather than raw filename; original name remains metadata.
One root integration assertion initially confused retained M30 with M3 by substring; it now
compares parsed words. A late Prepare event after shutdown was reproduced as a new worker;
the UI now checks its alive state in both button eligibility and the action handler.

Focused feature tests: **55 passed in0.68s**.
Full local suite at `e19dfa8c3c903bbd91550d583e2aa8503cb03591`:
`python -m pytest -q --junitxml=.venv/dry-run-pytest.xml`:
**2564 passed,2 skipped,11 warnings,310 subtests in207.90s**.
All55 new cases and architecture/import/growth checks are included.
Ignored local evidence: .venv/dry-run-pytest.log and .xml.
The two upstream empty Qt drafts remain skipped; existing SWIG/Shapely warnings remain.

## Actual desktop
At the same tested head, `python tests/smoke_app.py` exited0. The actual MikroCAM desktop prepared,
reviewed and transferred a cutting source into a distinct dry job. Its projected arc completed at
(2,1,8)mm with one initial Z movement and no spindle/coolant start words. A second160-move dry job
remained active for normal application shutdown, which retained ABORTED/stop-unverified evidence.

Markers: DRY_RUN_PROJECTION_COMPLETE_OK; DRY_RUN_ACTIVE_SHUTDOWN_READY;
JOB_ACTIVE_SHUTDOWN_OK; PREFLIGHT_SHUTDOWN_OK; MACHINE_SHUTDOWN_OK; SHUTDOWN_OK.
All prior CAM/project/laser/manual/preflight/streaming journeys passed in the same run.
Root inspected3840x2089 .venv/dry-run-smoke.png: machine/dry source identity, active accepted-block
progress, explicit Z8 and original/derived line preview visible.
Log: .venv/dry-run-smoke.log. Existing editor/QThreadStorage warnings remain; the arg-thread pipe
reported already closing (WinError232), followed by successful owned shutdown markers.

## Limits and delivery
[Operator guide](../../docs/DRY_RUN.md), [contract](contracts/dry-run.md).
Clearance and dry plane are operator-declared, not measured. This is real mechanical motion;
no physical collision, spindle power or stopping guarantee is inferred. Laser execution is not
provided. Firmware interpolation/steps remain outside the numeric representation guard.
[PR15](https://github.com/ozkurkuran/MikroCAM/pull/15) merged as `8458e6b92f06a51546025e474cd6439516faf8e9`.
[Windows CI](https://github.com/ozkurkuran/MikroCAM/actions/runs/36287355151) passed on final head
`785891f9cbbed6b7312eae2eb78f4cbade3ec923` in 6m29s. Physical-machine validation remains unperformed.
