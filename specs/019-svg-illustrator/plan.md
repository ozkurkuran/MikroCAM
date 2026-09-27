# Implementation Plan: Illustrator SVG appearance

**Branch**: `019-svg-illustrator` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

## Summary
Extend the established physical SVG import with offline XMP fallback, bounded simple embedded
style rules, visible layer evidence, exact bounded compound winding and local clip applications.
Keep original paths/source text; render clipped material before reports/host publication.

## Technical Context
Python3.13, existing NumPy/Shapely/PyQt6, no new dependency. Windows desktop plus pure pytest.
Existing source16MiB, elements10000, depth64, generated coordinates500000/100000 per element.
CSS<=65536chars/256 selectors; clip chain<=8, definitions<=64 shapes, aggregate generated budgets
include clip geometry. Clip overlay preflight<=2048 segments/32768 intersecting pairs;
application count times element count<=500000 bounds application-wide work before traversal.
Complex fill topology<=2048 segments, <=32768 intersecting segment pairs,
<=2048 polygonized faces and <=2000000 face/segment winding operations. Simple disjoint/nested
rings retain the existing fast path and limits. No unbounded repair/union fallback.
Report schema2 adds percentage source-unit representation; read/migrate strict schema1 unchanged
reports. Original dimensions remain source evidence, effective viewport attributes are separate.
Project object format is otherwise unchanged. Public functions annotated, <=600/80 line limits.
XMP evidence is confined to direct root SVG/unnamespaced metadata subtrees; original attrs remain
unchanged. CSS collection ignores metadata and foreign styles while preserving legitimate defs
styles. Declaration grammar/properties/local clip refs validate at compilation; only winning
paint is validated in actual material context. Clip silhouettes ignore paint/stroke/opacity.

## Constitution Check
All eight gates YES before research and after design:
1. XML/CSS/XMP traversal stays importers; geometry/winding/clip intersections and records stay core;
   bridge coordinates dependency path decoding; UI remains existing thin adapter/report.
2. No new legacy logic; use existing import seams, expected legacy growth0.
3. Concrete helpers for existing needs, no plugin abstraction or new dependency.
4. One existing mm/affine/viewport authority. Original/effective metadata distinct. Report2 has
   schema1 migration tests; no unrelated project-schema rewrite or second machine transform.
5. Core/domain regressions first; analytic input/reference checks, no hardware dependency.
6. No new machine/laser behavior. Clipped shapes are excluded from drill inference explicitly.
7. Independently adapt MIT Neo behavior with existing retained notice and immutable trace; no
   module copy/FlatCAM-Plus. Standards linked in research rather than guessed.
8. Three stories, 39tasks.

## Project Structure
- core/svg_models.py: bounded clip applications/layer/effective-root records.
- importers/svg_metadata.py: bounded XMP page fallback/provenance.
- importers/svg_css.py: offline simple-selector cascade, used by svg_document.py.
- importers/svg_document.py and svg_style.py: visible layers and local clip expansion.
- core/svg_fill.py: simple/complex fill winding; svg_paint.py delegates fill.
- core/svg_clip.py: physical intersection and bbox frames; bridge/svg_import.py orchestration.
- core/import_report.py and codec: original percentages/schema2 and migration.
- core/svg_drill_circles.py: refuse clipped evidence, never infer a full source circle.
- tests/test_svg_illustrator*.py, original fixture and tests/smoke_svg_illustrator.py.
- docs/SVG_IMPORT.md and specs validation retain precise support/evidence limits.

## Complexity Tracking
No exceptions. Clip definitions may not themselves reference clipping; masks/filters/external CSS
are rejected. Ancestor/child applications and userSpaceOnUse/objectBoundingBox remain supported.
A degenerate objectBoundingBox application is rejected explicitly instead of approximated.
