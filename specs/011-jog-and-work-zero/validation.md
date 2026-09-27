# Validation: Bounded jog and G54 work zero

Status: software delivered; final-head CI passed and PR merged. No physical hardware claim.
Three stories /33 tasks; all10 specification checklist items reviewed and complete.
No extension hooks are installed. Existing dependencies and layer boundaries remain unchanged.

## Analysis and coverage
| Requirement | Implemented evidence |
| --- | --- |
| FR-001/003, SC-001 | protocol/controller jog tests, exact presets/commands and causal endpoint |
| FR-002/004 | all-state gates, startup proof, output-off ACK/modal/fresh-status preparation |
| FR-005 | one transaction, post-batch scheduling, duplicate/late ACK and no replay |
| FR-006/007, SC-002 | selectG54/zero tests, full before/after parameter evidence and work coordinates |
| FR-008/009, SC-003/004 | every-phase cancel/abort/disconnect faults and worker priority/closure |
| FR-010/011 | typed intent-slot tests, singleton/session ownership and previous read-only suite |
| FR-012, SC-005 | full suite, architecture/growth/size, ten Qt cycles and actual desktop fake flow |

The eight constitution gates in plan.md have no planned exception. No application-side
persistent format or new dependency is introduced. Output-on commands cannot pass the shared
strict TX grammar. Startup blocks are inspected only; nonempty/unverified records block manual
actions. Stop fallback explicitly distinguishes verified-empty-startup reset from safety-door
with possible configured parking. Neither claims physical stop on a broken link.

Luna review confirmed standardGRBL G10L20 G92/TLO composition and `$13`-affected parameter units.
It identified the material reset/startup-macro hazard, now addressed in spec/plan/contracts.
Root also verified accessory state can be absent/intermittent, so it is not used as output-off
proof. Luna's implementation review caught Door being accepted as verified cancellation:
regression now requires causal Idle because Door can include configured parking. Root added
a second regression preserving failed-stop evidence across late ACK/cancel events.

## Implementation evidence
All code was independently written against documented protocol behavior. No new dependency,
application source port, legacy production hook or persistent application format was added.
The shared transmit validator admits only the specified read/manual grammar; output-start,
resume/home/unlock, startup assignments and arbitrary settings writes remain rejected.

Tests first: protocol started with missing-module failures, then seven invalid-grammar cases;
Fake started with20 failures; controller/zero/stop started with27 missing-API failures; serial
started with18 failures; worker/stop started with7 failures. Each was resolved by its scoped
implementation. The failed-stop-evidence regression also failed before its fix.

Focused results on Windows CPython3.13.13 x64:
- Protocol/Fake/serial:312 passed.
- Controller/zero/stop/adversarial:125 passed, including42 additional adverse cases.
- Worker/stop/previous UI:37 passed before the final failed-stop regression was added.
- New and existing Qt panel tests:30 passed in15.76s, including10 actual worker sessions.
- Architecture suite:83 passed in56.05s. This feature adds no legacy production lines.
- AST size check: largest new domain module356 lines; largest relevant function53 lines.
  All checked production modules/functions remain within600/80 limits.

Actual desktop smoke (runtime equivalent to4665cde2):
`python tests/smoke_app.py` exited0. It retained Gerber/Excellon, isolation/CNC, project
round-trip, laser preview/interlace/multipass/SVG+DXF export and rendering checks. It added
FakeGRBL G54 selection,0.1mm jog, persistentXY zero, cancellation and final worker disposal.
Markers: `MACHINE_READ_ONLY_OK`, `MACHINE_JOG_G54_CANCEL_OK (3.1,4.0,5.0)`,
`MACHINE_MANUAL_OK`, `RENDER_OK`, `MACHINE_SHUTDOWN_OK`, `SHUTDOWN_OK`.
Root and UI implementer visually inspected the3840x2089 screenshot: controls and stop buttons
fit the dock. Local ignored artifacts: `.venv/jog-smoke.log`, `.venv/machine-smoke.png`.
Existing Qt disconnect/QThreadStorage warnings occurred; this is not a warning-free claim.

All12 requirements and5 success criteria have corresponding tests above. The eight constitution
gates in plan.md hold: pure domain/owned bridge I/O/thin UI, no legacy growth, concrete single
operation rather than generic queue, mm normalization, tests first, explicit hazard/stop states,
independent protocol provenance, and three stories/33 tasks. Full-suite and final-head CI
results must be recorded below before delivery is declared complete.

## Limitations and delivery

Only FakeGRBL/mock serial was exercised. Actual travel, physical output-off, USB reset behavior,
parking configuration and physical stopping require hardware validation. A lost cable cannot
deliver a stop; reset may lose position; Door may park. Read-back is controller evidence only.
The selected step/feed caps are not machine-envelope/fixture-clearance checks; roadmap012
adds preflight, and013 adds job streaming. No automatic home/unlock/resume/recovery is provided.

Full suite, implementation/test tree equivalent to `b34319f5d4a62237b45808053fbc0bad8b1a6126`:
`python -m pytest -q --junitxml=.venv/jog-pytest.xml` completed with **1967 passed,
2 skipped,11 warnings and310 subtests passed in184.11s**. Output is retained locally in
`.venv/jog-pytest.log`/`.xml`;42 adversarial cases are included. Remaining warnings are existing
SWIG/Shapely deprecations. Documentation-only delivery updates follow this tested tree.

[PR #12](https://github.com/ozkurkuran/MikroCAM/pull/12) publishes the feature.
Final head `41c400a781647963ce0c605ce237c1b2e6d3ce68` passed [Windows CI run36282950060](https://github.com/ozkurkuran/MikroCAM/actions/runs/36282950060). PR#12 merged as `720c29b690afdbbe95f05b8f19c0777ba3939c5b`. All33 tasks are complete; this post-merge record changes documentation only.
