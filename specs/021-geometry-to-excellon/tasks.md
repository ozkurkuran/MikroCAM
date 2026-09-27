# Tasks: Geometry circles to Excellon

Input: spec, plan, research, data model and contracts. Three stories, 39 tasks; tests first.

## Shared foundations
- [x] T001 Research authoritative Geometry storage and existing SVG drill seams in research.md.
- [x] T002 Freeze records/APIs/bounds and eight gates in contracts/geometry-drills.md and plan.md.
- [x] T003 Write shared circle-fit tests in tests/test_circle_fit.py before extraction.
- [x] T004 Extract core/circle_fit.py and delegate svg_drill_circles._fitted without changing SVG gates.
- [x] T005 [P] Write DrillHole/grouping/tool validation cases in tests/test_drill_tools.py.
- [x] T006 Add shared hole grouping/tool validation in core/drill_groups.py; SVG wrapper delegates.
- [x] T007 Write Geometry review record invariants in tests/test_geometry_drill_models.py.
- [x] T008 Add frozen records in core/geometry_drill_models.py.

## US1: current physical circle review
- [x] T009 [US1] Write analytic contour/role/MM/IN tests in tests/test_geometry_drill_detection.py.
- [x] T010 [US1] Implement bounded traversal/fingerprint and circle review in core/geometry_drills.py.
- [x] T011 [US1] Test invalid/3D/nonfinite/open/ellipse/coarse geometry and all bounds in tests/test_geometry_drill_detection.py.
- [x] T012 [US1] Test equivalent contour deduplication and alternative concentric roles in tests/test_geometry_drill_detection.py.
- [x] T013 [US1] Write authoritative single/multi-tool source tests in tests/test_geometry_drill_bridge.py.
- [x] T014 [US1] Implement explicit source extraction in bridge/geometry_drills.py.

## US2: explicit selection and tool review
- [x] T015 [US2] Test unique indices/group mean/overlap after grouping in tests/test_geometry_drill_selection.py.
- [x] T016 [US2] Add group_geometry_selection delegation in core/geometry_drills.py.
- [x] T017 [US2] Write no-preselection/role/summary/invalid selection tests in tests/test_geometry_drill_ui.py.
- [x] T018 [US2] Implement parent-owned GeometryDrillDialog in ui/geometry_drills.py.
- [x] T019 [US2] Add one active-Geometry Plugins entry through a short appMain.py hook.

## US3: preserve source and publish Excellon
- [x] T020 [US3] Test shared Excellon factory defaults/units/failures/guard in tests/test_excellon_bridge.py.
- [x] T021 [US3] Extract bridge/excellon.py common creator; bridge/svg_drills.py retains public API.
- [x] T022 [US3] Test stale name/unit/mode/tool/geometry/membership/replacement in tests/test_geometry_drill_bridge.py.
- [x] T023 [US3] Implement verify_geometry_review and guarded creation in bridge/geometry_drills.py.
- [x] T024 [US3] Test actual MM/IN Excellon export/reparse and source preservation in tests/test_geometry_drill_roundtrip.py.
- [x] T025 [US3] Test cancelled/failed/actual creation dialog outcomes in tests/test_geometry_drill_ui.py.
- [x] T026 [US3] Add actual desktop selection/export/project journey in tests/smoke_geometry_drills.py and smoke_app.py.

## Audit and delivery
- [x] T027 Audit FR001–010/SC001–005 and gates in validation.md.
- [x] T028 Add regressions before audit fixes in tests/test_geometry_drill*.py.
- [x] T029 Verify all existing SVG circle/group/factory behavior in tests/test_svg_drill*.py.
- [x] T030 Document source authority, intent and tolerances in docs/GEOMETRY_DRILLS.md.
- [x] T031 Record independent implementation/source reuse in validation.md and docs/GEOMETRY_DRILLS.md.
- [x] T032 Run focused/reference/import-boundary/growth checks and record validation.md.
- [x] T033 Run complete suite at final runtime head and record validation.md.
- [x] T034 Run actual desktop all journeys at that head and inspect screenshots for validation.md.
- [x] T035 Update docs/ROADMAP.md and publish focused PR after020 delivery.
- [x] T036 Verify final-head Windows CI and record validation.md.
- [x] T037 Merge validated head and record PR/CI/merge links in validation.md.
- [x] T038 Mark delivery in tasks.md/docs/ROADMAP.md, preserving physical-validation limits.
- [x] T039 Confirm source objects and prior delivered behavior remain covered in validation.md.

Dependencies: shared mathematical/grouping records -> pure detection and host extraction -> selection
UI and shared factory -> guarded publication -> complete validation. Sol may implement shared grouping/
factory and isolated review UI against frozen APIs; root owns circle math, source authority and fingerprint
integration. Luna audits read-only. All Git belongs to root. No shared write ownership.
US1 is the smallest independent review; all three stories are required for delivery.
