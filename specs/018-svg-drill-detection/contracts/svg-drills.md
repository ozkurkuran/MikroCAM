# SVG drill review contract

## Core
`SvgElement.fill_is_white: bool | None = None` retained by traversal. None is unknown/no active
fill; bool identifies resolved enabled fill. Existing paint/geometry behavior is unchanged.
`style_fill_is_white(style) -> bool | None` resolves currentColor and opaque supported colors;
white equivalence includes #fff/#ffffff, clamped rgb and hsl lightness. No fill -> None.

Frozen `DrillCandidate(center_mm: tuple[float,float], diameter_mm: float,
opening_id: str, pad_id: str)`; finite coordinates abs<=1e9, 0<diameter<=1e9,
nonempty IDs<=256, bool is never numeric.
Frozen `DrillReview(source_name: str, source_sha256: str, flipped: bool,
candidates: tuple[DrillCandidate,...], notices: tuple[SvgNotice,...])`;
name 1..256 UTF8, hash lowercase64, strict bool, <=1000 candidates, <=200 notices.
`detect_svg_drills(result: SvgImportResult) -> DrillReview` pure/unchanged geometry. Enumerates
circle/ellipse and single explicitly closed path only. Native axes must describe a circle after
full physical transform; path fit has >=12 unique points, no backward winding/self intersection,
angular gap <=pi/4, radial and segment midpoint errors <=min(0.01 mm, radius*0.02).
Concentric centres <=0.02 mm; pad contains opening plus 0.01 mm margin. White filled unstroked
opening, larger nonwhite filled circular pad. Bound circular evidence to1000 or ValueError;
unsupported/ambiguous candidates excluded with bounded explanatory notices. Equal duplicates use
centre <=0.02 mm and diameter <=0.01 mm; incompatible overlaps excluded, no silent size guessing.

Frozen `DrillTool(diameter_mm: float, centers_mm: tuple[tuple[float,float],...])`;
positive finite diameter<=1e9, nonempty bounded finite centre tuple <=1000.
`group_drill_selection(review: DrillReview, indices: tuple[int,...]) -> tuple[DrillTool,...]`:
nonempty <=1000 unique exact integer indices in range, deterministic input-order independent groups,
ascending diameter, group spread <=0.01 mm, arithmetic mean tool diameter, centres sorted XY.
Decimal boundary roundoff allows 1e-12 mm; proposed grouped diameters must not make holes overlap.

## Bridge
`load_drill_review(path: Path | str, *, flip: bool=True) -> DrillReview`: existing load_svg_file
then detect; exceptions propagate without changing host. No raw file kept after review.
`verify_drill_source(path: Path | str, review: DrillReview) -> None`: bounded reread and SHA256
match before creation; changed/missing/oversized files invalidate the review without reinterpreting it.
`create_drill_object(app: object, review: DrillReview, indices: tuple[int,...], name: str) -> object`:
validate selection/name (1..256 printable characters, trimmed nonempty) before factory. Factory
`new_object('excellon',name,initialize,...)` owns defaults/units. Initializer builds fresh tools
`{1: {'tooldia': ..., 'drills': [Point...], 'slots': [], 'solid_geometry': ...}}`, create_geometry,
source_file via app.f_handlers.export_excellon(..., local_use=obj, use_thread=False). Return fail
on creation/export failure before publication; bridge raises useful ValueError on factory failure.
All units converted once from mm, no settings edited or machine command emitted.

## UI
`SvgDrillDialog(app, parent=None)` parented modal dialog; `open_svg_drills(app)` opens it.
Public controls for tests: path_edit, browse_button, flip_check, analyse_button, table,
name_edit, create_button, status_label; `analyse()` and `create_selected()` slots.
Table checkboxes initially unchecked; columns Select, X mm, Y mm, Diameter mm, Evidence.
Source/hash, flip and tolerances visible, plain text notices. Changing path/flip invalidates review,
clears rows and disables create; selected rows only; successful creation accepts dialog; failure
stays with useful error and never invents success. GUI layer uses only bridge APIs/core records.
Creation first verifies current source bytes; failed verification clears review/selection and asks
for analysis again. This covers edits to a file without changing the path text.
One File/Import menu action, existing translation via gettext/builtins convention; no worker.

## Spec 041 amendment
core.svg_drill_circles.COINCIDENT_ENDPOINT_MM = 1e-6: a single open subpath whose end lies within it of
its start is closed at that point and must pass the unchanged fit (one turn of exactly 2*pi).
core.svg_drills.PAD_MARGIN_MM = 0.01. Without circular support, a nonwhite filled unclipped single
Polygon pad supports an opening when its centroid is <=0.02 mm from the centre, it contains the centre
and its boundary distance is >= radius + 0.01 mm; the smallest-area pad is reported. Centre and
diameter always come from the white circle; pads never become candidates.
