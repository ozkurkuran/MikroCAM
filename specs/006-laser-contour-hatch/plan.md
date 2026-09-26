# Implementation Plan: Laser contour and hatch

**Branch**: `006-laser-contour-hatch` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

## Summary
Core owns geometric feature classification, closed-outline validation, contour/hatch kernels
and immutable path/options values. The laser domain orchestrates kernels and existing
Placement. A host bridge snapshots Gerber metadata and publishes ordinary Geometry. A
thin PyQt6 dock collects explicit inputs and runs planning in a cancellable worker.

## Technical Context
CPython 3.13, existing Shapely and PyQt6 only. Three stories, 18 tasks. All geometry remains
mm; recipe/job schema 1 stays unchanged. The kernel limits candidate scan lines to 50,000
and emitted paths to 200,000, with cancellation checks between geometric operations.
Explicit outlines are limited to 500 rings before pairwise ambiguity checks.
Individual GEOS operations are not interruptible; shutdown waits for the active bounded
worker to finish before destroying it. No queued overlapping generations.

## Constitution Check
| Gate | Result | Evidence |
| --- | --- | --- |
| I: layers | Yes | Geometry in core; laser imports core/stdlib; host only bridge; thin UI. |
| II: legacy | Yes | One menu action/lazy UI hookup, target fewer than 10 added lines. |
| III/VII: simplicity/dependencies | Yes | Dataclasses/functions and concrete adapter; existing dependencies only. |
| IV: one source | Yes | mm, existing Placement and LaserJob recipe; no new persistence format. |
| V: tests first | Yes | Core/domain and bridge tests precede implementation; UI smoke covers integration. |
| VI: hazards/stop | Yes | Geometry-only hazards in spec; cancellation states and stale-result tests. |
| VII: provenance | Yes | Independent code and synthetic analytic fixtures; no external source port. |
| Feature size | Yes | Three stories, eighteen tasks. |

## Structure
`mikrocam/core/laser_paths.py`: path/options/feature values and validation.
`mikrocam/core/laser_features.py`: Gerber semantic region/explicit outline geometric helpers.
`mikrocam/core/laser_geometry.py`: contour and clipped angled hatch kernels.
`mikrocam/laser/__init__.py`, `planner.py`: request orchestration and one output placement.
`mikrocam/bridge/laser_cam.py`: concrete desktop adapter, snapshots and Geometry publication.
`mikrocam/ui/laser_cam.py`, `laser_worker.py`: translated controls and cancellable worker.
`tests/test_laser_{paths,geometry,planner,cam_bridge,cam_ui}.py`, analytic reference fixture,
and `tests/smoke_app.py` desktop extension.

## Complexity Tracking
No exceptions. Keep every new module <=600 and function <=80 lines. No AppTool subclass,
plugin registry, general task framework, new object type, new setting or device abstraction.
A QDockWidget avoids coupling to Evo's rebuilt plugin tab and detached-tab internals.
