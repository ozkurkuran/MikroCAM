# Tasks: safe-plane XY dry run

## Contracts
- [x] T001 Review the roadmap, constitution, existing Evo tools, and 013 seams.
- [x] T002 Freeze the spec, plan, lineage, output policy, quality criteria, and eight gates.
- [ ] T003 Write rejection, source-preservation, and numeric-setup tests first.
- [ ] T004 Implement finite, explicit dry Z, source binding, and the frozen result.

## US1: separate safe-plane source
- [ ] T005 Test XY preservation in millimetres/inches and absolute/incremental modes, plus the initial
      vertical retract.
- [ ] T006 Implement canonical filtering, preamble, and lineage while preserving original modes and
      leaving the source unchanged.
- [ ] T007 Test arcs, full circles, helices, and retained modal-only Z blocks.
- [ ] T008 Implement XY projection and the positive planar-path check.
- [ ] T009 Test removal of M3/M4/M7/M8/S, rejection of unknown commands and pauses, and output-off
      behavior.
- [ ] T010 Test, then implement, derived-report/PreparedJob proof and bounds, precision, and
      cancellation caps.

## US2: review and transfer
- [ ] T011 Write worker, cancellation, generation, source-change, and shutdown tests.
- [ ] T012 Implement a concrete, owned DryRunWorker.
- [ ] T013 Test blank height, review, provenance, bounded preview, and explicit-transfer UI.
- [ ] T014 Implement the dry-run panel and existing preflight entry point without port access.
- [ ] T015 Test, then implement, synchronous invalidation on original-source/height changes and
      pending-start cancellation.
- [ ] T016 Implement joined or retained dry-worker shutdown through preflight ownership.

## US3: established execution
- [ ] T017 Write a Fake full-job test proving the first move is Z-only, XY is unchanged, and output
      start is absent.
- [ ] T018 Integrate with the existing Machine-panel Start flow using only the derived binding and
      identity.
- [ ] T019 Test mismatched live position/G54 and forbid fallback to the source job.
- [ ] T020 Test that pause, resume, stop, and active close retain 013 ownership and failure evidence.

## Delivery
- [ ] T021 Review 11 FRs, 5 SCs, and eight gates; run tests before audit fixes.
- [ ] T022 Document operator-selected height/frame, lineage, restrictions, and physical clearance.
- [ ] T023 Run full pytest, import, growth, and size checks; record the head and counts.
- [ ] T024 Run a Fake dry run on the actual desktop and inspect the UI; preserve prior flows.
- [ ] T025 Update the roadmap and validation record, then publish a focused PR.
- [ ] T026 Verify final-head Windows CI and fix actual failures.
- [ ] T027 Merge the validated head.
- [ ] T028 Record delivery links and evidence-only completion.
- [ ] T029 Carry physical-validation limits forward.

Tests precede implementation; shared contracts precede delegation; each file has one owner. All
stories are required.
