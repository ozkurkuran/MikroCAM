# Tasks: SVG scale, transforms and solid strokes

## Shared contracts
- [x] T001 Review roadmap/constitution, Evo shared seam and primary SVG/CSS specifications.
- [x] T002 Freeze three stories, source mapping/paint contracts, limits and eight gates.
- [ ] T003 Write strict immutable model and length/matrix/viewport tests first.
- [ ] T004 Implement core models and source-coordinate math.

## US1: physical scale
- [ ] T005 Test bounded XML/source identity/root dimensions/viewBox and inference notices.
- [ ] T006 Implement document parsing, namespace handling and viewport resolution.
- [ ] T007 Test mm/cm/in/pt/pc/px and mixed element units under viewBox.
- [ ] T008 Test mm/IN host conversion and single optional vertical flip.
- [ ] T009 Implement bridge result assembly and final host-unit boundary.

## US2: transforms and source traversal
- [ ] T010 Test list/parent/reference order, matrix coefficient order and rotation centres.
- [ ] T011 Implement bounded group/local-use traversal and unused-definition handling.
- [ ] T012 Test malformed transforms, singular matrices, duplicate/missing/cyclic/external IDs.
- [ ] T013 Implement explicit unsupported syntax/resource/depth/numeric failures.
- [ ] T014 Write line/Bezier/elliptic-arc flattening error and budget tests.
- [ ] T015 Implement bounded physical-tolerance curve flattening and bridge svg.path adaptation.
- [ ] T016 Characterize existing Move/Close/path fixtures without changing frozen artifacts.

## US3: material width
- [ ] T017 Test inherited paint/inline overrides, none/zero width and unsupported appearance.
- [ ] T018 Implement finite inherited style resolution with useful diagnostics.
- [ ] T019 Test primitive paths, fill rules/implicit closure and preserved open centreline metadata.
- [ ] T020 Implement bounded primitive construction and simple fill policy.
- [ ] T021 Test cap/join/miter and nonuniform/skewed stroke expansion before transform.
- [ ] T022 Implement local solid stroke expansion and validated per-element geometry.
- [ ] T023 Test source point/geometry budgets, explicit CAM centreline/color notices and empty output.

## Integration and delivery
- [ ] T024 Test existing GUI/Tcl shared import seam, useful errors and no partial object mutation.
- [ ] T025 Add thin UI adapter and replace legacy extraction while retaining object/tool population.
- [ ] T026 Add authored reference fixtures with independent analytic bounds/area and source hashes.
- [ ] T027 Verify fixture equivalence/tolerances and existing frozen reference suite.
- [ ] T028 Audit all 11 FRs/5 SCs and eight gates; add regressions before substantive fixes.
- [ ] T029 Document supported units/appearance, inference/notices and explicit rejected semantics.
- [ ] T030 Run full pytest/import/growth/size checks with exact tested head/counts.
- [ ] T031 Run actual desktop Geometry/Gerber imports, source preservation and save/reopen.
- [ ] T032 Inspect desktop output and preserve all prior smoke journeys.
- [ ] T033 Update roadmap/validation and publish focused PR.
- [ ] T034 Verify final-head Windows CI and fix actual failures.
- [ ] T035 Merge validated head after preceding slices.
- [ ] T036 Record delivery links and evidence-only completion.
- [ ] T037 Carry approximation/unsupported/physical limitations forward.

Tests precede implementation. Shared contracts precede exclusive file delegation. Root alone stages
and commits. All three stories are required; no frozen reference harness is edited.
