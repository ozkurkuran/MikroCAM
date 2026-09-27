# Validation: G-code preflight

Status: local full-suite/desktop validation passed; final-head CI and merge pending.
Three stories/37 tasks, quality checklist10/10. No extension hooks or new dependencies.

## Requirements and constitution review
| Requirement | Evidence |
| --- | --- |
| FR001 | immutable source/digest and bounded UTF-8 bridge tests; no body fallback/mutation |
| FR002/003 | modal/linear/arc fixtures, units/feed retention, Placement rotation/mirror extrema |
| FR004/005 | explicit blank setup, initial/XYZ/rapid/feed checks with original source lines |
| FR006/007 | bounded200 findings plus total counters, partial bounds, unknown/nominal timing |
| FR008/009 | owned worker, generation/source/setup checks, cancellation and joined/retained close |
| FR010 | byte/line/token/value caps,100000-line performance fixture and cancellation checks |
| FR011 | selected-job/file desktop journey plus existing CAM/project/laser/manual flows |

SC001 analytic extents/time tested with1e-6 tolerances, SC002 unsupported/hazard cases blocked,
SC003 immutable source and stale result/owner tests, SC004100000-line analysis<10s and cancellation
<1s in the measured test, SC005 full Windows/desktop evidence below. All eight gates remain yes:
pure core and narrow bridge/thin UI; only11 legacy hook lines (appMain+6,appLifecycle+5), concrete
models/interpreter/worker without a generic framework, existing mm/Placement authority, tests
first without hardware, explicit conditional/no-send safety design, independent protocol facts
without copied source, three stories/37 tasks. No external application source was ported.

AST size checks at implementation head2985ee51: largest new module284 lines, largest function42;
all within600/80. No machine/serial dependency in preflight. Existing controller/menu behavior remains.

## Tests first and audit fixes
Models/source/lexer/motion/parser/worker/UI/shutdown tests began with missing implementation/API
failures. The interpreter initially passed28 cases and failed36: incomplete-program no-motion
reporting was corrected, and one test assertion was fixed to compare nested bounds per axis.

Substantive review regressions failed before fixes:
- Luna found near-zero angular center arcs could hide a GRBL full circle:3 failures; such ambiguous
  nonidentical endpoints now block, while exact full circles remain supported.
- Luna found G49 axis words could create fictitious motion:3 failures; G49 no longer carries axes
  or motion in this subset. T256 is also rejected to match the standard tool-number range.
- Sol adversarial tests found four decimal-rounding cases turning unsupported GM/integer NT words
  into accepted values and missing normalized-R limit enforcement:5 failures, then34 cases green.
- GUI tests caught late cancellation replacing newer source diagnostics, ambiguous old-source
  presentation after failed file load and a provider exception escaping the GUI callback; fixed.

Final focused command covering all ten test_gcode modules: **319 passed in7.83s** before the
last layout-only change. The100000-line fixture and10 real worker sessions are included.
No physical port or machine was opened. All supported source words are interpreted offline;
output commands remain report metadata, never transport writes.

## Desktop evidence
Actual desktop smoke at `2985ee510724212b50b889aa207bb0497c872d3e` exited0:
`python tests/smoke_app.py`. It generated a real GRBL_11_no_M6 CNC job, analyzed its complete
selected source and a byte-preserved file snapshot, and obtained identical allowed bounds over
1235 executable blocks. An unsafe-rapid file was blocked. Source text/body/file bytes remained
unchanged. A final owned analysis was left for normal application shutdown to cancel/join.

Markers: `PREFLIGHT_SELECTED_FILE_OK 1235`, `PREFLIGHT_HAZARD_OK`, `PREFLIGHT_SHUTDOWN_OK`,
`MACHINE_SHUTDOWN_OK`, `SHUTDOWN_OK`, with previous CAM/project/laser/manual checks retained.
Ignored local artifacts: `.venv/preflight-final-smoke.log`, `.venv/preflight-smoke.png`.
Root inspected the3840x2089 screenshot. Initial overly stretched input groups were compacted;
the dock received a stable object name, removing its new saveState warning. Existing Qt editor
signal/QThreadStorage warnings remain and are not described as warning-free shutdown.

## Limits and delivery
Report correctness is conditional on explicit initial position, Placement, envelope and zero
initial G92/TLO. Unknown semantics block; unknown time stays unavailable. This is not a full
GRBL emulator, collision simulation, controller/hardware compatibility test or execution approval.
Operator setup must be checked against actual hardware before later streaming. Details:
[operator guide](../../docs/GCODE_PREFLIGHT.md), [dialect contract](contracts/preflight.md),
[primary protocol research](research.md). No physical manufacturing result is claimed.

[PR#13](https://github.com/ozkurkuran/MikroCAM/pull/13) publishes the feature.
Full local suite at `2985ee510724212b50b889aa207bb0497c872d3e`: `python -m pytest -q --junitxml=.venv/preflight-pytest.xml` completed with **2286 passed,2 skipped,11 warnings,310 subtests in192.42s**. The complete suite includes architecture/import/growth checks and all319 new preflight cases. Logs/XML are retained locally under `.venv/preflight-pytest.*`. Existing SWIG/Shapely warnings remain. Final-head Windows CI/merge: pending.
