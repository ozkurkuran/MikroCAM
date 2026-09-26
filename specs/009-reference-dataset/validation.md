# Validation: PCB reference dataset

## Initial pre-implementation analysis
Documentation authored 2026-09-27 for branch 009-reference-dataset. Three stories, 26 tasks;
all eight constitution gates are satisfied by the proposed scope, with admission evidence
explicitly required. No code, dataset or capture claim is made by this analysis.
Spec Kit specify/plan/tasks/analyze instructions were read; `.specify/extensions.yml` is absent,
so no pre/post extension hooks are registered. Setup templates/pointer already existed.

| Requirement | Tasks |
| --- | --- |
| FR-001 / SC-001 | T003–T007 |
| FR-002 | T003–T007, T023 |
| FR-003 / SC-002 | T008, T010–T014 |
| FR-004 | T008–T012, T014, T022 |
| FR-005 | T008–T014 |
| FR-006 | T008, T011–T014, T017–T020 |
| FR-007 / SC-003 | T008, T013–T014 |
| FR-008 | T015–T019 |
| FR-009 / SC-004 | T015–T018 |
| FR-010 | T003–T004, T008, T011, T015, T017 |
| FR-011 / SC-005 | T017–T022 |
| FR-012 | T003, T008, T015–T017, T021–T024 |

Coverage: 12/12 functional requirements and 5/5 success criteria. No unmapped task or
constitution exception. Tasks T001/T002 freeze pending capture evidence before artifact creation;
T015/T016 pure comparator work can proceed independently against the agreed contract.

## Evidence currently available
Pinned baseline source SHAs and read-only worktree identities are supplied by the root.
Root probes confirm real headless parsing/isolation/CNC generation+own parsing on both;
Evo optimization N versus legacy hardcoded RTree, parser.units authority and header+body
G-code are recorded in research.md. Eight isolated MM/IN/repeat processes confirm factor25.4
and repeat-identical G-code/path hashes per pair. These are probe findings, not completed corpus goldens.

## Evidence still required
- Final 10–20-board audit with all five origin tools, original notices and per-file SHA256.
- Formal strict capture schema/config freeze and retained runtime/source hashes.
- Actual retained per-board captures and failure inventory; feasibility/IN/repeat probes are resolved.
- Test-first failures, introduced-mismatch success, strict-invalid cases and CLI exit evidence.
- Full tests, architecture/growth/size, owned-process cleanup, read-only/offline and hosted CI evidence.

Implementation results must append exact commands, counts and observed limitations. A baseline
error/unsupported stage remains indeterminate; do not mark it matching or claim all-stage coverage
merely because both engines fail. Both distinct actual baseline outputs remain retained.

## Pure comparison implementation
- Initial `pytest -q tests/test_reference_compare.py` failed collection because the core
  module did not exist. Tool-inventory tests subsequently failed in ten cases before
  `ReferenceTool`/`compare_tools` existed.
- Final focused run with CPython 3.13 repro-a: **59 passed in 0.30s**. Deliberate topology,
  scale, path reversal/order/vertex-count, tool-diameter and duplicate-drill changes fail
  comparison; tolerance boundaries, malformed/trailing/SRID/Z/M/empty/nonfinite WKB and
  resource limits are covered. Unused declared drill tools remain metadata, not lost hits.
- The initial geometry/path implementation plus import-boundary suite passed 93 tests.
  Full architecture/integration and hosted CI remain delivery tasks.
- Independent read-only review found no confirmed geometry/path defect; its M/SRID coverage
  suggestion is now tested. Empty successful outputs must be contextual errors at the capture
  boundary, and report integration must preserve them as indeterminate.

## Emitted machining instructions and report integration
Review identified a real coverage gap in comparing only 2D paths/requested settings:
wrong emitted Z/feed/spindle/dwell could otherwise pass. The spec/plan/contract were amended
before a narrow numeric-word comparator was implemented. Its initial test run failed with
the missing module; all 30 tests then passed. Together with geometry/path/drill cases:
**89 passed in 0.23s**. This is saved-output comparison, not modal simulation/preflight.

Report CLI tests first failed on the absent module, then **14 passed in 2.13s**. They verify
unchanged offline inputs, contextual missing/corrupt/unsupported evidence, parameter changes,
runtime/config/input mismatches and exclusive report publication outside input directories.
Actual baseline/candidate captures and real corpus comparison remain the next integration gate.

## Audited corpus and bounded comparison review
The admitted corpus contains 10 distinct designs from Eagle, Altium, DipTrace, Fritzing,
Proteus, EasyEDA and KiCad: 60 source files, 3,612,881 bytes. All 60 committed Git blobs
were checked against their manifest SHA256, including unchanged archive members. Source
identities, individual licenses and rejected ambiguous candidates are recorded in the
manifest, retained notices, reference README and THIRD_PARTY_CHANGES.md.

