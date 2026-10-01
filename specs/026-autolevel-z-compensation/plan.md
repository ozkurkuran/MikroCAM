# Implementation Plan: Auto-level Z compensation

**Branch**: `026-autolevel-z-compensation` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

## Summary
Complete map bilinear surface queries, shared-placement offline compensated canonical G-code,
linear/arc cell subdivision, independent preflight/PreparedJob validation and explicit UI review.

## Technical Context
CPython3.13.x, stdlib core, existing PyQt6 UI and pytest/pytest-qt. Windows11 primary.
No new dependency/storage schema. Reuse immutable ProbeMap schema1 JSON; output ordinary G-code.
Bound16MiB/250000 output lines, 200 preview lines, cooperative cancellation per generated piece.

## Constitution Check (pre/post design)
1. YES - pure core geometry, bridge file I/O, thin asynchronous UI; legal layer imports.
2. YES - existing preflight composition only, no legacy growth.
3. YES - concrete feature helper/worker, existing real/Fake Machine path; no new abstraction/dependency.
4. YES - mm, existing Placement, stored map G54; no format migration or duplicate transform.
5. YES - core/bridge/UI tests precede implementation, analytic hardware-free fixtures.
6. YES - hazard analysis, fresh derived review, existing single-owner start/stop/Fake coverage.
7. YES - independent mathematical implementation, no copied source or new license requirement.
8. YES - three user stories, 23 tasks. All gates remain YES after independent design audit.

## Project Structure
`core/autolevel_surface.py`: validated settings, digest, bilinear interpolation and cell crossings.
`core/autolevel_paths.py`: bounded exact-endpoint line/arc tessellation and cell refinement.
`core/autolevel_precision.py`: serialized/float32 chord error certificate.
`core/autolevel.py`: result, canonical generation, lineage, review/frame and precision verification.
`bridge/autolevel_files.py`: atomic separate G-code export.
`ui/autolevel_worker.py`, `ui/autolevel_panel.py`: concrete cooperative preparation, current-input
binding, bounded preview, map load/settings/confirmation/save/transfer; preflight integration.
`tests/test_autolevel_surface.py`, `test_autolevel_core.py`, `test_autolevel_files.py`,
`test_autolevel_ui.py`, `smoke_autolevel.py`: test-first evidence.

## Audit decisions
Surface-error contract is along emitted linear chords; arc XY approximation has its own bound.
Require effectively equal arc endpoint radii; original analytic arc extents remain inside map.
Horizontal feed cannot begin at a different uncompensated Z: reject and request vertical plunge.
Split each chord at grid boundaries; bilinear midpoint error is exact there. Reserve budgets for
serialized/float32 endpoints and certify actual resulting chords against map cells/tolerances.
Reject precision/resource/staleness failures, do not clamp/extrapolate. Preserve S/T/output before
motion, dwell once, M2/M30 after motion. Normalize feeds once. M0/M1/M7 rejected explicitly.

## Complexity Tracking
No exception. Separate concrete modules/functions remain within600/80line budgets.
