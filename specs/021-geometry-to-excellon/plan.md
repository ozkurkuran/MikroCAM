# Implementation Plan: Geometry circles to Excellon

Branch021-geometry-to-excellon | Date2026-09-27 | [Spec](spec.md)

## Summary
Review bounded circular contours in the current Geometry object's authoritative geometry. Preserve
boundary role and explicit selection; share existing circle-fit mathematics, diameter grouping and
Excellon construction with SVG drills, keeping SVG-specific white-opening rules unchanged.

## Technical Context
Python3.13, existing NumPy/Shapely/PyQt6, no dependency. Windows desktop and pure pytest. Core uses
strict immutable candidate/review records and current-geometry fingerprints, not source-file hashes.
No persistent schema is added: reviews are ephemeral, final Excellon uses existing persistence.
Object units are explicit MM/IN. Convert current geometry to mm once; no source reparse, flip or
placement transform. Factory converts selected physical tools once to its explicit output units.
Bounds:10000 visited geometry/container parts, depth64,500000 coordinates,100000 per contour,
1000 candidates and200 notices. Coordinates limited to1e9mm. Circle fit retains existing radial
and segment-midpoint residual min(0.01mm,2%radius), >=12 distinct points, simple closed ring,
monotone full revolution and max45degree gap. No repair or bbox-only inference.

## Constitution Check
All eight gates YES before and after design:
1. Pure circle mathematics, grouping and geometry review in core; host source/factory in bridge;
   UI only collects selection and displays evidence. No cross-domain or Qt/core imports.
2. One short Plugins menu hook in appMain, below aggregate50line budget; no new legacy logic.
3. Shared concrete helpers have two actual users (SVG and Geometry), no registry or new dependency.
4. Existing units, transforms, defaults and Excellon format retained; ephemeral review is not persisted.
5. Tests first for extraction/fitting/refactor/grouping/fingerprint/factory; existing SVG behavior locked.
6. No controller connection or drilling. Explicit unchecked selection and stale/overlap guards.
7. Independent extension of existing MikroCAM code. No external module copy/merge or restricted source.
8. Three stories, <=40tasks.

## Project Structure
core/circle_fit.py extracts shared fitting mathematics; svg_drill_circles.py keeps SVG gates.
core/drill_groups.py adds strict DrillHole and group_drill_holes; existing SVG selection delegates.
core/geometry_drill_models.py immutable candidates/review; core/geometry_drills.py handles bounded
source traversal/fingerprint/fit/dedup; split helper module if needed, <=600/80 limits.
bridge/excellon.py owns shared creation from grouped tools; existing svg_drills.create_drill_object
retains its API and delegates. bridge/geometry_drills.py selects authoritative owner geometry and
revalidates object membership/name/units/mode/content before publication.
ui/geometry_drills.py is a parent-owned review dialog, opened from Plugins using current Geometry.
tests/test_geometry_drill*.py, shared-helper regressions and smoke_geometry_drills.py.

## Complexity Tracking
No exceptions. Multi-tool Geometry uses per-tool solid_geometry, matching GeometryObject.plot;
top-level cache is not mixed in. Empty/missing/unsupported inputs report clearly. General contours
are candidates only; concentric different-sized candidates may coexist, but conflicting selections
cannot create Excellon. Tool merging across source objects remains022.
