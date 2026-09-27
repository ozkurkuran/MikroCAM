# Data model: reviewed Geometry circles

DrillHole(center_mm:Point2D, diameter_mm:float) in core/drill_groups.py is a strict frozen physical
hole used by both SVG and Geometry grouping. Existing DrillTool(diameter_mm,centers_mm) stays intact.

GeometryDrillCandidate(center_mm,diameter_mm,source_id,role,duplicate_count=0): frozen, finite XY
within1e9mm, positive diameter<=1e9mm, nonempty UTF8 source_id<=256, role exterior/interior/closed-line,
exact duplicate_count integer0..10000. Keep first source identity when equivalent contours collapse;
duplicate_count and review notices disclose the collapse. No automatic drill-intent field.

GeometryDrillReview(source_name,source_units,geometry_sha256,candidates,notices): frozen;
nonempty UTF8 name<=256, explicit MM/IN, lowercase64hex fingerprint, exact tuple<=1000 candidates,
exact tuple<=200 nonempty UTF8 notice strings<=512chars. Candidate source IDs unique. Review is
immutable and ephemeral; it is never inserted into a project file.

Input sources are exact tuple(label,geometry-tree) pairs, <=10000. Bridge supplies one geometry label
for single mode or deterministic type-qualified tool labels for multi mode. Geometry trees may be
nested lists/tuples of Shapely planar geometries. Core traversal is bounded; no generator/dict fallback.
Fingerprint includes name, units, source labels, tree structure and validated original WKB, before
mm conversion. Shape objects are immutable; review contains measurements only, not host references.
UI separately retains the chosen owner reference; collection membership must still match it.
