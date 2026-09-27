# Implementation Plan: SVG drill candidates

**Branch**: `018-svg-drill-detection` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

## Summary
Dedicated File/Import action loads bounded SVG with the established physical importer. Resolved
white-fill facts accompany each visible element. Core validates circular evidence, associates
white openings with concentric nonwhite pads, excludes conflicts and groups an explicit selection.
A modal review dialog lists physical candidates; a bridge creates a complete Excellon atomically.

## Technical Context
Python 3.13.13 x64; existing NumPy/Shapely and PyQt6, no new runtime dependency.
Windows 11 desktop; pure core pytest, bridge tests, offscreen Qt smoke and real desktop lifecycle.
Storage: existing Excellon/project format only. Review is transient; no migration required.
Limits: existing 16 MiB/10,000 elements/500,000 coordinates, at most 1,000 circular evidence items;
200 notices; no background worker or hardware I/O. The explicit evidence cap bounds pairwise work.
Circle fit operates in mm with 0.01 mm radial/chord tolerance (also 2% relative), 0.02 mm concentric
centre tolerance and 0.01 mm tool grouping. Native circle/ellipse uses exact transformed axes;
path needs >=12 distinct perimeter points, monotone full angular coverage and no large angular gap.
No generic geometry conversion, clipping or slots in this slice.

## Constitution Check
All eight gates YES before research and again after design:
1. Core owns immutable geometry/evidence/grouping; importer only retains resolved white-fill fact;
   bridge owns file/legacy creation; UI only gathers/renders/calls.
2. One short menu hook in appMain.py, aggregate legacy growth below +50.
3. Concrete functions/records/dialog, no abstraction or dependency added.
4. Existing SVG transforms and mm source are authoritative; conversion once at Excellon boundary;
   existing format only; host defaults copied once by its existing object factory.
5. Domain/record/geometry tests first; analytic fixtures and old reference suite retained.
6. No machine/laser behavior, controller or transport involved.
7. Neo MIT behavior trace recorded with immutable upstream commits and retained notice; independently
   implement bounded detection rather than copying a module; no FlatCAM-Plus code accessed.
8. Three stories and 36 tasks.

## Project Structure
- `mikrocam/core/svg_drills.py`: frozen records, circle evidence and detection (split fit helper if needed).
- `mikrocam/core/drill_groups.py`: selection validation and deterministic tools.
- `mikrocam/core/svg_models.py`, `mikrocam/importers/svg_style.py`, `svg_document.py`: paint fact.
- `mikrocam/bridge/svg_drills.py`: bounded load and atomic complete Excellon.
- `mikrocam/ui/svg_drills.py`: parent-owned transient review dialog/action.
- `tests/test_svg_drill*.py`, authored `tests/reference/svg-drills.svg`, `tests/smoke_svg_drills.py`.
- Specs include research, data model, contracts, quickstart, tasks and final validation.
Modules <=600 lines, functions <=80, public APIs annotated.

## Complexity Tracking
No exceptions. A dedicated source-file workflow avoids trusting historical reports after geometry edits.
