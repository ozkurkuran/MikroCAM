# Validation: Auto-level Z compensation

## Requirement and constitution audit
| Coverage | Evidence |
| --- | --- |
| FR001-002 / SC001 | Complete-map-only flat/tilted/saddle/nonuniform edge/interior bilinear tests, explicit numeric bounds |
| FR003-006 / SC002 | mm/inch/absolute/incremental, rotated/mirrored G54 frames, CW/CCW/full circle/helix, cell curvature, output/dwell/end ancestry |
| FR007-008 / SC003 | Complete analytic arc extent, outside-map/rounded-radius rejection, cooperative subdivision cancel/output cap, warped-Z/rapid and float32 precision guards |
| FR009-011 / SC003-004 | Immutable input, obsolete worker suppression, map/source/settings/cancel/shutdown, board confirmation, current handoff, nonmodal file choice, protected atomic export |
| FR012 / SC005 | Desktop below, complete local suite and final-head Windows CI pending |

All eight constitution gates remain YES. No runtime dependency, copied source, new persistent
schema, new transport or legacy feature logic. New modules<=259 lines; maximum new function37
lines at initial implementation audit (AST checked). Legacy growth is zero.

Test-first evidence: missing surface/core modules caused two collection errors before
implementation; first US1 surface group35 passed before path generation. Missing bridge/UI
modules caused two errors before implementation; missing Preflight integration failed before
its hook. Combined preflight/dry-run/auto-level group202 passed in10.58s, followed by two
additional precision/incomplete-map cases within a24-case core run. There are77 new feature
cases across surface/core/files/UI. Core units use analytic expected values and reparse output.

Independent read-only design audit identified feed entry, within-cell-only midpoint guarantee,
arc radii, controller rounding, analytic arc coverage and output ordering; these were explicitly
resolved in plan/contracts and implementation. Follow-up geometry audit found no blocker;
export could overwrite input files. Four failing regressions reproduced this before protection
of resolved paths/hardlink identity. Input files now remain unchanged; separate output replacement
is still atomic and covered by failure cleanup tests. No external source code was copied.

## Actual desktop

CPython3.13.13, Windows actual desktop/OpenGL, `tests/smoke_app.py`: final run exit0 on
2026-10-01; log `.venv/autolevel-desktop-final.log`.
`AUTOLEVEL_MAP_ARC_SAVE_FAKE_COMPLETE_OK`: complete nine-point analytic plane, original
G2 semicircle plus linear cut, separate26-line output/22 executable blocks, fresh review,
explicit confirmation/transfer/Start and exact Fake completion at (2,2,5)mm.
`AUTOLEVEL_INPUT_FILES_PROTECTED_OK`: original loaded G-code and map destinations rejected
without byte changes. `AUTOLEVEL_CHANGED_INPUT_INVALIDATED_OK`: changed reference immediately
invalidates preview/save/transfer. Preparation emits no job/probe motion. Prior import/CAM/laser,
probe, preflight/job/jog/console/dry-run and active shutdown journeys still pass; `RENDER_OK`
and `SHUTDOWN_OK` emitted. Existing Qt size/teardown warnings do not fail assertions.

Inspected `.venv/autolevel-smoke.png`: loaded map simulated/complete provenance, G54 offset,
explicit settings/confirmation, original/map/derived hashes, bounds/time and numeric source-line
preview are readable without clipping. Smoke global watchdog grows85->120s for the added
map/arc/export/streaming journey; per-stage deadlines remain unchanged.
Initial snapshot-only desktop also passed. First enhanced file-source run failed only the
harness's LF-vs-Windows-CRLF comparison; final assertion now compares exact decoded input bytes,
matching the existing bridge's exact snapshot semantics. It then passed completely.

## Remaining delivery evidence
Complete local final-runtime suite, architecture/growth result, PR, final-head Windows CI and
merge pending. Physical CNC/probe/registration/clearance accuracy is not validated; surface
error describes emitted linear chords, with a separate XY arc approximation budget.
