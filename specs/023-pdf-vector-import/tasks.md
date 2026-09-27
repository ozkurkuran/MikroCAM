# Tasks: selected PDF vector page

## Design and foundations
- [x] T001 Evaluate legacy page/affine behavior and permissive readers in research.md.
- [x] T002 Freeze records, boundaries and eight constitution gates in plan.md, data-model.md and contracts/pdf-vectors.md.
- [x] T003 Write strict record/report/result tests in tests/test_pdf_vector_models.py.
- [x] T004 Implement immutable bounded records in mikrocam/core/pdf_models.py.
- [x] T005 Write and implement strict schema-one codec in tests/test_pdf_report_codec.py and mikrocam/core/pdf_report_codec.py.

## US1: select one bounded page
- [x] T006 Pin lazy pypdf dependency and record BSD license in requirements and dependency inventory.
- [x] T007 Write selected-page/inherited-box/rotation/unsupported-content tests in tests/test_pdf_vector_reader.py.
- [x] T008 Implement bounded reader in mikrocam/bridge/pdf_reader.py.
- [x] T009 Test source/stream/tree/operator bounds and configuration reset in tests/test_pdf_vector_reader.py.
- [x] T010 Add explicit file inspection/page selection in mikrocam/ui/pdf_import.py.

## US2: physical vector review
- [x] T011 Write physical rotation/crop/flip tests in tests/test_pdf_vector_frame.py.
- [x] T012 Implement physical frame in mikrocam/core/pdf_frame.py.
- [x] T013 Write path/subpath/state/curve grammar tests in tests/test_pdf_vector_program.py.
- [x] T014 Implement finite interpreter in mikrocam/importers/pdf_program.py.
- [x] T015 Write fill/stroke/opaque paint/clip tests in tests/test_pdf_vector_geometry.py.
- [x] T016 Implement bounded geometry composition in mikrocam/core/pdf_geometry.py using existing helpers.
- [x] T017 Add point/overlay/state complexity and unsupported grammar regressions in tests/test_pdf_vector_program.py.
- [x] T018 Add options/review invalidation and tests in mikrocam/ui/pdf_import.py and tests/test_pdf_vector_ui.py.

## US3: guarded Geometry publication
- [x] T019 Write source mutation/forgery/factory failure tests in tests/test_pdf_vector_bridge.py.
- [x] T020 Implement bounded file review and guarded creator in mikrocam/bridge/pdf_import.py.
- [x] T021 Test historical/missing/invalid PDF report persistence in tests/test_pdf_report_ui.py.
- [x] T022 Add optional Geometry report hooks and mikrocam/ui/pdf_report.py.
- [x] T023 Test explicit successful/failed creation in tests/test_pdf_vector_ui.py.
- [x] T024 Add short File Import menu hook in appMain.py.
- [x] T025 Test actual MM/IN host/export/project preservation in tests/test_pdf_vector_roundtrip.py.
- [x] T026 Add actual desktop page/crop/flip/export/project journey in tests/smoke_pdf_vectors.py and tests/smoke_app.py.

## Audit and delivery
- [x] T027 Audit requirements and eight gates in validation.md.
- [x] T028 Add meaningful regression tests before audit fixes in tests/test_pdf_vector*.py.
- [x] T029 Verify existing PDF, SVG and source/report regressions.
- [x] T030 Document supported grammar, physical frame and limits in docs/PDF_VECTOR_IMPORT.md.
- [x] T031 Verify license/provenance and reproducible environments in validation.md.
- [x] T032 Run focused, architecture, dependency and growth checks; record validation.md.
- [x] T033 Run complete suite at final runtime head; record validation.md.
- [x] T034 Run actual desktop journeys and inspect screenshot; record validation.md.
- [x] T035 Update docs/ROADMAP.md and publish focused PR after022 delivery.
- [x] T036 Verify final-head Windows CI; record validation.md.
- [x] T037 Merge validated head and record PR/CI/merge links in validation.md.
- [x] T038 Mark delivery in tasks.md/docs/ROADMAP.md, retaining validation limits.
- [x] T039 Confirm original sources and prior behavior remain covered in validation.md.

Dependencies: strict records -> bounded page reader and physical frame -> interpreter/painting ->
review -> guarded creation/persistence -> actual host/desktop/full validation. Tests precede their
implementation. US1 is an independently reviewable page inventory; all three stories deliver the
slice. Sol owns isolated records/codec/UI and reader/dependency files; root owns geometry,
interpreter and host integration. Luna audits read-only. Root alone stages and commits.
