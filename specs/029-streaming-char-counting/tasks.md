# Tasks: Karakter sayımlı GRBL gönderimi
- [x] T001 Complete spec/clarification/research/plan and map FR001–012; analyze zero critical issues.
- [x] T002 Merge final implemented 028 dependency before queue integration.
- [x] T003 Write FIFO/capacity/mode tests first (FR001/002/003/005/006/007).
- [x] T004 Implement job_stream and immutable mode requests after red tests.
- [x] T005 Write multi-block coordinator/Fake tests first (FR003/004/005/006/010/011).
- [x] T006 Integrate selected source-only window, serialized capability and Fake RX FIFO.
- [x] T007 Test faults/late ACK/fragment/hold/priority/final/queue boundaries (FR006–011).
- [x] T008 Complete stop/quarantine/deadline/priority behavior after regressions.
- [x] T009 Write UI mode-intent tests before selector (FR002/012).
- [x] T010 Implement selectors on single job and queue, preserve default (FR001/002/012).
- [x] T011 Document algorithm/limits, extend actual desktop Fake journey (FR001–012).
- [x] T012 Related/full/architecture and actual desktop validation, validation.md/tracker.
- [ ] T013 Commit/push separate PR and require final-head Windows CI.

Dependencies T001→T002→T003→T004→T005→T006→T007→T008→T009→T010→T011→T012→T013.
Analyze: all12 FR map to tasks; no critical/high finding; existing final proof reused, no D scope.
Implementation checklist gate: requirements9/9 PASS; no extension hooks; .gitignore existing PASS.
