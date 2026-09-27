# Research: reviewed Excellon merge

## Decision: current tools and explicit units are authoritative
ExcellonObject.merge (around line1377) concatenates tools and geometry, rounds diameters, copies
last-source options/units/zeros and does not regenerate source_file or check overlaps. Mixed units
therefore cannot safely use this path. Inspect tools[tooldia, drills, slots] and obj.units directly;
solid_geometry, source_file and units_found are caches/history. Existing project serialization stores
tools/units and Excellon source text. No source reparsing or inferred unit fallback is appropriate.

## Decision: preserve straight slots and exact diameter groups
A tool can contain round drill Points and slot endpoint pairs. Dropping slots would silently change
the manufacturing result. Add one strict physical ExcellonTool record that can contain either kind;
keep DrillTool API unchanged and adapt its actual SVG/Geometry callers into the shared creator.
The existing create_geometry populates destination tool data from destination.default_data. State
that new objects use normal current defaults; do not inherit arbitrary last-source machining settings.

## Decision: exact duplicates, analytic capsule conflicts
Use exact normalized physical diameter/coordinate equality for deduplication. Reversed endpoints
identify the same straight slot, retaining the first orientation. A nonzero similarity tolerance was
considered and deferred: nearby holes or differing diameters must not silently move or change size.
Round holes are zero-length centre segments; slots are nonzero segments. The distance between their
centre segments/points must be at least the sum of radii. Shapely distance avoids tessellated-buffer
underestimation and works for drill/drill, drill/slot and slot/slot. Tangency is allowed consistently
with existing drill grouping. Reject malformed/3D/nonfinite or degenerate slots instead of repair.

## Decision: bounded immutable review and guarded publication
Maximum64 sources,1000 total input tools and1000 total operations. At most499500 pair checks; retain
first200 conflict details plus exact total, so conflict truncation cannot permit creation. Retain all
removed duplicates and complete source-to-output tool map. Hash original bounded tool IDs, diameters,
point WKB and units/name before physical conversion. The bridge re-snapshots owners and recomputes
review equality at both factory checkpoints, preventing forged or stale measurements. No controller,
new schema, external code copy or dependency. Existing legacy merge remains available independently.

## Export precision
Existing exporter writes METRIC tool diameters with2 decimals and INCH with4, plus configured
coordinate decimals/format. Tests must use configured quantization; never claim exact exported
floating-point identity. Normal project persistence should preserve unquantized operations exactly.
