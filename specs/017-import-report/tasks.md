# Tasks: Import quality report

## Setup and shared contracts
- [x] T001 Review roadmap016/017 and existing source/selection/serialization seams in research.md.
- [x] T002 Freeze three stories and interfaces in contracts/import-report.md with eight plan gates.
- [ ] T003 Write root source-facts/flip preservation tests in tests/test_import_report_source.py.
- [ ] T004 Extend immutable source facts in core/svg_models.py and importers/svg_document.py; pass flip in bridge/svg_import.py.

## US1: truthful import facts
- [ ] T005 [US1] Write strict record and analytic measurement tests in tests/test_import_report.py.
- [ ] T006 [US1] Implement bounded records in mikrocam/core/import_report.py.
- [ ] T007 [US1] Test original units/viewBox/aspect, inferred dimensions, root mapping/flip in tests/test_import_report.py.
- [ ] T008 [US1] Implement result-only builder in mikrocam/core/import_report.py.
- [ ] T009 [US1] Test open/closed paths, atomic component validity, bounds and precision in tests/test_import_report.py.
- [ ] T010 [US1] Verify notices/truncation and limits without resampling in tests/test_import_report.py.

## US2: selected-object presentation
- [ ] T011 [P] [US2] Write widget plaintext/empty/error/reuse tests in tests/test_import_report_ui.py.
- [ ] T012 [US2] Implement read-only collapsed section in mikrocam/ui/import_report.py.
- [ ] T013 [US2] Write owning-object store/read and failed-import atomicity tests in tests/test_import_report_bridge.py.
- [ ] T014 [US2] Implement host boundary in mikrocam/bridge/import_report.py and optional owner in ui/svg_import.py.
- [ ] T015 [US2] Connect two host SVG seams to report ownership in camlib.py and appParsers/ParseGerber.py.
- [ ] T016 [US2] Test two-owner selection, no-report hide and invalid clearing in tests/test_import_report_ui.py.
- [ ] T017 [US2] Add minimal Properties attachment hooks in GeometryObject.py and GerberObject.py.
- [ ] T018 [US2] Verify historical label and no import/controller calls in tests/test_import_report_ui.py.

## US3: durable evidence
- [ ] T019 [P] [US3] Write schema1 codec and corrupt/version/size cases in tests/test_import_report_codec.py.
- [ ] T020 [US3] Implement strict codec in mikrocam/core/import_report_codec.py.
- [ ] T021 [US3] Write actual-object roundtrip and old-field migration tests in tests/test_import_report_persistence.py.
- [ ] T022 [US3] Add optional initialized report serialization fields in GeometryObject.py and GerberObject.py.
- [ ] T023 [US3] Verify malformed/newer records preserve usable object state in tests/test_import_report_persistence.py.
- [ ] T024 [US3] Extend actual desktop two-object report/save/reopen checks in tests/smoke_svg.py.

## Validation and delivery
- [ ] T025 Audit FR001–010/SC001–005 and eight gates; record evidence in validation.md.
- [ ] T026 Add regressions before audit fixes in dedicated tests/test_import_report*.py files.
- [ ] T027 Document historic report/units/precision/unavailable states in docs/IMPORT_REPORT.md.
- [ ] T028 Run full pytest including reference/import/growth at exact runtime head; record validation.md.
- [ ] T029 Run actual desktop report/lifecycle and all prior journeys using tests/smoke_app.py.
- [ ] T030 Inspect desktop evidence and record results/limitations in validation.md.
- [ ] T031 Update docs/ROADMAP.md and publish focused PR after016 delivery.
- [ ] T032 Verify final-head Windows CI and fix real failures, recording validation.md.
- [ ] T033 Merge only the validated head after016, record PR/CI links in validation.md.
- [ ] T034 Record completed delivery in tasks.md and docs/ROADMAP.md without claiming hardware tests.

Dependency order: source contracts/facts -> US1 -> US2 ownership; US3codec can run alongside widget
once records are frozen; persistence/desktop follows integration. Sol record+codec owner and Sol
widget owner may work in separate files. Root handles source facts/host integration and all Git.
MVP is truthful data, but all three stories must ship in this slice. No tests mirror implementation;
analytic geometry, old data, malformed data and actual lifecycle drive them. Total34tasks.
