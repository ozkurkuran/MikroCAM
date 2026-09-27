# Geometry drill contracts

## Shared mathematics and grouping
core.circle_fit.fit_closed_circle(points:tuple[Point2D,...])->tuple[Point2D,float]|None returns centre
and radius. Validate finite bounded points/count, require explicit complete closure; preserve the
existing normalized least-squares/radial/midpoint/winding/gap tests from SVG. Invalid records raise
ValueError; valid noncircles returnNone. svg_drill_circles._fitted delegates after its one-path/closed
gate, preserving native-circle and SVG material semantics.
core.drill_groups adds frozen DrillHole and group_drill_holes(holes:tuple[DrillHole,...])->tuple[DrillTool,...].
Require1..1000 exact holes, sort diameter/centre, total spread<=0.01 with existing1e-12roundoff,
mean diameter and sorted centres. Reject all footprint overlaps including coincident centres after
grouping. Existing group_drill_selection keeps exact SVGreview/index validation and delegates.
validate_drill_tools(tools:tuple[DrillTool,...])->None validates exact tuple/records, <=1000total
centres, finite bounds and nonoverlap; shared factory calls it without regrouping or altering tools.

## Pure current-geometry review
core.geometry_drills.review_geometry_sources(sources:tuple[tuple[str,object],...], source_name:str,
units:str)->GeometryDrillReview. Strict immutable source pairs with unique bounded labels; nested
geometry lists/tuples accepted. Iterative traversal caps10000 visited nodes/depth64/500000coordinates,
100000points per contour. Cyclic lists hit explicit depth/count budget, no unbounded recursion.
Reject invalid/nonfinite/nonplanar geometries, unsupported objects/units; valid empty/point/open/noncircle
components get bounded notices. Supported Polygon/MultiPolygon, LineString/LinearRing/MultiLineString,
GeometryCollection and Point/MultiPoint (points excluded) are traversed deterministically.
Fingerprint name+units+labels+tree structure+original WKB before physical conversion, stable for
unchanged input. Current coordinates converted once to mm; reject physical magnitude>1e9.
Propose polygon exterior/interior and closed-line contours only, source ID includes source label,
component ordinal and ring role/index. Deduplicate within centre0.02mm/diameter0.01mm against retained
first representative, never chain; preserve first measurement/identity and increment duplicate_count.
Different-sized concentric/overlapping candidates remain available for explicit choice; grouping
rejects incompatible selected footprints. Max1000 candidates; notices<=199plusomission marker.
core.geometry_drills.group_geometry_selection(review, indices:tuple[int,...])->tuple[DrillTool,...]
validates exactreview/unique1..1000in-rangeintegerindices, converts to DrillHole and delegates.

## Host authority and source guard
bridge.geometry_drills.load_geometry_review(owner:object)->GeometryDrillReview requires kindgeometry,
explicit trimmed source name, unitsMM/IN and exactboolmultigeo. Single mode uses owner.solid_geometry;
multi mode uses every tools entry's solid_geometry, with stable type-qualified bounded int/string
keys and labels. Reject missing geometry, unsupported tool keys or malformed tool dictionaries; never
fall back to a stale top-level cache. No mutation, defaults or source-file I/O.
verify_geometry_review(app,owner,review)->None requires current collection.get_by_name(review.source_name)
is owner, and a newly bounded review fingerprint/name/units matches. Source rename, replacement,
removal, mode/tool/path/unit change rejects with an analyse-again message.
create_geometry_drills(app,owner,review,indices,name)->object groups selection and delegates to
bridge.excellon.create_excellon_tools(app,tools,name,*,source_guard=None). The optional no-argument
source guard runs inside factory initialization before destination changes and after local source
export, before publication. Common factory preserves defaults, validates tools/name/current host
MM/IN, validates matching object units, converts mm once, completes create_geometry and export_excellon
local_use/use_threadFalse, then assigns source_file and returns. Failure returnsfail from initializer;
wrapper raisesValueError unless the factory published exactly its initialized object. Existing
bridge.svg_drills.create_drill_object retains its API and calls the shared factory with grouped tools.

## UI
ui.geometry_drills.GeometryDrillDialog(app,owner,parent=None) is parent-owned modal, source fixed
for this dialog. Controls: analyse_button, table(select/Xmm/Ymm/diametermm/evidence), name_edit,
create_button, source_label, notices_view, grouping_label, status_label. review startsNone;
analyse clears prior selection, obtains current review, lists unchecked candidates and notes roles.
Selection updates grouped summary; invalid/empty selection disables create. create_selected calls
guarded bridge creation, keeps dialog open on failure and accepts only an actual returned object.
open_geometry_drills(app) resolves collection.get_active(); no validGeometry reports a useful error.
A short Plugins menu action in appMain connects it. No controller, source edit, generic canvas picker,
reparse, independent scale/flip or implicit selection. Public strings plain text.

## Required validation
Analytic circles/holes/rings inMM/IN, rotation/uniformscale vs anisotropicellipse, duplicates/overlap,
open/coarse/selfcrossing/3D/nonfinite, nested/multi-tool stale-cache authority and all budgets.
Existing SVG fit/group/factory tests pass unchanged through extraction. Test source mutation at both
guard points, deleted/replaced owner, unit/name changes, defaults and all factory/export failures.
Actual desktop selectedGeometry review→selectedExcellon→export/reparse→projectsave/reopen, source
WKB/tool/default/source text unchanged. In-memory tolerance1e-6mm; exported tolerances follow the
configured coordinate/tool quantum plus existing legacy inch-conversion roundoff where necessary.
