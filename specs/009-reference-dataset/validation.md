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
