# Tasks: Read-only GRBL connection

## Setup and contract
- [x] T001 Review constitution, roadmap, official GRBL/pyserial documentation and existing worker/shutdown integration in research.md.
- [x] T002 Freeze state, coordinate evidence, transport ownership and TX allowlist in data-model.md and contracts/read-only-grbl.md.
- [x] T003 Analyze spec/plan/tasks and record requirements coverage and all eight gates in validation.md before runtime changes.

## US1: Explicit connection and disconnection (P1)
**Independent test:** FakeGRBL connects, fails, disconnects and reconnects without any motion or persistent setting writes.
- [x] T004 [US1] Write lifecycle/allowlist/error/reconnect tests first in tests/test_machine_controller.py.
- [x] T005 [P] [US1] Write bounded framing and FakeGRBL tests first in tests/test_machine_grbl.py and tests/test_machine_fake.py.
- [x] T006 [US1] Add frozen lifecycle models and Transport Protocol in mikrocam/machine/models.py and transport.py.
- [x] T007 [US1] Implement deterministic read-only FakeGRBL in mikrocam/machine/fake.py.
- [x] T008 [US1] Implement incremental bounded ASCII framing in mikrocam/machine/grbl.py.
- [x] T009 [US1] Implement single-owner connect/disconnect/poll/settings lifecycle in mikrocam/machine/controller.py, including partial-write and close failure handling.
- [x] T010 [P] [US1] Write physical-port metadata/serial adapter tests first in tests/test_machine_serial.py; never open real ports.
- [x] T011 [US1] Implement SerialIO and metadata enumeration in mikrocam/bridge/serial_transport.py; reuse existing pyserial with fixed bounded timeouts.
- [x] T012 [US1] Validate exact allowed transmissions, one outstanding request, bounded diagnostics, timeout and reset settings transactions in controller tests.

## US2: Truthful machine and work coordinates (P1)
**Independent test:** Analytic MPos/WPos and mm/inch values agree; malformed, unknown, stale or obsolete evidence is never shown as valid coordinates.
- [x] T013 [US2] Write strict status/unit/state parsing tests in tests/test_machine_grbl.py before parser implementation.
- [x] T014 [US2] Implement pure status/settings parsing in mikrocam/machine/grbl.py with finite three-axis vectors and unknown state preservation.
- [x] T015 [US2] Write reset/unit-change/stale/missing-offset/order tests in tests/test_machine_controller.py before evidence implementation.
- [x] T016 [US2] Implement once-only mm normalization, current-session WCO and evidence invalidation in mikrocam/machine/controller.py.
- [x] T017 [US2] Validate malformed/oversized status, alarm and unknown state cannot preserve a fabricated safe state; record analytic results in validation.md.

## US3: Read-only machine panel (P2)
**Independent test:** Ten simulated panel sessions close without open transports/live workers; actual CAM desktop smoke remains successful.
- [x] T018 [US3] Write worker and panel lifecycle smoke tests first in tests/test_machine_ui.py, including close during connect and late old-session snapshots.
- [x] T019 [US3] Add concrete controller factory in mikrocam/bridge/machine.py and owned QThread in mikrocam/ui/machine_worker.py.
- [x] T020 [US3] Implement translated read-only panel in mikrocam/ui/machine_panel.py with explicit refresh/connect/disconnect, mm DRO and truthful unavailable state.
- [x] T021 [US3] Add lazy singleton menu and orderly application shutdown integration in appMain.py; keep legacy growth below +50.
- [x] T022 [US3] Run ten simulated lifecycles and verify stop/join bounds, exact writes and GUI-thread ownership in tests/test_machine_ui.py.
- [x] T023 [US3] Extend tests/smoke_app.py with simulated machine panel evidence, preserving real desktop CAM flow.

## Delivery
- [x] T024 Document usage, serial-open reset caveat and read-only disconnect meaning in docs/MACHINE_CONTROL.md and quickstart.md.
- [x] T025 Run full pytest, import/growth/size checks and actual desktop smoke; record exact commands/results in validation.md.
- [x] T026 Review all FR/SC coverage, eight constitution gates and no-new-dependency/license implications in validation.md.
- [x] T027 Update docs/ROADMAP.md with completed evidence, publish PR and verify Windows CI against the final head.
- [x] T028 Merge only the validated final head and update delivery links in validation.md.

## Dependencies and parallel work
T001-T003 precede runtime changes. Tests precede their implementation. Parser/models/Fake and
the serial adapter may be implemented independently against the frozen contract; controller
integration follows their contract tests. UI follows controller behavior and owns no protocol
logic. T024-T028 require all three stories. Root owns controller and integration, agents may
own disjoint parser/serial files. No physical machine is connected during automated validation.