Actual Altium evidence required raising the decoded JSON/child bound from 128 to 512 MiB;
the old Evo resource error is excluded from the accepted baseline run. A new UTF-8 boundary
test checks JSON parse/dump/gzip/publication. G-code comparison streams blocks and records
total differences plus 100 indices. Topology/area failures omit the unnecessary quadratic
Hausdorff metric explicitly as null. New behavior tests first failed in three cases, then
passed. Independent review also reproduced baseline replay and missing-stage-context issues
in three failing CLI tests; both are fixed without changing capture helper bytes.

Latest focused comparator/CLI run: **110 passed in 4.79s**. Boundary codec/dataset/CLI run:
**78 passed in 7.28s**; child capture boundary suite: **25 passed**. Full tests, final frozen
artifacts and hosted CI still require the delivery checks below.

## Accepted frozen captures (2026-09-27)
Both engines were captured twice into distinct new directories. All 20 complete compressed
artifacts have identical SHA256 on the second run. The accepted copies total **120,199,820
bytes**: legacy 39,997,483 and Evo 80,202,337. `goldens/inventory.json` records exact file hashes
and lengths; the integrity tests also validate input links, source identity and stage schemas.
Each engine has 10 boards / 49 requested stages: **47 ok, 2 error**. The two errors are the
empty KiCad NPTH files (Pico2ROMEmu and MUX-ADG706): actual parser produced no tools. Neither
repeated error counts as a matching CAM result. Proteus drill maps remain retained artwork,
not invented Excellon output.

Sources are unchanged `6ba378bca139aa306f8c94f09461a98f95d3c75b` (247 application Python files)
and `d0a86cf4f1ac41a206b20f316d4a29f28a93bbff` (337). Every source file hash is in each capture.
Runtime is standard CPython 3.13.13 x64, with the identical pinned development/image environment
and full dependency inventory recorded in the artifacts.

- Configuration SHA256: `e5525f14f581921aac335bac3e4b18963f0df7d02215fa5619d3606ff59dfc27`.
- Harness SHA256: `cc78d08a7173f4dd497026c896e9743ca5875c6e59dc8cd8b6d3d671861df847`.
- Sorted legacy filename/hash inventory digest: `79dca4f1feb2da234307a80ac8d5844c8c2be7333a833b9e35fca5cd39d52965`.
- Sorted Evo filename/hash inventory digest: `f89b04a098027142d6e40c5ff779e9d39867488e20b7e7125e975b734e027f05`.

Git attributes now preserve all six hashed helper files byte-for-byte, including the sandbox's
existing CRLF bytes; indexed blobs were checked against the working bytes and the frozen
harness hash. This prevents Windows newline conversion from changing capture provenance on
checkout. No helper working byte changed during the accepted captures.

Actual commands (run from `E:/VSCode/Flatcam/MikroCAM-reference-data`, using
`E:/VSCode/Flatcam/MikroCAM/.venv/repro-b/Scripts/python.exe` for both parent and child):

```powershell
python tests/reference/capture.py --engine legacy8994 --source ../FlatCAM-reference-8994 --python E:/VSCode/Flatcam/MikroCAM/.venv/repro-b/Scripts/python.exe --manifest tests/reference/boards/manifest.json --config tests/reference/capture-config.json --output .venv/capture-v2-legacy8994-1 --timeout-seconds 300
python tests/reference/capture.py --engine evo --source ../MikroCAM-reference-evo --python E:/VSCode/Flatcam/MikroCAM/.venv/repro-b/Scripts/python.exe --manifest tests/reference/boards/manifest.json --config tests/reference/capture-config.json --output .venv/capture-v2-evo-1 --timeout-seconds 300
```

Each command was repeated with output suffix `-2`; both runs exited 0 for complete validated
artifacts. The earlier 128 MiB resource-limited Evo capture was not admitted. The accepted
Altium Evo capture has all five stages ok, 185,830,678 decoded JSON bytes, 40,790,151 gzip
bytes and 989,620 G-code lines.

Real integration exposed a geometry representation mismatch: legacy batches a MultiPolygon,
Evo stores individual polygons. Four failing tests demonstrated false differences from zipping
batches. The report now compares their physical unions, preserving raw batch counts only as
diagnostics and leaving CNC/tool sequence comparisons separate. **114 focused tests pass**;
independent review found no defect. The actual geometry-set probe measured Altium isolation
symmetric difference 0.3945467210 mm² and round-drill difference 0.4307060293 mm² between the
baselines at explicit 1e-6 mm / 1e-6 mm² tolerance; neither is silently widened to a match.
