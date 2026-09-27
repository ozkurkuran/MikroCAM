# Implementation Plan: SVG scale, transforms and solid strokes

Branch `016-svg-scale-transforms`, 2026-09-27. Three stories, at most 38 tasks. Roadmap 009 is
complete; 015 merges before this feature is delivered. No new dependency or persistent schema.

## Summary and technical context
CPython 3.13, existing Shapely 2 and svg.path pins, Windows 11, existing Qt desktop. Pure core owns
strict source-coordinate affine math, lengths, paths and filled/stroked geometry. The importers
domain parses bounded XML into immutable resolved element records using stdlib only. The bridge
reads bounded files, adapts the pinned svg.path parser into core paths and translates final mm
geometry into host units exactly once. A thin UI adapter reports errors/notices through existing
application channels; camlib.Geometry.import_svg uses that adapter and retains existing object/tool
population, as does the separate Gerber override. No direct legacy-to-domain dependency, extra
renderer framework or new import panel.

Source coordinate transforms are not CAM-to-machine Placement. Their result is mm geometry that
subsequent Placement consumes normally. Unsupported semantics are rejected, never silently repaired.
Initial explicit scope: root viewBox with none/meet alignment, absolute units, supported transforms,
primitive/path geometry, local use references and finite inherited paint. Slice/nested viewports,
external CSS/resources, fonts/text, clipping/masks/markers/dashes/non-scaling strokes are explicit
errors pending appropriate later slices or outlining in the source editor. Basic fill winding for
simple rings is necessary to preserve fill while adding stroke; general self-intersecting compound
path/Illustrator handling remains 019. Existing direct legacy helper tests remain unchanged.

## Constitution Check
| Gate | Result |
| --- | --- |
| I layers | Yes: core geometry/math, stdlib domain, svg.path and I/O only in bridge, thin UI adapter |
| II legacy | Yes: one adapter shared by Geometry/Gerber seams; replace old extraction |
| III simplicity | Yes: concrete SVG records/functions, existing dependencies, no generic renderer |
| IV truth | Yes: mm boundary, one accumulated source mapping, existing downstream Placement |
| V tests first | Yes: analytic units/transforms/strokes and host atomicity before implementation |
| VI safety | Yes: bounded offline parser, no machine I/O or new execution path |
| VII license | Yes: independent implementation; existing dependency pins/licenses, primary facts |
| VIII slices | Yes: three stories and no more than 38 tasks |

No complexity exception. Every new module <=600 lines, function <=80, public APIs annotated.

## Structure and ownership
- core/svg_models.py, svg_transform.py: immutable contracts and source-coordinate math (Sol).
- core/svg_paint.py: primitive paths and solid fill/stroke expansion (Sol after contracts).
- core/svg_curves.py: bounded curve flattening with physical-space tolerance (root).
- importers/svg_document.py, svg_style.py: bounded XML/reference/style traversal (root).
- bridge/svg_import.py, svg_paths.py: bounded read/adaptation/host-unit conversion (root).
- ui/svg_import.py: notice/error adapter; minimal Geometry/Gerber seams and UTF-8 source read (Sol).
- Dedicated unit/integration/reference tests and tests/smoke_svg.py; no frozen harness edits.

Implementation follows the frozen contract, tests first. File ownership is exclusive; root stages
and commits. Validate focused analytic/fault tests, full suite/import/growth, actual desktop imports,
then final-head Windows CI. Keep source bytes and all frozen reference artifacts unchanged.
