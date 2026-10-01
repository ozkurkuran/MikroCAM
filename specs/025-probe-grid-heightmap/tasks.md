# Tasks: probe grid and height map

## Design and US1
- [x] T001 Research current owner/protocol in research.md.
- [x] T002 Freeze spec, hazard analysis, models/contracts and eight constitution gates.
- [x] T003 [US1] Write grid/plan/map validation tests in tests/test_probe_map.py.
- [x] T004 [US1] Implement immutable records in mikrocam/core/probe_map.py.
- [x] T005 [US1] Write schema corruption/roundtrip tests in tests/test_probe_codec.py.
- [x] T006 [US1] Implement strict schema1 codec in mikrocam/core/probe_codec.py.
- [x] T007 [US1] Write review/edited-input binding tests in tests/test_probe_ui.py.
- [x] T008 [US1] Add explicit bounded grid/plan controls in mikrocam/ui/probe_controls.py.

## US2: one-owner acquisition
- [x] T009 [US2] Write typed request/observation tests in tests/test_probe_models.py.
- [x] T010 [US2] Implement records in mikrocam/machine/probe_models.py.
- [x] T011 [US2] Write narrow wire grammar/report-unit tests in tests/test_probe_protocol.py.
- [x] T012 [US2] Implement independent protocol in mikrocam/machine/probe_protocol.py.
- [x] T013 [US2] Write deterministic plane/Fake fault tests in tests/test_probe_fake.py.
- [x] T014 [US2] Implement mikrocam/machine/fake_probe.py and short Fake/transport hooks.
- [x] T015 [US2] Write preparation/admission/plane/sequence tests in tests/test_probe_controller.py.
- [x] T016 [US2] Implement single-owner coordinator in mikrocam/machine/probe_control.py.
- [x] T017 [US2] Add existing controller/snapshot/manual/job/console mutual-exclusion hooks.
- [x] T018 [US2] Write missing/duplicate/malformed/alarm/timeout/disconnect/stop tests in tests/test_probe_failures.py.
- [x] T019 [US2] Complete failure/taint/preserved-partial-map behavior in probe_control.py/controller.py.
- [x] T020 [US2] Write worker priority/lifecycle tests in tests/test_probe_worker.py.
- [x] T021 [US2] Add typed intent/priority handling to mikrocam/ui/machine_worker.py.
- [x] T022 [US2] Add progress/start/stop UI and small machine_panel.py dialog integration.

## US3: persistence and view
- [x] T023 [US3] Write bounded/atomic file I/O tests in tests/test_probe_files.py.
- [x] T024 [US3] Implement mikrocam/bridge/probe_files.py.
- [x] T025 [US3] Write missing/complete/map-view/offline tests in tests/test_probe_view.py.
- [x] T026 [US3] Implement height/numeric view and save/load UI in mikrocam/ui/probe_view.py.
- [x] T027 [US3] Add actual desktop Fake grid/save/load/stop journey in tests/smoke_probe.py and smoke_app.py.

## Audit and delivery
- [x] T028 Audit requirements/SC/constitution and independent protocol provenance in validation.md.
- [x] T029 Add failing regression before each audit fix in tests/test_probe*.py.
- [x] T030 Document frame, clearance, partial outcomes and physical limits in docs/PROBING.md.
- [x] T031 Verify focused/architecture/growth and prior machine behavior.
- [x] T032 Run full suite at final runtime head; record validation.md.
- [x] T033 Run actual desktop, inspect screenshot and record validation.md.
- [x] T034 Update docs/ROADMAP.md and publish focused PR after 024 delivery.
- [ ] T035 Verify final-head Windows CI.
- [ ] T036 Merge validated head and record PR/CI/merge links.
- [ ] T037 Update delivery tasks/roadmap while retaining physical validation limit.
- [x] T038 Verify complete/incomplete map persistence and no offline machine activity.
- [x] T039 Verify existing preflight/job/jog/console/import desktop journeys remain covered.

Tests precede implementation. Core models/codec precede typed protocol, coordinator and UI.
Root owns complex controller/protocol integration and Git. Sol can independently own core
records/codec/file I/O then isolated controls/view. Luna audits semantics read-only.
