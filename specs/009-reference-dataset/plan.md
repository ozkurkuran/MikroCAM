# Implementation Plan: PCB reference dataset
**Branch**: `009-reference-dataset` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

## Summary / Technical Context
Pure comparison functions live in `mikrocam/core/reference_compare.py`; developer tooling
under `tests/reference/` validates corpus/provenance, invokes unchanged applications in
isolated subprocesses and reads/writes strict compressed JSON1 artifacts/reports.
CPython 3.13 x64, stdlib and existing Shapely/NumPy/pytest. Windows 11 primary, no GUI/hardware.
No new dependencies, product UI, settings or generic backend framework.

Pinned baselines: `legacy8994` = `6ba378bca139aa306f8c94f09461a98f95d3c75b`;
`evo` = `d0a86cf4f1ac41a206b20f316d4a29f28a93bbff`. Sibling detached worktrees
`FlatCAM-reference-8994` and `MikroCAM-reference-evo` are read-only sources. Capture refuses
dirty/wrong revisions; current capture requires its explicitly declared clean revision.
All normalized output coordinates are mm. Both baselines are retained even when different.
CLI tolerances are required explicit finite nonnegative `distance_mm` and `area_mm2`.
Capture API calls, explicit machining values and IN/repeat feasibility are probe-verified
in research.md; formal codec/config freeze precedes harness. No guessed fallback settings.
Core bounds: WKB64MiB decoded/geometry, paths200000, vertices2000000; developer decoded
gzip JSON128MiB/artifact. Exact tool records preserve diameter/multiplicity and ordered drill/slots.

## Constitution Check
| Gate | Result | Evidence |
| --- | --- | --- |
| I layers | Yes | Product comparison core-only; unchanged-engine capture is developer test tooling, not runtime host logic. |
| II legacy/+50 | Yes | No legacy edits or baseline patches. |
| III/VII simplicity/deps | Yes | Plain functions/data and existing deps; no plugin/backend registry. |
| IV single source | Yes | Hashes, explicit config, once-only mm conversion; schema1 manifest/capture/report. |
| V tests first/offscreen | Yes | Comparator mismatch/unit/error tests precede code; subprocess capture without Qt GUI. |
| VI hazards | Yes | Evidence hazards only; no motion/emission. |
| VII provenance | Yes, admission gate | Every input needs audited redistribution terms and original notices before inclusion. |
| size | Yes | Three stories, 26 tasks; module <=600/function <=80 lines. |
Pre/post-design: no exceptions. Pending admission is not a license approval.

## Project Structure
```text
mikrocam/core/reference_compare.py
tests/test_reference_dataset.py
tests/test_reference_capture.py
tests/test_reference_compare.py
tests/reference/boards/manifest.json
tests/reference/boards/<board-id>/<original inputs and notices>
tests/reference/capture-config.json
tests/reference/reference_data.py
tests/reference/capture.py
tests/reference/capture_worker.py
tests/reference/compare.py
tests/reference/goldens/{legacy8994,evo}/<board-id>.json.gz
```
`reference_data.py` owns strict developer codecs/provenance; capture orchestration and
concrete engine calls are split coherently, not through a general framework. Temporary
current/reproduction outputs and reports live outside goldens. Existing synthetic analytic
fixtures remain useful but do not count toward authentic-board admission.

## Phases / Complexity Tracking
Audit and probe first; test schemas then admit inputs; test isolated capture then freeze
actual two-baseline artifacts; test mismatch/error comparator behavior then implement
core/CLI; compare current against each baseline and record results. No automatic golden
overwrite. A fresh output directory and explicit review are required for new captures.
No complexity exception. Raw G-code remains audit text; ordered parsed-path comparison
does not expand into a lexical interpreter or machine preflight.
