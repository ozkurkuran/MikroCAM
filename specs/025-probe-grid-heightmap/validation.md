# Validation: probe grid and height map

## Requirements and constitution

| Requirements | Evidence |
| --- | --- |
| FR001–003 | Strict Grid/Plan bounds, full route envelope, upward-first Z, live binding and edited-review UI tests |
| FR004–005 | Sole owner/factory/transport thread; typed intent; mechanical/setup gates; correlated PRB+ACK+fresh Idle, final retract |
| FR006–007 | Fault matrix, priority stop/close, late response deadline and unsolicited evidence quarantine; incomplete prefix retained |
| FR008–009 | Strict1MiB schema1 codec, atomic replacement/failure cleanup; numeric/heat-map view, offline historical-map retention |
| FR010 | Analytic mm/inch/G54-offset Fake, failure/worker/serial boundary and complete desktop below |

SC001–003 use independent analytic heights, final safe coordinates and exact complete/incomplete
persistence. SC004–005 require desktop/full/CI below. All eight constitution gates remain YES;
no new dependency, copied source, generic framework, new project format or legacy feature logic.
Probe wire commands have a distinct validated boundary on the existing real/Fake transports.
Largest modified production module472lines; all functions<=80lines at implementation audit.

## Test-first and audit evidence

Core/codec/files initially failed with missing modules, then120tests passed. The additional
incomplete outcome and strict codec cases brought this group to131tests. Protocol initially
failed missing-module collection; controller18cases failed missing request_probe before its
implementation. Worker tests initially rejected the new typed request. Production implementation
then passed799 combined probe and prior-machine tests in27.21s before final audit additions.

Meaningful red regressions preceded fixes for large integer validation, late ACK bypassing an
expired deadline, idle unsolicited PRB admission, and unchanged live results overwriting a loaded
historical map. Cached PRB from legitimate parameter queries remains separate and harmless.
Partial maps now carry incomplete until a terminal outcome; all measurements alone do not prove
the final retract succeeded. Luna independently audited protocol/controller/Fake and found no
remaining concrete safety blocker after the deadline fix; defensive idle quarantine was also added.

Final focused suite: 221 passed in 16.60 s. Runtime head:
`bedd649deb6d9fa03d5cc61c1a13e732030ca2a3`.

Roadmap work was paused on 2026-09-27 and resumed on 2026-09-28. Later commits on this branch
change documentation only; the runtime head above is unchanged.

## Complete suite and desktop

Local complete suite at the runtime head (2026-09-28): 5007 passed, 4 failed, 2 upstream
templates skipped, 11 existing warnings and 310 subtests in 1390.65 s. All four failures are
60 s subprocess timeouts in tests that start a fresh interpreter and import legacy application
modules: `test_runtime_compatibility.py::test_import_does_not_consume_test_runner_arguments`,
`test_excellon_merge_roundtrip.py` (METRIC-MM) and `test_svg_drill_bridge.py` (MM, IN). None
touches probe code. Unrelated applications kept the machine at 94–100 % CPU with 1.9 GB of
32 GB free; the run took 23 min against 4.7 min for 024, and the legacy-growth test alone took
about 7 min. Rerun in isolation, all seven variants of the four tests passed in 18.01 s (2–3 s
each). Architecture, legacy-growth, probe and prior machine tests passed in the complete run.
This local run is not counted as a passing complete suite; final-head Windows CI supplies that
evidence.

Actual desktop, same load: two runs exceeded the smoke's 85 s total watchdog before reaching
the probe journey. The first had completed seven journeys (startup, About, SVG drill, SVG,
import report, Illustrator, CAD source, geometry drill); the second stopped during startup. No
assertion failed, and neither run counts as a passing desktop run. The second run also showed
an existing harness defect: after the watchdog terminated the application pool workers, the
pool spawned a replacement that kept the log handle open until it was stopped manually.

