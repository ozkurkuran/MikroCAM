# Tasks: selected PDF vector page

## Design and foundations
- [x] T001 Evaluate legacy page/affine behavior and permissive readers in research.md.
- [x] T002 Freeze records, boundaries and eight constitution gates in plan.md, data-model.md and contracts/pdf-vectors.md.
- [ ] T003 Write strict record/report/result tests in tests/test_pdf_vector_models.py.
- [ ] T004 Implement immutable bounded records in mikrocam/core/pdf_models.py.
- [ ] T005 Write and implement strict schema-one codec in tests/test_pdf_report_codec.py and mikrocam/core/pdf_report_codec.py.

## US1: select one bounded page
- [ ] T006 Pin lazy pypdf dependency and record BSD license in requirements and dependency inventory.
- [ ] T007 Write selected-page/inherited-box/rotation/unsupported-content tests in tests/test_pdf_vector_reader.py.
- [ ] T008 Implement bounded reader in mikrocam/bridge/pdf_reader.py.
- [ ] T009 Test source/stream/tree/operator bounds and configuration reset in tests/test_pdf_vector_reader.py.
- [ ] T010 Add explicit file inspection/page selection in mikrocam/ui/pdf_import.py.

## US2: physical vector review
- [ ] T011 Write physical rotation/crop/flip tests in tests/test_pdf_vector_frame.py.
- [ ] T012 Implement physical frame in mikrocam/core/pdf_frame.py.
- [ ] T013 Write path/subpath/state/curve grammar tests in tests/test_pdf_vector_program.py.
- [ ] T014 Implement finite interpreter in mikrocam/importers/pdf_program.py.
- [ ] T015 Write fill/stroke/opaque paint/clip tests in tests/test_pdf_vector_geometry.py.
- [ ] T016 Implement bounded geometry composition in mikrocam/core/pdf_geometry.py using existing helpers.
- [ ] T017 Add point/overlay/state complexity and unsupported grammar regressions in tests/test_pdf_vector_program.py.
- [ ] T018 Add options/review invalidation and tests in mikrocam/ui/pdf_import.py and tests/test_pdf_vector_ui.py.

## US3: guarded Geometry publication
- [ ] T019 Write source mutation/forgery/factory failure tests in tests/test_pdf_vector_bridge.py.
- [ ] T020 Implement bounded file review and guarded creator in mikrocam/bridge/pdf_import.py.
- [ ] T021 Test historical/missing/invalid PDF report persistence in tests/test_pdf_report_ui.py.
- [ ] T022 Add optional Geometry report hooks and mikrocam/ui/pdf_report.py.
- [ ] T023 Test explicit successful/failed creation in tests/test_pdf_vector_ui.py.
- [ ] T024 Add short File Import menu hook in appMain.py.
- [ ] T025 Test actual MM/IN host/export/project preservation in tests/test_pdf_vector_roundtrip.py.
- [ ] T026 Add actual desktop page/crop/flip/export/project journey in tests/smoke_pdf_vectors.py and tests/smoke_app.py.

## Audit and delivery
- [ ] T027 Audit requirements and eight gates in validation.md.
- [ ] T028 Add meaningful regression tests before audit fixes in tests/test_pdf_vector*.py.
- [ ] T029 Verify existing PDF, SVG and source/report regressions.
- [ ] T030 Document supported grammar, physical frame and limits in docs/PDF_VECTOR_IMPORT.md.
- [ ] T031 Verify license/provenance and reproducible environments in validation.md.
- [ ] T032 Run focused, architecture, dependency and growth checks; record validation.md.
- [ ] T033 Run complete suite at final runtime head; record validation.md.
- [ ] T034 Run actual desktop journeys and inspect screenshot; record validation.md.
- [ ] T035 Update docs/ROADMAP.md and publish focused PR after022 delivery.
- [ ] T036 Verify final-head Windows CI; record validation.md.
- [ ] T037 Merge validated head and record PR/CI/merge links in validation.md.
- [ ] T038 Mark delivery in tasks.md/docs/ROADMAP.md, retaining validation limits.
- [ ] T039 Confirm original sources and prior behavior remain covered in validation.md.

Dependencies: strict records -> bounded page reader and physical frame -> interpreter/painting ->
review -> guarded creation/persistence -> actual host/desktop/full validation. Tests precede their
implementation. US1 is an independently reviewable page inventory; all three stories deliver the
slice. Sol owns isolated records/codec/UI and reader/dependency files; root owns geometry,
interpreter and host integration. Luna audits read-only. Root alone stages and commits.
