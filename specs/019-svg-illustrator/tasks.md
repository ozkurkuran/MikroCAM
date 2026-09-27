# Tasks: Illustrator SVG appearance

Input: spec/plan/research/data-model/contracts. Three stories,39tasks; tests first.

## Setup and source records
- [x] T001 Research Neo/standards/current importer and record limits in research.md.
- [x] T002 Freeze eight gates and APIs in contracts/illustrator-svg.md.
- [ ] T003 Write clip/layer/effective-root record bounds in tests/test_svg_illustrator_models.py.
- [ ] T004 Add SvgClip (<=64shapes), clips<=8, layer_path<=64 and viewport_attributes to core/svg_models.py.

## US1: physical page and visible layers
- [ ] T005 [P] [US1] Write namespaced XMP units/ambiguity/fallback tests in tests/test_svg_illustrator_metadata.py.
- [ ] T006 [US1] Implement bounded effective page attrs in mikrocam/importers/svg_metadata.py.
- [ ] T007 [P] [US1] Write simple selector/inline/important precedence and limits in tests/test_svg_illustrator_css.py.
- [ ] T008 [US1] Implement <=65536char/256selector cascade in mikrocam/importers/svg_css.py.
- [ ] T009 [US1] Test hidden layers/child visibility/use and original tokens in tests/test_svg_illustrator_document.py.
- [ ] T010 [US1] Integrate metadata/cascade/layer evidence in mikrocam/importers/svg_document.py.
- [ ] T011 [US1] Write percent-token/schema1 migration/schema2 rejection cases in tests/test_svg_illustrator_report.py.
- [ ] T012 [US1] Update report builder/codec in mikrocam/core/import_report.py and import_report_codec.py.
- [ ] T013 [US1] Retain existing report/host behavior through tests/test_import_report*.py.

## US2: compound fill intent
- [ ] T014 [US2] Write overlapping/touching/selfcrossing winding fixtures in tests/test_svg_illustrator_fill.py.
- [ ] T015 [US2] Extract unchanged simple nesting into mikrocam/core/svg_fill.py.
- [ ] T016 [US2] Implement bounded polygonized winding and svg_paint.py delegation.
- [ ] T017 [US2] Test <=2048segments/32768pairs/2048faces/2000000 winding operations in tests/test_svg_illustrator_fill.py.
- [ ] T018 [US2] Verify orientation/implicit closure/unchanged paths and reference behavior in tests/test_svg_illustrator_fill.py.

## US3: local clipping
- [ ] T019 [US3] Write definition/source-style/reference/chain tests in tests/test_svg_illustrator_document.py.
- [ ] T020 [US3] Add noninherited clip-path and inherited clip-rule in importers/svg_style.py.
- [ ] T021 [US3] Implement bounded local clip expansion in importers/svg_document.py (split helper if needed).
- [ ] T022 [US3] Write analytic clip/frame/group-bbox/flip/union/intersection tests in tests/test_svg_illustrator_clip.py.
- [ ] T023 [US3] Implement application matrix, physical intersections and budgets in core/svg_clip.py.
- [ ] T024 [US3] Render local definition paths at physical tolerance and apply clips in bridge/svg_import.py.
- [ ] T025 [US3] Test and exclude clipped source circles from drill inference in core/svg_drill_circles.py and tests/test_svg_illustrator_clip.py.
- [ ] T026 [US3] Test invalid/empty/oversized clips and failed host import atomicity in tests/test_svg_illustrator_clip.py.
- [ ] T027 [US3] Add original authored fixture/provenance in tests/reference/svg-illustrator.svg.
- [ ] T028 [US3] Extend actual desktop report/source/save/reopen in tests/smoke_svg_illustrator.py and smoke_app.py.

## Validation and delivery
- [ ] T029 Audit FR001–010/SC001–005 and eight gates in validation.md.
- [ ] T030 Write regressions before audit fixes in tests/test_svg_illustrator*.py.
- [ ] T031 Record supported CSS/XMP/clip/winding semantics in docs/SVG_IMPORT.md.
- [ ] T032 Update schema migration guide in docs/IMPORT_REPORT.md.
- [ ] T033 Record immutable Neo source/license/adaptation in THIRD_PARTY_CHANGES.md.
- [ ] T034 Run full/reference/architecture/growth suite at final runtime head and record validation.md.
- [ ] T035 Run actual desktop all journeys via tests/smoke_app.py and inspect screenshot.
- [ ] T036 Update roadmap and publish focused PR after018 delivery.
- [ ] T037 Verify final-head Windows CI and record validation.md.
- [ ] T038 Merge only validated head; record PR/CI/merge links in validation.md.
- [ ] T039 Mark delivery in tasks.md/docs/ROADMAP.md, preserving genuine-sample/physical limits.

Dependencies: records/contracts -> metadata/styles and compound core in parallel separatefiles;
source traversal + clip geometry -> bridge integration -> report/desktop. Sol owns bounded metadata
and report migration, Sol owns isolated CSS cascade; root owns complex topology/clip integration
and all Git. Luna reviews read-only. All three stories required; MVP is source evidence only.
