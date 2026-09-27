# Research: current Geometry circle conversion

## Decision: reuse mathematics, preserve source-specific meaning
Existing core/svg_drill_circles._fitted supplies a conservative complete-circle fit. Extract its
mathematics into core/circle_fit.py with regression tests before changing the SVG delegate.
Do not reuse SVG fill/white/pad/native-element gates for Geometry; original native-circle metadata
has been lost after general editing and DXF conversion. Fit the actual current planar contour.
Alternative bbox/circularity-area scoring cannot distinguish ellipses/coarse polygons reliably.

## Decision: use the same authoritative geometry as the host
GeometryObject.plot uses tools[*].solid_geometry when multigeo is true, and solid_geometry otherwise.
Some transforms update both, but top-level data can be stale after tool editing. The bridge must
select one authority, never combine top-level and per-tool data or silently fall back from missing
tool geometry. Retain tool identity/part/ring role. Include source name, units, mode, tool labels and
exact current geometry content in a bounded fingerprint so edits/replacements invalidate review.
The current coordinate frame already includes edits/transforms. No source-file reparse or extra flip.

## Decision: reviewed intent and deterministic grouping
Offer circular exteriors, interiors and closed lines with role labels; points/open arcs/ellipses do
not become candidates. Deduplicate centres/diameters within existing0.02/0.01mm evidence tolerances
and report duplicate counts. Different concentric sizes remain visible alternatives; selected
footprints must not overlap after grouping. Start unchecked, group by total diameter spread<=0.01mm,
use mean diameter, preserve existing SVG selection results independent of selection order.

## Decision: share atomic Excellon boundary
Existing bridge/svg_drills completes tools, geometry and local-use export before factory publication.
Move that body into bridge/excellon.py; both callers use it. Validate tool payloads and preserve
factory defaults/host units. A source guard for Geometry runs inside initialization before mutation
and again before successful return, rejecting source edits/removal/replacement without publishing.
No new output format or source-object modification. Desktop checks normal export/project roundtrip
using configured output quantum, while in-memory mm checks remain tight.

## Scope and alternatives
A modal review of the active Geometry object is sufficient; no canvas editing, multi-object merge,
slots or circle repair. Existing regression/refactoring evidence replaces external algorithm ports.
No FlatCAM-Plus source read; no new dependency. Genuine manufacturing intent and physical drilling
are explicitly outside evidence provided by circle recognition.
