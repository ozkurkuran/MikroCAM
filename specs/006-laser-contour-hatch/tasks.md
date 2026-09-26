# Tasks: Laser contour and hatch

## Foundation
- [X] T001 Review host representation/lifecycle in research.md and complete consistency analysis in validation.md.
- [X] T002 Write plain path/options tests in tests/test_laser_paths.py before core values.
- [X] T003 Implement validated values in mikrocam/core/laser_paths.py.

## US1: Contours
- [X] T004 [US1] Write analytic feature/outline/contour tests in tests/test_laser_geometry.py and tests/reference/laser_contour_hatch.json.
- [X] T005 [US1] Implement metadata/outline helpers in mikrocam/core/laser_features.py.
- [X] T006 [US1] Implement contour selection in mikrocam/core/laser_geometry.py.

## US2: Hatch
- [X] T007 [US2] Add test-first angled/cross/clipped/invalid/limit/cancel cases in tests/test_laser_geometry.py.
- [X] T008 [US2] Implement area selection and deterministic hatch kernel in mikrocam/core/laser_geometry.py.
- [X] T009 [US2] Add orchestration/one-placement tests in tests/test_laser_planner.py before domain implementation.
- [X] T010 [US2] Implement mikrocam/laser/__init__.py and planner.py.

## US3: Desktop preview
- [X] T011 [P] [US3] Write snapshot/owned-preview/unit tests in tests/test_laser_cam_bridge.py.
- [X] T012 [US3] Implement thin desktop adapter in mikrocam/bridge/laser_cam.py.
- [X] T013 [P] [US3] Add panel/worker smoke tests in tests/test_laser_cam_ui.py.
- [X] T014 [US3] Implement translated dock and cancellable worker in mikrocam/ui/laser_cam.py and laser_worker.py; wire one legacy menu action.
- [X] T015 [US3] Extend tests/smoke_app.py and run/inspect real desktop preview lifecycle.

## Delivery
- [X] T016 Run full suite/architecture/growth and size checks; record validation.md.
- [X] T017 Review hosted Windows CI and fix evidenced defects.
- [X] T018 Update docs/ROADMAP.md, quickstart.md and deliver PR after prior slices.

T001 precedes code; T002 before T003; T004 before T005/T006; T007 before T008;
T009 before T010. Bridge and UI tests/preparation can run independently against this contract,
but integration waits for core/domain. Root owns core/domain; separate agents own bridge and
UI. T015–T018 follow all stories. No overlapping writes to shared modules.
