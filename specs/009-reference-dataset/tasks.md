# Tasks: PCB reference dataset

## Setup and foundation
- [ ] T001 Verify source/license/API probe evidence and all eight constitution gates in specs/009-reference-dataset/research.md and validation.md.
- [ ] T002 Freeze exact strict codec/config schema in specs/009-reference-dataset/data-model.md and contracts/reference-data.md before harness/artifact creation; enforce agreed WKB64MiB, paths200000, vertices2000000 and decoded JSON128MiB limits.

## US1: Authentic audited inputs (P1)
**Independent test**: Offline audit admits 10–20 distinct designs/all five origins; corruption,
unknown license, duplicate identity and escaping paths fail before parsing.
- [ ] T003 [US1] Write corpus/schema/provenance rejection tests in tests/test_reference_dataset.py first, including duplicate keys/IDs, hashes, notices, additional valid origins, archive!member evidence and traversal/symlinks.
- [ ] T004 [US1] Implement strict developer manifest/config validation in tests/reference/reference_data.py; exact keys, schema1, relative safe paths and 64 lowercase-hex SHA256 required.
- [ ] T005 [US1] Audit candidate redistribution/tool-origin/design evidence and retain original notices in tests/reference/boards/<board-id>/ before copying board inputs.
- [ ] T006 [US1] Admit unchanged source bytes and role records in tests/reference/boards/manifest.json; require 10–20 unique design identities and KiCad/EasyEDA/Altium/Eagle/Proteus coverage.
- [ ] T007 [US1] Run offline corpus integrity/admission tests and record actual inventory/exclusions in specs/009-reference-dataset/validation.md.

## US2: Actual independent baseline capture (P1)
**Independent test**: Both pinned unchanged sources produce actual per-stage outcomes; repeat
capture agrees for successful deterministic results, IN scaling happens once and errors remain explicit.
- [ ] T008 [US2] Write capture/source/isolation/timeout/normalization/strict artifact tests first in tests/test_reference_capture.py; reject wrong/dirty source, missing stages, corruption and nonfinite/3D data; preserve Excellon tool diameters, duplicate drills/slots and source_units metadata.
- [ ] T009 [US2] Freeze probe-verified common explicit machining parameters and stages in tests/reference/capture-config.json; record Evo N versus legacy RTree separately, never use global fallback values.
- [ ] T010 [US2] Implement concrete unchanged-engine calls and once-only parser.units normalization in tests/reference/capture_worker.py; retain ordered kind/Point/LineString paths and header+body G-code.
- [ ] T011 [US2] Implement strict compressed JSON1 capture validation/provenance in tests/reference/reference_data.py; error/unsupported stages carry diagnostic without fabricated outputs.
- [ ] T012 [US2] Implement explicit-engine subprocess capture CLI in tests/reference/capture.py; sandbox settings before imports, clean only owned processes, refuse wrong SHA/dirty source/existing output directories.
- [ ] T013 [US2] Capture actual outcomes twice for each pinned engine into separate fresh directories; review provenance and reproducibility before adding tests/reference/goldens/legacy8994/ and goldens/evo/.
- [ ] T014 [US2] Record exact commands/runtime/source/config hashes, IN normalization/repeat evidence and authentic failure inventory in specs/009-reference-dataset/validation.md; preserve differences between baselines.

## US3: Explicit tolerant comparison (P2)
**Independent test**: Matching valid records pass; introduced topology/vertex/direction/order
changes fail; invalid provenance, missing stages and repeated baseline errors return indeterminate.
- [x] T015 [P] [US3] Write pure comparator tests first in tests/test_reference_compare.py for topology, discrete Hausdorff/area, exact-zero tolerance, nonboolean finite tolerances, bounds, unit-normalized mismatch, reverse/order/kind/vertex-count and oversized/invalid WKB.
- [x] T016 [US3] Implement frozen GeometryComparison/ReferencePath/PathComparison and pure compare_geometry/compare_paths in mikrocam/core/reference_compare.py using the exact contract; no Qt/host/G-code lexer.
- [ ] T017 [US3] Add emitted-instruction tests before core/reference_gcode.py implementation in tests/test_reference_gcode.py; then add tests/test_reference_compare_cli.py for explicit selected baseline/tolerances, source/input/config mismatch, corrupted artifacts, duplicate JSON, missing stage and repeated error/unsupported outcomes.
- [ ] T018 [US3] Implement read-only comparison CLI and JSON1 report in tests/reference/compare.py; exit0 only all-match, exit1 measured difference, exit2 any invalid/indeterminate, no golden update flag.
- [ ] T019 [US3] Capture declared clean current revision and compare separately against both retained baselines using tests/reference/capture.py and compare.py; do not automatically pick the closer baseline or widen tolerances.
- [ ] T020 [US3] Record per-board/input/stage metrics, differences and indeterminate outcomes in specs/009-reference-dataset/validation.md, preserving actual errors instead of silently skipping them.

## Delivery
- [ ] T021 Run all reference tests plus full pytest and architecture/growth/size gates; record commands/results in specs/009-reference-dataset/validation.md.
- [ ] T022 Verify offline comparison leaves goldens/corpus/settings unchanged and no capture children running in tests/test_reference_capture.py and test_reference_compare.py.
- [ ] T023 Review retained source-file hashes/notices and external dataset provenance in tests/reference/boards/manifest.json and THIRD_PARTY_CHANGES.md without relabeling original licenses.
- [ ] T024 Record hosted Windows CI evidence and any remaining actual baseline failures in specs/009-reference-dataset/validation.md.
- [ ] T025 Update developer usage and roadmap completion accurately in specs/009-reference-dataset/quickstart.md and docs/ROADMAP.md after verified delivery.
- [ ] T026 Review requirement/task/evidence coverage and deliver the feature PR; retain unresolved comparison evidence explicitly in specs/009-reference-dataset/validation.md.

## Dependencies and execution
T001/T002 gate artifact creation. T003 precedes T004; admission requires T005/T006. T008
precedes T009–T012; approved corpus/config precede T013. T015 precedes T016 and can run
independently of source capture: it uses synthetic mismatch tests that do not count as corpus
boards. T017 precedes T018; T019 requires actual baseline captures and core/CLI integration.
US1 gives an audited-input MVP, US2 adds real provenance-bearing captures, US3 gives regression reports.
Different-file evidence audit and pure comparator tests may proceed in parallel; shared codec
edits are sequential. No overlap or general backend framework is required.

**Counts**: 26 tasks; US1=5, US2=7, US3=6, setup/foundation=2, delivery=6.