Resumed actual desktop on 2026-10-01 using CPython 3.13.13 from
`E:/VSCode/Flatcam/MikroCAM/.venv/repro-a/Scripts/python.exe`: complete
`tests/smoke_app.py` passed (exit 0), within the unchanged 85 s watchdog.
Log: `.venv/probe-desktop-resumed.log`. Six analytic samples and final retract,
complete map offline roundtrip, priority stop with two preserved samples and incomplete
map roundtrip all passed. Existing import/CAM/laser, machine/jog/G54/console,
preflight/job/pause/resume/stop/dry-run and active-job shutdown journeys passed.
`RENDER_OK` and `SHUTDOWN_OK` were emitted. Inspected
`.venv/probe-grid-smoke.png`: all six numeric heights (0.00000..0.04000 mm),
physical grid coordinates, simulated/complete provenance and controls are readable.
Existing Qt window-size/teardown warnings did not fail assertions.

Resumed complete local suite on 2026-10-01 at delivery head
`d677dc2269dcaa6b00770658ce1815eac8a26d7b` (unchanged runtime): **5011 passed,
2 upstream templates skipped, 11 existing warnings, 310 subtests passed in 361.06 s**.
Command: shared CPython 3.13.13 `python -m pytest -q -rs` with
`QT_API=pyqt6`, `QT_QPA_PLATFORM=offscreen`, `PYTHONUTF8=1`.
Log: `.venv/probe-full-resumed.log`. Architecture and legacy-growth are included.
The four earlier timeout cases pass in this complete run.

Delivery PR: [#26](https://github.com/ozkurkuran/MikroCAM/pull/26).
Pending: final-head Windows CI and merge. Physical device validation remains open.


## PR review regressions (2026-10-01)

PR #26 identified small-coordinate Fake exponent notation, contact/stopped-position
conflation and a modal Save dialog blocking Stop during acquisition. Five targeted cases
failed before fixes (`.venv/probe-review-red.log`). Nine new regression variants now cover
small mm/inch reports, contact Z distinct from decelerated Idle Z, invalid stopped XY/Z,
and Save/Load exclusion during preparation, acquisition and pending Start.
Fake now formats decimal-only reports. Successful contact height remains the measurement;
fresh Idle must lie between contact and the reviewed minimum Z (within existing 0.005 mm
report tolerance), with matching XY and the reviewed machine envelope. Actual stopped
coordinates govern retract admission. Modal file controls are disabled while busy.

Focused probe/prior-machine/job/console/dry-run plus architecture/growth: **1312 passed in
109.94 s**, log `.venv/probe-review-focused.log`. Enhanced complete desktop passed (exit 0),
log `.venv/probe-review-desktop-final.log`: Fake stops 0.02 mm below contact while saved
heights still match the six analytic contact values, and Stop stays enabled with Save/Load
disabled during partial acquisition. Final probe screenshot inspected again; complete numeric
map and controls remain readable. Source semantics checked against GRBL primary
[probe monitor](https://github.com/gnea/grbl/blob/master/grbl/probe.c) and
[motion control](https://github.com/gnea/grbl/blob/master/grbl/motion_control.c);
no source code copied, no new dependency.

Earlier delivery-head CI passed at d677dc22 and a706f0dd; these precede the review fixes
and do not validate the final runtime. Final fixed-head Windows CI and merge remain pending.


## Final delivery

Final runtime/delivery head `7fbd39b883bc68621be55611e30a8f4bb8d58b07`:
complete local suite **5020 passed, 2 skipped, 11 existing warnings, 310 subtests passed
in 246.62 s** (`.venv/probe-review-full.log`, CPython 3.13.13).
[Final-head Windows CI](https://github.com/ozkurkuran/MikroCAM/actions/runs/36907928669)
passed: dependency consistency clean, **5020 passed, 2 skipped, 11 warnings,
310 subtests passed in 212.06 s**. Architecture and legacy-growth included.
Enhanced desktop and inspected screenshot at this same runtime are recorded above.
All three PR review findings were resolved after test-first fixes.

[PR #26](https://github.com/ozkurkuran/MikroCAM/pull/26) merged on 2026-10-01 as
[`01bb7413`](https://github.com/ozkurkuran/MikroCAM/commit/01bb74134ae80d9e7c71c87535e5ae82c5c9a5a5).
025 software delivery is complete. No physical probe/device validation is claimed;
Z compensation is feature 026. Earlier pending entries above are historical checkpoints,
superseded by this final delivery record.
