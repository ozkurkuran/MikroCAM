# Tasks: mechanical job streaming

## Shared
- [x] T001 Review roadmap/constitution/protocol facts and ownership seams.
- [x] T002 Freeze spec/plan/models/contracts, eight gates and quality checklist.
- [x] T003 Write pure snapshot/canonical/policy tests first.
- [x] T004 Implement immutable PreparedJob and exact source canonicalization.
- [x] T005 Test then implement JobObservation and confirmed Start intent.
- [x] T006 Test then extend real/Fake with separate validated job boundary.

## US1: exact reviewed job
- [x] T007 Write live admission tests for startup/settings/modal/offset/position/arbitration.
- [x] T008 Implement live preparation and fresh causal initial proof.
- [x] T009 Test exact block order and one ACK owner with interleaved status.
- [x] T010 Implement owner streaming/progress and post-batch scheduling.
- [x] T011 Test duplicate/unsolicited/error ACK and long dwell/planner waits.
- [x] T012 Implement bounded watchdog and fail-closed correlation.
- [x] T013 Test final ACK versus completion/output readback/endpoint mismatch.
- [x] T014 Implement final output-off and fresh endpoint proof.
- [x] T015 Test preparation worker/cancellation/stale result suppression.
- [x] T016 Implement owned preparation worker and explicit preflight transfer.
- [x] T017 Test then implement equipment confirmation/Start/progress/manual lock.

## US2: pause/resume
- [x] T018 Write deceleration/stopped/Idle and pending ACK hold tests.
- [x] T019 Implement priority pause and causal Hold:0/Idle proof.
- [x] T020 Test explicit resume/duplicate/stale/reconnect/alarm/door.
- [x] T021 Implement same-job resume and held-time watchdog accounting.
- [x] T022 Test then implement Qt pause/resume events and eligibility.
- [x] T023 Extend Fake queue/hold simulation with independent behavior tests.

## US3: stop/faults
- [x] T024 Write stop/abort/disconnect tests across every phase.
- [x] T025 Implement queue invalidation/reset/door and retained uncertainty.
- [x] T026 Test partial write/cable/reset/alarm/framing/stale/malformed evidence.
- [x] T027 Implement locked session and retained progress/diagnostic; no retry.
- [x] T028 Test priority arriving inside read/before write and stale starts.
- [x] T029 Implement pending typed intent/priority checks/source invalidation.
- [x] T030 Test ten Qt job/close cycles and owner retention on timeout.
- [x] T031 Implement joined workers and window retention.

## Delivery
- [x] T032 Audit14FR/5SC/eight gates; regressions precede substantive fixes.
- [x] T033 Document operator steps/restrictions/timing/physical limits.
- [x] T034 Full pytest/import/growth/size checks and exact head/counts.
- [x] T035 Actual desktop Fake job/pause/stop/completion smoke and UI inspection.
- [x] T036 Roadmap/validation and focused PR.
- [ ] T037 Final-head Windows CI; fix actual failures.
- [ ] T038 Merge validated head and record links.
- [ ] T039 Evidence-only completion and explicit hardware limits.

T001-T002 precede code; tests precede owned implementation. All three stories required.
Delegates edit disjoint files; root integrates.