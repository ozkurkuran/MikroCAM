# Tasks: read-only console and wire diagnostics

## Shared contracts
- [x] T001 Review the roadmap, constitution, existing Evo serial tools, and current owner seams.
- [x] T002 Freeze query/log contracts and eight gates; complete the quality checklist.
- [x] T003 Write immutable record/snapshot bounds and ring-eviction tests first.
- [x] T004 Implement `wire_log.py` and `console_models.py` without I/O.

## US1: inspect communication
- [x] T005 Test exact RX fragments and TX success/partial/error outcomes.
- [x] T006 Instrument the single controller boundary and retain the final log on failure/disconnect.
- [x] T007 Test omitted counters, empty reads, oversized data, and escaped control bytes.
- [x] T008 Implement bounded log rendering and an explicit local **Clear view** in `ConsoleControls`.
- [x] T009 Test, then integrate the collapsed console into `MachinePanel` without new legacy hooks.
- [x] T010 Test reconnect/new-session behavior and final-evidence preservation through worker
      shutdown.

## US2: explicit diagnostic query
- [x] T011 Write exact query/model/wire/Fake `$I` tests before extending permission.
- [x] T012 Implement exact `$I` and typed requests for the supported queries.
- [x] T013 Test job/manual/settings/query conflicts and fresh-Idle admission.
- [x] T014 Implement concrete `ConsoleControl` and single-owner arbitration.
- [x] T015 Test whole-batch ACK, duplicate/error/late reply, reset/alarm/stale framing, and units.
- [x] T016 Implement the deadline, quarantine, and retained outcome without retry.
- [x] T017 Test causal `?` scheduling without duplicate outstanding status requests, including
      reconnect-required behavior after a status-poll timeout.
- [x] T018 Integrate typed query intent and priority cancellation in the existing worker.
- [x] T019 Test UI eligibility, no raw bypass, and shutdown/failed-query evidence.

## Delivery
- [x] T020 Audit 11 FRs/5 SCs and eight gates; regressions precede substantive fixes.
- [x] T021 Document the query set, raw-chunk/outcome semantics, bounds, and physical limits.
- [x] T022 Run full pytest/import/growth/size checks and record the tested head/counts.
- [x] T023 Run the actual desktop console with existing flows and inspect the UI.
- [x] T024 Update the roadmap/validation record and publish a focused PR.
- [x] T025 Verify final-head Windows CI and fix actual failures.
- [x] T026 Merge the validated head.
- [x] T027 Record delivery links and evidence-only task completion.
- [x] T028 Carry physical-machine limitations forward.

Tests precede implementation; all stories required. Delegated files have one owner and root
coordinates staging/commits to avoid a shared-index race.
