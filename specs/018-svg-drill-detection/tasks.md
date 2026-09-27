# Tasks: SVG drill candidates

Input: spec/plan/research/data-model/contracts. Three stories, 36 tasks, tests first.

## Setup and foundations
- [x] T001 Research upstream behavior/license and host seams in research.md.
- [x] T002 Freeze spec, eight gates and bounded APIs in contracts/svg-drills.md.
- [x] T003 Write resolved white/currentColor/opacity tests in tests/test_svg_drill_paint.py.
- [x] T004 Add conservative fill fact to core/svg_models.py and importers/svg_style.py/svg_document.py.

## US1: inspect physical candidates
- [x] T005 [US1] Write immutable record bounds tests in tests/test_svg_drill_detection.py (finite abs<=1e9, positive diameter<=1e9, IDs 1..256, <=1000 candidates, <=200 notices).
- [x] T006 [US1] Implement frozen candidates/review in mikrocam/core/svg_drills.py.
- [x] T007 [US1] Write analytic circle/path, transformed metric/inch and negative shape tests in tests/test_svg_drill_detection.py.
- [x] T008 [US1] Implement exact primitive and bounded path circle evidence in mikrocam/core/svg_drills.py.
- [x] T009 [US1] Test white opening/nonwhite pad pairing, hidden/isolated/compound evidence in tests/test_svg_drill_detection.py.
- [x] T010 [US1] Implement pairing and bounded notices in mikrocam/core/svg_drills.py.
- [x] T011 [P] [US1] Write dialog load/error/plaintext and initial selection tests in tests/test_svg_drill_ui.py.
- [x] T012 [US1] Implement review dialog and bounded load adapter in mikrocam/ui/svg_drills.py and bridge/svg_drills.py.
- [x] T013 [US1] Add original analytic fixture and provenance in tests/reference/svg-drills.svg and docs/SVG_DRILLS.md.

## US2: create selected Excellon
- [x] T014 [P] [US2] Test exact unique integer selection, diameter spread<=0.01 and deterministic tools in tests/test_svg_drill_groups.py.
- [x] T015 [US2] Implement immutable DrillTool and grouping in mikrocam/core/drill_groups.py (<=1000 finite centres, positive diameter<=1e9).
- [x] T016 [US2] Test host MM/IN conversion, cancellation/failure atomicity and preserved source in tests/test_svg_drill_bridge.py.
- [x] T017 [US2] Implement complete initialized Excellon creation in mikrocam/bridge/svg_drills.py.
- [x] T018 [US2] Test real Excellon export/reparse/project fields in tests/test_svg_drill_bridge.py.
- [x] T019 [US2] Connect selected creation in mikrocam/ui/svg_drills.py and add small File/Import hook in appMain.py.
- [x] T020 [US2] Add real desktop create/export/project roundtrip in tests/smoke_svg_drills.py and smoke_app.py.

## US3: honest ambiguity and lifecycle
- [x] T021 [US3] Write duplicate/overlap/nonchained tolerance regressions in tests/test_svg_drill_detection.py.
- [x] T022 [US3] Implement deterministic duplicate/conflict exclusion in mikrocam/core/svg_drills.py.
- [x] T023 [US3] Test path/flip changes, failed reload, cancel and parent lifetime in tests/test_svg_drill_ui.py.
- [x] T024 [US3] Complete stale-state clearing and actionable notices in mikrocam/ui/svg_drills.py.
- [x] T025 [US3] Test source/curve/evidence caps and no partial candidates in tests/test_svg_drill_detection.py.
- [x] T026 [US3] Document heuristics/tolerances/export precision and genuine-sample limitation in docs/SVG_DRILLS.md.

## Validation and delivery
- [x] T027 Retain Neo MIT notice and immutable behavior trace in THIRD_PARTY_CHANGES.md and THIRD_PARTY_LICENSES/.
- [x] T028 Audit FR001–010/SC001–005 and gate/module/function bounds in validation.md.
- [x] T029 Add regression tests before any audit fixes in tests/test_svg_drill*.py.
- [ ] T030 Run full pytest/reference/growth checks at exact runtime head and record validation.md.
- [ ] T031 Run actual desktop all journeys via tests/smoke_app.py and inspect screenshot.
- [ ] T032 Record complete results and real Proteus/physical limitations in validation.md.
- [ ] T033 Update docs/ROADMAP.md and publish focused PR after017 delivery.
- [ ] T034 Verify final-head Windows CI and record its link/head in validation.md.
- [ ] T035 Merge validated head after017 and record PR/merge in validation.md.
- [ ] T036 Mark delivered tasks and roadmap without inventing physical/vendor validation.

Dependencies: frozen contract -> source paint facts -> US1 detector; grouping and thin UI can run
in separate files alongside detector after frozen records. Bridge/integration follows contracts;
all stories ship before validation. MVP is review, but creation and ambiguity are required delivery.
Root owns complex detector/integration/Git. Sol owns grouping and thin UI. Luna audits read-only.
