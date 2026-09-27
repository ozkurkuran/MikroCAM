# Tasks: Reviewed Excellon merge

Input: spec, plan, research, data model and contracts. Three stories, 39 tasks. Tests precede code.

## Setup and shared foundations
- [x] T001 Inspect source authority, legacy merge/export hazards in research.md.
- [x] T002 Freeze exact fusion, bounded records/APIs and gates in contracts/excellon-merge.md and plan.md.
- [x] T003 Write drill/slot tool record and capsule-distance cases in tests/test_excellon_tools.py.
- [x] T004 Add ExcellonTool and final footprint validation in mikrocam/core/excellon_tools.py.
- [x] T005 [P] Write immutable source/map/review invariants in tests/test_excellon_merge_models.py.
- [x] T006 Add frozen records in mikrocam/core/excellon_merge_models.py.

## US1: review current selected sources
- [x] T007 [US1] Write MM/IN source authority/hash/invalid-input tests in tests/test_excellon_merge_bridge.py.
- [x] T008 [US1] Add snapshot_excellon and bounded selected owners in mikrocam/bridge/excellon_merge.py.
- [x] T009 [US1] Write exact diameter/order/tool-map tests in tests/test_excellon_merge_review.py.
- [x] T010 [US1] Implement deterministic physical inventory/map in mikrocam/core/excellon_merge.py.
- [x] T011 [US1] Test caps/empty/malformed tools and sources in tests/test_excellon_merge_bridge.py.
- [x] T012 [US1] Write fixed selected-source UI review cases in tests/test_excellon_merge_ui.py.
- [x] T013 [US1] Add source/tool/map presentation in mikrocam/ui/excellon_merge.py.

## US2: duplicates and blocking conflicts
- [x] T014 [US2] Write duplicate holes/reversed slots/nearby differences in tests/test_excellon_merge_review.py.
- [x] T015 [US2] Add exact first-representative deduplication in mikrocam/core/excellon_merge.py.
- [x] T016 [US2] Write crossing/parallel/tangent drill-slot-slot cases in tests/test_excellon_merge_review.py.
- [x] T017 [US2] Add bounded analytic conflicts and totals in mikrocam/core/excellon_merge.py.
- [x] T018 [US2] Test and display duplicates/conflict blocks in tests/test_excellon_merge_ui.py and mikrocam/ui/excellon_merge.py.

## US3: guarded separate Excellon
- [x] T019 [US3] Write slot factory/default/guard/failure tests in tests/test_excellon_operations_bridge.py.
- [x] T020 [US3] Generalize one factory body for slot-capable tools in mikrocam/bridge/excellon.py; retain old API.
- [x] T021 [US3] Write mutation/membership/forged-review regressions in tests/test_excellon_merge_bridge.py.
- [x] T022 [US3] Add exact fresh-review guards and creation in mikrocam/bridge/excellon_merge.py.
- [x] T023 [US3] Test explicit creation and failure outcomes in tests/test_excellon_merge_ui.py.
- [x] T024 [US3] Add creation UI and short Plugins hook in mikrocam/ui/excellon_merge.py and appMain.py.
- [x] T025 [US3] Test actual MM/IN drills/slots export/reparse and source preservation in tests/test_excellon_merge_roundtrip.py.
- [x] T026 [US3] Add selected-source desktop/export/project journey in tests/smoke_excellon_merge.py and tests/smoke_app.py.

## Audit and delivery
- [x] T027 Audit FR001–010/SC001–005 and all eight gates in validation.md.
- [x] T028 Add meaningful regressions before audit fixes in tests/test_excellon_merge*.py.
- [x] T029 Verify unchanged SVG/Geometry/shared-factory callers in tests/test_svg_drill*.py and tests/test_geometry_drill*.py.
- [x] T030 Document exact fusion, slot footprint policy, source authority and output precision in docs/EXCELLON_MERGE.md.
- [x] T031 Record independent implementation/source reuse in validation.md and docs/EXCELLON_MERGE.md.
- [x] T032 Run focused/reference/import-boundary/growth checks and record validation.md.
- [x] T033 Run complete suite at final runtime head and record validation.md.
- [x] T034 Run actual desktop all journeys and inspect screenshot for validation.md.
- [x] T035 Update docs/ROADMAP.md and publish focused PR after021 delivery.
- [x] T036 Verify final-head Windows CI and record validation.md.
- [x] T037 Merge validated head and record PR/CI/merge links in validation.md.
- [x] T038 Mark delivery in tasks.md/docs/ROADMAP.md with validation limits retained.
- [x] T039 Confirm sources and all prior delivered behavior remain covered in validation.md.

Dependencies: strict tool/source records -> authoritative snapshot/inventory -> duplicate/conflict
review -> guarded factory/UI creation -> actual host/desktop/full validation. US1 is the smallest
independently reviewable inventory; all three stories are needed for delivery. Sol may own shared
physical tool/factory and isolated record/UI files against these APIs; root owns merge geometry,
source fingerprint integration and Git. Luna audits read-only. No shared write ownership.
