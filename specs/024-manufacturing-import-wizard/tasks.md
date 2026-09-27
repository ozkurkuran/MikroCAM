# Tasks: manufacturing file set review

## Design and foundations
- [x] T001 Research existing drop/parser/factory semantics and format evidence in research.md.
- [x] T002 Freeze records, contracts and eight constitution gates in data-model.md, contracts/manufacturing-import.md and plan.md.
- [x] T003 Write strict record/review compatibility tests in tests/test_manufacturing_models.py.
- [x] T004 Implement immutable records in mikrocam/core/manufacturing_models.py.
- [x] T005 Write and implement strict report codec in tests/test_manufacturing_codec.py and mikrocam/core/manufacturing_codec.py.

## US1: bounded collection and inspection
- [x] T006 [US1] Write filename/content/metadata classification tests in tests/test_manufacturing_classify.py.
- [x] T007 [US1] Implement pure byte classifier in mikrocam/importers/manufacturing_classify.py.
- [x] T008 [US1] Write duplicate/path/size/read-error tests in tests/test_manufacturing_files.py.
- [x] T009 [US1] Implement bounded file inspection in mikrocam/bridge/manufacturing_import.py.
- [x] T010 [US1] Add and test multiple local drop/select rows in mikrocam/ui/manufacturing_import.py and tests/test_manufacturing_ui.py.

## US2: resolve and review
- [x] T011 [US2] Write conflicting metadata/filename, inner copper, PTH/NPTH and missing-unit regressions in tests/test_manufacturing_classify.py.
- [x] T012 [US2] Complete conservative proposals and evidence in mikrocam/importers/manufacturing_classify.py.
- [x] T013 [US2] Write compatible assignment/source-change/forged-inspection tests in tests/test_manufacturing_bridge.py.
- [x] T014 [US2] Implement fresh selected-file review in mikrocam/bridge/manufacturing_import.py.
- [x] T015 [US2] Test selected unresolved/error/name conflicts and review invalidation in tests/test_manufacturing_ui.py.
- [x] T016 [US2] Add editable assignment/evidence/review controls in mikrocam/ui/manufacturing_import.py.
- [x] T017 [US2] Verify licensed existing corpus layer proposals in tests/test_manufacturing_reference.py.

## US3: explicit per-file import and persistence
- [x] T018 [US3] Write compact Gerber/X2/macro/malformed-token tests in tests/test_gerber_statements.py.
- [x] T019 [US3] Implement bounded source statements in mikrocam/importers/gerber_statements.py.
- [x] T020 [US3] Write parser/factory/default/unit/source-guard/stop-order tests in tests/test_manufacturing_bridge.py.
- [x] T021 [US3] Implement guarded sequential factory receipt iterator in mikrocam/bridge/manufacturing_import.py.
- [x] T022 [US3] Test worker outcomes, stop/review/retry/no-repeat/close-lock in tests/test_manufacturing_ui.py.
- [x] T023 [US3] Add existing worker dispatch and explicit per-row outcomes in mikrocam/ui/manufacturing_import.py.
- [x] T024 [US3] Add tested optional report UI/persistence and short legacy hooks in mikrocam/ui/manufacturing_report.py, GerberObject.py, ExcellonObject.py and appMain.py.
- [x] T025 [US3] Test actual MM/IN parsing and source/report project roundtrip in tests/test_manufacturing_roundtrip.py.
- [x] T026 [US3] Add real desktop multi-drop/review/import/reopen journey in tests/smoke_manufacturing_import.py and tests/smoke_app.py.

## Audit and delivery
- [x] T027 Audit FR001–010/SC001–005 and all gates in validation.md.
- [x] T028 Add meaningful failing regressions before audit fixes in tests/test_manufacturing*.py.
- [x] T029 Verify old Gerber/Excellon/import reports and all previous behavior.
- [x] T030 Document supported classification, unit assumptions and per-file outcomes in docs/MANUFACTURING_IMPORT.md.
- [x] T031 Record independent implementation and existing corpus/license provenance in validation.md.
- [x] T032 Run focused/reference/architecture/growth checks and record validation.md.
- [x] T033 Run complete suite at final runtime head and record validation.md.
- [x] T034 Run actual desktop and inspect screenshot; record validation.md.
- [x] T035 Update docs/ROADMAP.md and publish focused PR after023 delivery.
- [x] T036 Verify final-head Windows CI and record validation.md.
- [x] T037 Merge validated head and record PR/CI/merge links in validation.md.
- [x] T038 Mark delivery in tasks.md/docs/ROADMAP.md, retaining limits.
- [x] T039 Confirm original source/default preservation and prior features remain covered.

Dependencies: strict records -> bounded classifier/files -> reviewed assignments -> bounded
statement boundary/normal factories -> worker outcomes and persistence -> actual full/desktop
validation. Tests precede implementation. US1 independently exposes a useful file inventory;
all three stories deliver the complete slice. Sol may own records/codec/UI and isolated classifier
files; root owns parser boundary, source/factory integration and Git. Luna audits read-only.
