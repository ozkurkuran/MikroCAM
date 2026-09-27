# Geometry circles to Excellon

Select one Geometry object, then open **Plugins → Geometry circles to Excellon...**.
Choose **Analyse current Geometry**, review the physical measurements and boundary roles,
check only the intended holes, enter a new object name and create the selected drills.
Nothing starts selected. The summary shows the resulting tool diameters and hole counts.

The review uses current geometry, including edits and transforms. Single-geometry objects
use `solid_geometry`; multi-tool objects use each tool's `solid_geometry`, just as the
Geometry renderer does. A stale top-level cache is ignored in multi-tool mode. Input units
must explicitly be MM or IN. The bridge converts to physical millimetres once; the normal
Excellon factory converts to the destination units once. No source file is reparsed and
no additional flip or placement transform is applied.

Circular polygon exteriors, polygon interiors and closed lines are candidates with distinct
role labels. A circular contour alone does not establish drilling intent. The fit requires
at least 12 distinct points, a simple complete ring, one monotone revolution, no angular gap
over 45 degrees, and both radial and chord-midpoint residuals within the smaller of 0.01 mm
and 2% of the radius. Open paths, points, ellipses and insufficiently resolved contours are
excluded. Invalid, nonfinite, nonplanar or excessive input fails the entire analysis.

Duplicate evidence within 0.02 mm in centre and 0.01 mm in diameter collapses to its first
representative, with a visible duplicate count. Comparisons always use that representative,
so a chain of near neighbours cannot extend the tolerance. These absolute tolerances can
collapse distinct very small contours: inspect dimensions and duplicate counts before
selection. Different concentric sizes outside that tolerance remain separate alternatives.
Selected diameters form groups with total spread at most 0.01 mm; the representative tool
diameter is their mean. The final grouped footprints must not overlap.

The review is temporary. Its fingerprint covers source name, units, typed source/tool
labels, container structure, primitive type and original geometry bytes. Source identity
and a fresh review are checked inside Excellon initialization, before any destination
changes and again after local export, before publication. Renaming, replacing, removing or
editing the source requires another analysis. Source geometry, tools, source text and
machining settings are preserved. Factory/export failure does not publish a partial object.

Analysis is bounded to 10,000 nodes, nesting depth 64, 500,000 total coordinates, 100,000
points per contour, 1,000 candidates, 10,000 duplicates per candidate and 200 notices. Coordinates and diameters are bounded
to 1e9 mm. Omitted notices are counted. No new project schema or dependency is introduced.

Circle fitting, grouping and Excellon construction reuse existing MikroCAM SVG-drill code;
SVG paint, pad and opening rules remain specific to SVG. This is an independent extension
of that code, without an external algorithm port. Tests cover analytic geometry, source
guards, normal Excellon export/reparse and project persistence. In-memory checks use
1e-6 mm; exported checks follow configured coordinate/tool precision and the existing
legacy inch-conversion roundoff. No physical drilling is performed by this workflow.
