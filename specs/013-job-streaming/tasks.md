# Tasks: mechanical job streaming

## Shared
- [x] T001 Review roadmap/constitution/protocol facts and ownership seams.
- [x] T002 Freeze spec/plan/models/contracts, eight gates and quality checklist.
- [ ] T003 Write pure snapshot/canonical/policy tests first.
- [ ] T004 Implement immutable PreparedJob and exact source canonicalization.
- [ ] T005 Test then implement JobObservation and confirmed Start intent.
- [ ] T006 Test then extend real/Fake with separate validated job boundary.

## US1: exact reviewed job
- [ ] T007 Write live admission tests for startup/settings/modal/offset/position/arbitration.
- [ ] T008 Implement live preparation and fresh causal initial proof.
- [ ] T009 Test exact block order and one ACK owner with interleaved status.
- [ ] T010 Implement owner streaming/progress and post-batch scheduling.
- [ ] T011 Test duplicate/unsolicited/error ACK and long dwell/planner waits.
- [ ] T012 Implement bounded watchdog and fail-closed correlation.
- [ ] T013 Test final ACK versus completion/output readback/endpoint mismatch.
- [ ] T014 Implement final output-off and fresh endpoint proof.
- [ ] T015 Test preparation worker/cancellation/stale result suppression.
- [ ] T016 Implement owned preparation worker and explicit preflight transfer.
- [ ] T017 Test then implement equipment confirmation/Start/progress/manual lock.

## US2: pause/resume
- [ ] T018 Write deceleration/stopped/Idle and pending ACK hold tests.
- [ ] T019 Implement priority pause and causal Hold:0/Idle proof.
- [ ] T020 Test explicit resume/duplicate/stale/reconnect/alarm/door.
- [ ] T021 Implement same-job resume and held-time watchdog accounting.
- [ ] T022 Test then implement Qt pause/resume events and eligibility.
- [ ] T023 Extend Fake queue/hold simulation with independent behavior tests.

## US3: stop/faults
- [ ] T024 Write stop/abort/disconnect tests across every phase.
- [ ] T025 Implement queue invalidation/reset/door and retained uncertainty.
- [ ] T026 Test partial write/cable/reset/alarm/framing/stale/malformed evidence.
- [ ] T027 Implement locked session and retained progress/diagnostic; no retry.
- [ ] T028 Test priority arriving inside read/before write and stale starts.
- [ ] T029 Implement pending typed intent/priority checks/source invalidation.
- [ ] T030 Test ten Qt job/close cycles and owner retention on timeout.
- [ ] T031 Implement joined workers and window retention.

## Delivery
- [ ] T032 Audit14FR/5SC/eight gates; regressions precede substantive fixes.
- [ ] T033 Document operator steps/restrictions/timing/physical limits.
- [ ] T034 Full pytest/import/growth/size checks and exact head/counts.
- [ ] T035 Actual desktop Fake job/pause/stop/completion smoke and UI inspection.
- [ ] T036 Roadmap/validation and focused PR.
- [ ] T037 Final-head Windows CI; fix actual failures.
- [ ] T038 Merge validated head and record links.
- [ ] T039 Evidence-only completion and explicit hardware limits.

T001-T002 precede code; tests precede owned implementation. All three stories required.
Delegates edit disjoint files; root integrates.