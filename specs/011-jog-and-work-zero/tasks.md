# Tasks: Bounded jog and G54 work zero

## Setup and shared contracts
- [x] T001 Review official protocol, existing010 integration and constitution in research.md; explicitly resolve startup-reset and safety-door parking hazards.
- [x] T002 Freeze immutable request/query/observation APIs, limits and stop policy in data-model.md and contracts/manual-grbl.md; review all eight gates in plan.md.
- [x] T003 Write pure value/encoder/query/read-back tests first in tests/test_machine_manual_protocol.py: exact +/-0.1/1/10mm, feeds100/300/600, axesXY/Z/XYZ, finite mm values, complete unique inventories and tolerance0.005mm.
- [x] T004 Implement frozen values in mikrocam/machine/manual_models.py and ManualObservation in models.py; implement bounded encoders/parsers/verify_zero in manual_protocol.py without Qt/serial/global state.
- [x] T005 Write simulator tests first in tests/test_machine_manual_fake.py for modal/offset/jog/output-off/startup/cancel/abort behavior and transcript fidelity.
- [x] T006 Extend mikrocam/machine/fake.py with the concrete manual protocol and scripted adverse replies; keep010 read-only behavior intact.

## US1: One deliberate increment (P1)
**Independent test:** Each allowed +/- axis move completes at its mm endpoint; repeated or
forbidden requests send no new jog, regardless of parser/report units.
- [x] T007 [US1] Write tests/test_machine_manual_controller.py for admission, empty-startup proof, output-off preparation and every forbidden state before controller changes.
- [x] T008 [US1] Add concrete operation/transaction collaborator in mikrocam/machine/manual_control.py and typed request_manual entry point in controller.py; one ordinary ACK owner, no action queue.
- [x] T009 [US1] Add bounded provisional query inventories and post-batch command scheduling in manual_control.py; duplicate/unexpected/late ACKs taint the session instead of advancing unsent phases.
- [x] T010 [US1] Add query/report sequencing to controller.py and tests/test_machine_manual_controller.py so a pre-ACK status cannot verify an action.
- [x] T011 [US1] Implement startup-query -> M5/M9 -> modal verification -> fresh Idle -> one jog flow, including expected endpoint and30s completion deadline in manual_control.py.
- [x] T012 [US1] Validate exact byte transcripts, mm/inch/modal preservation, target mismatch, no auto-repeat and no emission-start in tests/test_machine_manual_controller.py.

## US2: Explicit G54 origin (P1)
**Independent test:** Select G54 deliberately; XY/Z/XYZ zero changes only chosen offsets and
is successful only after full read-back and fresh work coordinates.
- [x] T013 [US2] Write select/zero success and forbidden-state tests first in tests/test_machine_work_zero.py, including G92/TLO and inch reporting.
- [x] T014 [US2] Implement explicit SelectG54Request handling and modal/fresh-status verification in manual_control.py; connect/open never changes WCS.
- [x] T015 [US2] Implement pre-zero G54/modal/parameter evidence and one selected-axis G10 write in manual_control.py; no implicit defaults or retries.
- [x] T016 [US2] Clear WCO on accepted coordinate write, require complete after-inventory plus causal fresh WCO/work zero, and preserve omitted axes/otherWCS/G92/TLO in controller.py/manual_control.py.
- [x] T017 [US2] Verify missing/malformed/duplicate read-back, wrong active WCS, timeout/reset and ambiguous ACK never claim success or replay G10 in tests/test_machine_work_zero.py.

## US3: Priority cancel, abort and closure (P1)
**Independent test:** Every action phase can be stopped; queued intents disappear and failed
stop delivery remains visible through panel/application closure.
- [x] T018 [US3] Write tests/test_machine_manual_stop.py first for0x85, empty-startup-gated0x18, unknown-startup0x84, parking warning, loss/timeout/reset and close from every phase.
- [x] T019 [US3] Implement cancel_jog/abort and disconnect sequencing in manual_control.py/controller.py; cancel2s, ordinary ACK3s, stale2s, no automatic unlock/resume/home or startup assignments.
- [x] T020 [US3] Write updated transport grammar tests in tests/test_machine_serial.py before enabling bounded manual command bytes in mikrocam/bridge/serial_transport.py; retain mocked hardware boundary.
- [x] T021 [US3] Update serial transport to use the shared strict command validator and verify short-write/error propagation in tests/test_machine_serial.py.
- [x] T022 [US3] Write priority intent-slot, cancellation/close timing and old-session tests in tests/test_machine_manual_worker.py and tests/test_machine_manual_ui.py before worker/UI changes.
- [x] T023 [US3] Extend mikrocam/ui/machine_worker.py with one typed intent slot and priority stop/abort/cancel events, checked before action admission; close via controller's bounded stop path.
- [x] T024 [US3] Add thin translated mikrocam/ui/machine_controls.py with fixed step/feed selectors, +/-XYZ, G54 select/zero and cancel/abort; no repeating keys/raw command entry.
- [x] T025 [US3] Integrate controls/immutable operation diagnostics in machine_panel.py, including startup-on-connect caveat and4s retain-or-join shutdown.
- [x] T026 [US3] Run ten fake action/connect/close cycles and state-change-before-transmit scenarios in tests/test_machine_manual_ui.py; verify single I/O/GUI owners.
- [x] T027 [US3] Extend tests/smoke_app.py with FakeGRBL jog/G54/cancel evidence while retaining actual CAM/project/laser desktop flow and shutdown assertions.

## Delivery
- [x] T028 Document manual controls, persistent G54, output-off/startup gate, safety-door parking, reset position loss and physical-stop limits in docs/MACHINE_CONTROL.md and quickstart.md.
- [x] T029 Run full pytest, import/growth/size checks and actual desktop smoke; record commands, heads, counts and limitations in validation.md.
- [x] T030 Review all12FR/5SC and eight constitution gates in validation.md; audit exact supported TX grammar and absence of new dependency/source port.
- [x] T031 Update docs/ROADMAP.md with delivered evidence and publish a focused PR.
- [ ] T032 Verify Windows CI at the final full head; correct failures before merging.
- [ ] T033 Merge the validated head and record actual delivery links/checklist completion in validation.md.

## Dependencies and delegation
T001-T002 precede code; tests precede implementation. Shared protocol/model work and a separate
simulator test design can run independently against the frozen contract. Root owns controller,
manual transaction/stop integration and complex concurrency; Sol agents may own disjoint pure
protocol or thin UI files. US2/US3 depend on shared ownership/query sequencing fromUS1, and their
pure tests can be drafted earlier. All three stories are required before delivery. No physical
hardware or external application source is used in automated validation.
