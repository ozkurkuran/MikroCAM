# Tasks: Evo Python 3.13 baseline

## Phase 1 — Setup

- [x] T001 Audit Evo APIs, dependency resolution and test inventory in research.md.
- [x] T002 Record target interpreter in .python-version and create the isolated .venv.

## Phase 2 — Foundation

- [x] T003 Capture unmodified upstream test collection/results in validation.md before fixes.
- [x] T004 Add pytest.ini and test isolation in tests/conftest.py if required without excluding upstream tests.

## Phase 3 — US1: repeatable install and launch

Goal: a clean environment opens/closes the application with one command.
Independent check: clean install, pip check, three normal startup/shutdown cycles.

- [x] T005 [US1] Add import/CLI regression cases in tests/test_runtime_compatibility.py before changing appMain.py and flatcam.py (FR-001, FR-005).
- [x] T006 [P] [US1] Add optional-image regression tests in tests/test_optional_image_import.py before fixing appPlugins/ToolImage.py (FR-002, FR-004).
- [x] T007 [US1] Move import-time argument parsing to explicit startup in appMain.py and flatcam.py; preserve headless/shell options (FR-001, FR-005).
- [x] T008 [US1] Make raster/trace imports lazy and handle missing optional dependencies in appPlugins/ToolImage.py (FR-002, FR-004).
- [x] T009 [US1] Pin compatible runtime/dev and optional dependencies in requirements*.txt; record added dependency notices under THIRD_PARTY_LICENSES/ (FR-003, FR-004).
- [x] T010 [P] [US1] Add run-flatcam.ps1 with local interpreter validation and argument forwarding (FR-002, FR-005).

## Phase 4 — US2: reference CAM journey

Goal: Gerber/Excellon to saved/reopened CNC project and real rendering.
Independent check: tests/smoke_app.py uses isolated data/settings and exits successfully.

- [ ] T011 [US2] Adapt the legacy journey into tests/smoke_app.py, asserting object kinds/names, nonempty geometry/G-code and round-trip equality (FR-006, FR-007, FR-011).
- [x] T012 [US2] Add fixed fixtures/expected geometry under tests/reference/ and behavioral compatibility regressions before any parser/geometry fixes (FR-006, FR-008).
- [ ] T013 [US2] Fix reproduced runtime/parser/render/shutdown compatibility failures in their owning legacy files without new features (FR-005–FR-008).
- [ ] T014 [US2] Run and record three isolated desktop smoke cycles, screenshots and worker cleanup in validation.md (SC-002, SC-003).

## Phase 5 — US3: regression confidence

Goal: all existing and adapted tests pass without suppression.
Independent check: complete pytest inventory and explicit comparison to upstream.

- [x] T015 [US3] Complete all eight port behavior adaptations in tests/test_runtime_compatibility.py and document mapping in validation.md (FR-008).
- [ ] T016 [US3] Run the full upstream + new test suite; repair reproduced failures with preserved assertions and record counts/warnings in validation.md (FR-009–FR-011, SC-004).
- [x] T017 [US3] Verify second clean install and matching installed versions; record both pip checks in validation.md (FR-003, FR-004, SC-001).

## Phase 6 — Completion

- [ ] T018 Update README.md, CLAUDE.md, quickstart.md, docs/ROADMAP.md and validation.md with verified commands/results and limits (FR-010, FR-012).
- [ ] T019 Record imported files/commits/licenses in THIRD_PARTY_CHANGES.md and measured legacy growth/any justified exceptions in plan.md (FR-012, SC-005).
- [ ] T020 Verify checklist/spec/plan/tasks, clean diff and publish completed feature commits on 001-evo-py313-baseline (FR-012).

## Dependencies and parallel work

Setup → baseline capture → regression tests → corresponding fixes → complete validation.
US1 enables US2; US3 covers both. T006/optional-image edits and T010/launcher can run
independently while the coordinator handles appMain/flatcam and test collection. US2 smoke
preparation may run alongside compatibility regressions once the runtime contract is fixed.
US3 full pytest and second-environment install can run independently after code stabilizes.

## Implementation strategy

Deliver US1 first, then the CAM journey, then all regressions/reproducibility. No failed
test is removed/skipped to satisfy a gate. Update each task only after its evidence exists.
20 total tasks: setup 2, foundation 2, US1 6, US2 4, US3 3, completion 3.
