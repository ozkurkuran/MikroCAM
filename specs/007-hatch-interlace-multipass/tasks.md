# Tasks: Interlace and multiple passes
## Foundation
- [X] T001 Review research/artifact coverage in validation.md before implementation.
## US1: Interlace
- [X] T002 [US1] Write N/order/multiset/cancel tests in tests/test_laser_interlace.py first.
- [X] T003 [US1] Extend PlanOptions in mikrocam/core/laser_paths.py and implement mikrocam/laser/interlace.py.
- [X] T004 [US1] Integrate ordering in mikrocam/laser/planner.py with existing placement tests.
## US2: Recipe editing
- [X] T005 [P] [US2] Write editor/roundtrip/atomic-save failure tests in tests/test_laser_recipe_ui.py.
- [X] T006 [US2] Implement mikrocam/ui/laser_recipe.py with strict existing models and codec.
- [X] T007 [US2] Integrate editor/save/interlace controls in mikrocam/ui/laser_cam.py and panel tests.
## US3: Planned passes
- [X] T008 [US3] Add pass-plan identity/order/settings tests before extending core LaserPlan.
- [X] T009 [US3] Implement LaserPassPlan/pass_plans in mikrocam/core/laser_paths.py; update panel status.
## Delivery
- [X] T010 Extend/run/inspect real desktop tests/smoke_app.py interlace/two-pass journey.
- [X] T011 Run full tests, architecture/growth/size checks and hosted CI; record validation.md.
- [X] T012 Update docs/ROADMAP.md and deliver feature PR after 006.

T001 gates code. T002 precedes T003/T004; T005 precedes T006/T007; T008 precedes T009.
One owner handles core/interlace/planner; another editor/panel. Both can proceed against the
contract. Root handles smoke and integration after both. No edits to existing recipe schema.
