# Tasks: İş kuyruğu

Input: spec.md, plan.md, research.md, data-model.md, contracts/ui.md.
Tests required by constitution and spec; each test task precedes its implementation.

## Setup and foundations
- [x] T001 Confirm existing B1/C1 integration, dependencies and tracker; no hardware.
- [x] T002 Complete spec/clarification, research agent and plan contracts (FR001–012).
- [x] T003 [US1] Write tests/test_queue_models.py for immutable snapshots, bounds, IDs and offline edits (FR001/002/010).
- [x] T004 [US1] Implement mikrocam/machine/queue_models.py after red tests (FR001/002/010).

## US1 Ordered prepared snapshots
- [x] T005 [US1] Write tests/test_queue_ui.py for snapshot sealing, candidate changes, order/edit exclusion (FR001/002/003/010).
- [x] T006 [US1] Implement mikrocam/ui/queue_controls.py and machine_panel.py hookup (FR001/002/003/010/012).

## US2 Automatic verified advancement
- [x] T007 [US2] Write tests/test_queue_control.py for three contiguous jobs, full per-job setup and every final boundary (FR004/005/006/007).
- [x] T008 [US2] Implement mikrocam/machine/queue_control.py and controller/models integration (FR004–007/011/012).
- [x] T009 [US2] Write tests/test_queue_worker.py for typed admission, initial approval and priority races (FR003/006/009/011).
- [x] T010 [US2] Integrate existing machine_worker.py typed queue intent, snapshot and stop/resume (FR003/006/009/011).

## US3 Faults, stop and ownership
- [x] T011 [US3] Extend tests/test_queue_control.py with C1 matrix, competing owners, hold/transition priority and reconnect results (FR008/009/011/012).
- [x] T012 [US3] Complete queue fault/quarantine/session lifecycle after red cases (FR008/009/011/012).

## Polish and validation
- [x] T013 Document snapshots/contiguous coordinates/automatic queue approval in docs/JOB_QUEUE.md; retain physical limitation (FR010/012).
- [x] T014 Add tests/smoke_queue.py in existing smoke_app.py; actual desktop screenshot, finish and stop journeys (FR001–012).
- [x] T015 Run related/architecture/full suites, inspect desktop, update validation.md and tracker (all FR).
- [ ] T016 Commit/push, make PR #32 ready and require final-head Windows CI; record evidence (all FR).

Dependencies: T001/T002 → T003 → T004 → T005/T007/T009/T011 → respective implementation
T006/T008/T010/T012 → T013/T014 → T015/T016. Shared runtime files edited sequentially.
US1 is testable offline; US2 with one queue on Fake; US3 independently injects owned faults.
No task authorizes hardware or ROADMAP completion edits before merge.
