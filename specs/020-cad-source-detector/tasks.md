# Tasks: CAD source detection

Input: spec.md, plan.md, research.md, data-model.md and contracts/cad-source.md.
Three stories, 38 tasks. Tests precede core/domain implementation.

## Setup and shared records
- [x] T001 Research explicit producer markers and actual licensed exports in research.md.
- [x] T002 Freeze APIs, bounds and eight gates in contracts/cad-source.md and plan.md.
- [ ] T003 Write immutable source/evidence invariant tests in tests/test_cad_source_models.py.
- [ ] T004 Implement core/cad_source.py records without geometry or I/O dependencies.
- [ ] T005 Write strict schema, old absence and malformed tests in tests/test_cad_source_codec.py.
- [ ] T006 Implement schema1 detached codec in core/cad_source_codec.py.

## US1: SVG source evidence
- [ ] T007 [US1] Write producer classification/conflict/limit cases in tests/test_cad_source_detection.py.
- [ ] T008 [US1] Implement finite producer rules and bounded dispatcher in importers/cad_source.py.
- [ ] T009 [US1] Write root/version/XMP/desc/comment and namespace-negative tests in tests/test_cad_source_svg.py.
- [ ] T010 [US1] Implement offline bounded SVG extraction in importers/cad_svg_source.py.
- [ ] T011 [US1] Test fixed DTD, entities, oversized/deep XML and malformed input in tests/test_cad_source_svg.py.
- [ ] T012 [US1] Preserve licensed KiCad SVG export and provenance in tests/reference/cad-source/.
- [ ] T013 [US1] Test real KiCad SVG, upstream Inkscape asset and authored019 Unknown in tests/test_cad_source_fixtures.py.

## US2: DXF source evidence
- [ ] T014 [P] [US2] Write pair/framing/generator and negative geometry/style tests in tests/test_cad_source_dxf.py.
- [ ] T015 [US2] Implement bounded text DXF evidence in importers/cad_dxf_source.py.
- [ ] T016 [US2] Test malformed, binary, excessive lines/pairs and conflicting claims in tests/test_cad_source_dxf.py.
- [ ] T017 [US2] Preserve unmarked real KiCad DXF/provenance in tests/reference/cad-source/.
- [ ] T018 [US2] Verify real KiCad DXF remains Unknown in tests/test_cad_source_fixtures.py.

## US3: historical source evidence
- [ ] T019 [US3] Test optional owner publication, invalid payload and retained identity in tests/test_cad_source_bridge.py.
- [ ] T020 [US3] Implement pure owner boundary in bridge/cad_source.py.
- [ ] T021 [US3] Test plain-text, missing/error/replace display in tests/test_cad_source_ui.py.
- [ ] T022 [US3] Implement parent-owned source section and adapter in ui/cad_source.py.
- [ ] T023 [US3] Attach source section independently from physical report in ui/import_report.py.
- [ ] T024 [US3] Add optional persisted cad_source fields in GeometryObject.py and GerberObject.py.
- [ ] T025 [US3] Add short successful source hooks and exact DXF newlines in appHandlers/appIO.py.
- [ ] T026 [US3] Test actual SVG/DXF host geometry/default/source preservation in tests/test_cad_source_host.py.
- [ ] T027 [US3] Add actual desktop roundtrip journey in tests/smoke_cad_source.py and smoke_app.py.

## Audit and delivery
- [ ] T028 Audit FR001–009, SC001–005 and gates in validation.md.
- [ ] T029 Add regressions before any audit fixes in tests/test_cad_source*.py.
- [ ] T030 Document supported markers, uncertainty and fixture coverage in docs/CAD_SOURCE.md.
- [ ] T031 Record immutable source/license/adaptation in THIRD_PARTY_CHANGES.md.
- [ ] T032 Run focused source/reference/architecture tests and record validation.md.
- [ ] T033 Run final runtime full suite and record validation.md.
- [ ] T034 Run actual desktop all journeys and inspect screenshot for validation.md.
- [ ] T035 Update docs/ROADMAP.md and publish focused PR after019 delivery.
- [ ] T036 Verify final-head Windows CI and record validation.md.
- [ ] T037 Merge validated head and record delivery links in validation.md.
- [ ] T038 Finish tasks.md/docs/ROADMAP.md without overstating vendor/hardware coverage.

Dependencies: shared immutable records -> SVG and DXF parsers in parallel -> owner/UI integration ->
full validation. Sol owns records/codec; another Sol owns independent DXF parser and fixture assembly.
Root owns SVG parsing, conflict orchestration, integration and all Git. Luna audits read-only.
US1 is the smallest independent evidence result; all three stories are required for delivery.
Every task has an explicit file scope; no competing write ownership.
