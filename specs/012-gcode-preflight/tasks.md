# Tasks: Read-only G-code preflight

## Shared contracts
- [x] T001 Review roadmap, constitution, legacy/reference parser seams and official protocol facts in research.md.
- [x] T002 Freeze bounded core/source/UI contracts, zero-offset assumptions and eight plan gates.
- [ ] T003 Write invalid/frozen source/setup/report tests first in tests/test_gcode_models.py.
- [ ] T004 Implement core/gcode_models.py with finite mm values, snapshot digest, bounded report and cancellation exception.

## US1: Interpret the actual program
Independent test: equivalent unit/mode programs and analytic circles have expected endpoints/extents; unknown syntax blocks.
- [ ] T005 Write tests/test_gcode_lexer.py for comments, words, line numbers, realtime/control bytes and all resource caps.
- [ ] T006 Implement bounded core/gcode_lexer.py with source-line errors and no silently skipped tokens.
- [ ] T007 Write tests/test_gcode_motion.py for signed-R/relative-IJ, full circles/helices, rounding and Placement extrema.
- [ ] T008 Implement independent arc geometry/length/extrema in core/gcode_motion.py using existing Placement.
- [ ] T009 Write modal interpreter tests in tests/test_gcode_preflight.py before parser changes, including every unsupported/modal conflict and no partial-block acceptance.
- [ ] T010 Implement concrete modal state/events in core/gcode_parser.py for the exact contract subset.
- [ ] T011 Test/implement physical feed persistence, explicit initial modes and program-end semantics; unsupported changes fail closed.
- [ ] T012 Verify complete versus partial interpretation and no-motion failure in tests/test_gcode_preflight.py.

## US2: Declared setup and hazards
Independent test: placement and analytic travel/rapid/feed cases produce exact line-specific blocked outcomes.
- [ ] T013 Write pure preflight tests for initial/move/arc bounds, Z limits, unsafe rapid, missing feed and declared offsets.
- [ ] T014 Implement online complete-path bounds and setup mapping in core/gcode_preflight.py; no toolpath retention.
- [ ] T015 Implement line-specific feed/XYZ/rapid checks with total counters and bounded diagnostic samples.
- [ ] T016 Test rotated/mirrored arc interior extrema, boundary tolerance and all-axis violations.
- [ ] T017 Write tests for feed/rapid/dwell duration, pauses/missing rates and incomplete paths before timing implementation.
- [ ] T018 Implement honest nominal time with per-axis rapid rates; unknown contributions keep total unavailable.
- [ ] T019 Measure100000-line analysis/cancellation and test malicious resource limits; correct complexity before UI integration.

## US3: Read-only report workflow
Independent test: file/selected-job workflows show the same immutable result; cancellation/input changes prevent stale results.
- [ ] T020 Write tests/test_gcode_source.py for complete CNCJob source copying, bounded UTF-8 read and no mutation/fallback.
- [ ] T021 Implement narrow bridge/gcode_source.py; reject absent or incomplete source without invoking legacy export.
- [ ] T022 Write tests/test_gcode_ui.py for required setup, no implicit limits, file/job snapshot identity and report display.
- [ ] T023 Implement ui/preflight_setup.py using existing Placement and explicit initially-empty numeric fields.
- [ ] T024 Implement ui/preflight_worker.py with immutable values and bounded cooperative cancellation.
- [ ] T025 Implement ui/preflight_panel.py load/select/analyze/cancel/report flow; no controller dependency or raw send.
- [ ] T026 Test and implement generation tokens, selected-job rechecks and snapshot labeling to invalidate stale reports.
- [ ] T027 Test and implement worker close/timeout retention and GUI-thread ownership with existing shutdown pattern.
- [ ] T028 Add minimal lazy Plugins menu and host shutdown hook in appMain.py/appHandlers/appLifecycle.py.
- [ ] T029 Extend actual desktop smoke with selected-job/file preflight success, hazard block and source-preservation evidence.

## Delivery
- [ ] T030 Document dialect, explicit setup, conditional result, unknown timing and physical limits in docs/GCODE_PREFLIGHT.md.
- [ ] T031 Review all11FR/5SC and eight gates; check strict grammar and no machine/dependency/source-port expansion.
- [ ] T032 Run full pytest and import/growth/size checks; record counts/head and performance results.
- [ ] T033 Run actual desktop smoke and inspect the panel; preserve existing CAM/laser/manual flows.
- [ ] T034 Update roadmap and validation.md; publish focused PR.
- [ ] T035 Verify final-head Windows CI and fix any failures before merge.
- [ ] T036 Merge validated head and record delivery links/status.
- [ ] T037 Mark only evidenced tasks complete; carry hardware limitations forward without claiming physical validation.

## Dependencies/delegation
T001-T002 precede code; tests precede owned implementation. Sol may own frozen models or narrow
bridge/UI independently; root owns parser/modal/arc integration and review. Luna audits sources
and bounded assumptions. No concurrent edits to shared files. All three stories required.
