# Tasks: read-only console and wire diagnostics

## Shared contracts
- [x] T001 Review roadmap, constitution, existing Evo serial tools and current owner seams.
- [x] T002 Freeze query/log contracts and eight gates; complete quality checklist.
- [ ] T003 Write immutable record/snapshot bounds and ring eviction tests first.
- [ ] T004 Implement wire_log.py and console_models.py without I/O.

## US1: inspect communication
- [ ] T005 Test exact RX fragments and TX success/partial/error outcomes.
- [ ] T006 Instrument the one controller boundary and retain final log on failure/disconnect.
- [ ] T007 Test omitted counters, empty reads, oversized data and escaped control bytes.
- [ ] T008 Implement bounded log rendering and explicit local Clear view in ConsoleControls.
- [ ] T009 Test then integrate collapsed console into MachinePanel without new legacy hooks.
- [ ] T010 Test reconnect/new session and final evidence preservation through worker shutdown.

## US2: explicit diagnostic query
- [ ] T011 Write exact query/model/wire/Fake $I tests before extending permission.
- [ ] T012 Implement exact $I and typed supported query requests.
- [ ] T013 Test job/manual/settings/query conflicts and fresh Idle admission.
- [ ] T014 Implement concrete ConsoleControl and single-owner arbitration.
- [ ] T015 Test whole-batch ACK, duplicate/error/late reply, reset/alarm/stale framing and units.
- [ ] T016 Implement deadline, quarantine and retained outcome without retry.
- [ ] T017 Test causal ? scheduling without duplicate outstanding status requests.
- [ ] T018 Integrate typed query intent and priority cancellation in existing worker.
- [ ] T019 Test UI eligibility, no raw bypass and shutdown/failed-query evidence.

## Delivery
- [ ] T020 Audit11FR/5SC and eight gates; regressions precede substantive fixes.
- [ ] T021 Document query set, raw-chunk/outcome semantics, bounds and physical limits.
- [ ] T022 Run full pytest/import/growth/size checks and record tested head/counts.
- [ ] T023 Run actual desktop console plus existing flows and inspect UI.
- [ ] T024 Update roadmap/validation and publish focused PR.
- [ ] T025 Verify final-head Windows CI and fix actual failures.
- [ ] T026 Merge the validated head.
- [ ] T027 Record delivery links and evidence-only task completion.
- [ ] T028 Carry physical-machine limitations forward.

Tests precede implementation; all stories required. Delegated files have one owner and root
coordinates staging/commits to avoid a shared-index race.