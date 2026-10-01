# Tasks: Auto-level Z compensation

## Setup and foundations
- [x] T001 Freeze user scope/hazards in specs/026-autolevel-z-compensation/spec.md.
- [x] T002 Research/audit parser/frame/precision in specs/026-autolevel-z-compensation/research.md.
- [x] T003 Record eight gates and models/contracts in specs/026-autolevel-z-compensation/plan.md.

## US1: complete measured surface (MVP)
- [x] T004 [US1] Write analytic/interior/edge/exterior/incomplete/settings tests in tests/test_autolevel_surface.py.
- [x] T005 [US1] Implement exact complete-map bilinear/settings/cell helpers in mikrocam/core/autolevel_surface.py.

## US2: derived placed motion
- [x] T006 [US2] Write frame/units/feed/arc/saddle/rapid/precision/limit/cancel tests in tests/test_autolevel_core.py.
- [x] T007 [US2] Implement bounded line/cell/arc subdivision in mikrocam/core/autolevel_paths.py.
- [x] T008 [US2] Implement immutable result, semantics/lineage/frames in mikrocam/core/autolevel.py.
- [x] T009 [US2] Certify serialized/controller chords and fresh PreparedJob in mikrocam/core/autolevel.py.

## US3: current review and explicit handoff
- [x] T010 [US3] Write atomic export/failure tests in tests/test_autolevel_files.py.
- [x] T011 [US3] Implement separate atomic G-code export in mikrocam/bridge/autolevel_files.py.
- [x] T012 [US3] Write worker/map/settings/source/cancel/close/stale tests in tests/test_autolevel_ui.py.
- [x] T013 [US3] Implement cooperative worker in mikrocam/ui/autolevel_worker.py.
- [x] T014 [US3] Implement explicit map/settings/confirmation/preview/save/handoff in mikrocam/ui/autolevel_panel.py.
- [x] T015 [US3] Integrate opening and shutdown in mikrocam/ui/preflight_panel.py.
- [x] T016 [US3] Add desktop map/prepare/save/Fake completion/staleness in tests/smoke_autolevel.py.

## Audit and delivery
- [x] T017 Audit requirements/budgets and test-first fixes in specs/026-autolevel-z-compensation/validation.md.
- [x] T018 Document use/frame/approximation/physical limits in docs/AUTOLEVEL.md.
- [ ] T019 Verify focused/prior-machine/architecture/growth and full suite in specs/026-autolevel-z-compensation/validation.md.
- [x] T020 Verify desktop and inspect .venv/autolevel-smoke.png; record specs/026-autolevel-z-compensation/validation.md.
- [ ] T021 Publish PR and verify final-head Windows CI; record specs/026-autolevel-z-compensation/validation.md.
- [ ] T022 Merge validated head; record specs/026-autolevel-z-compensation/validation.md.
- [ ] T023 Update delivery tasks and docs/ROADMAP.md.

Dependencies: foundations -> US1 -> US2 -> US3 -> delivery. Validate the analytic US1 MVP
before path work; then validate full derived geometry before UI. Separate file export and UI
fixture authoring can proceed independently once US2 contract exists. Implementation remains
single-owner; read-only research audit was independent. All23 task entries have IDs and paths.
