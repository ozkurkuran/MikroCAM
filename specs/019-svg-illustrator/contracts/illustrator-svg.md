# Illustrator import contracts

Existing physical import/load/UI APIs remain source compatible. No extra dependency or hardware I/O.

## Metadata and report
`resolve_page_attributes(root: ET.Element) -> tuple[tuple[tuple[str,str],...], tuple[SvgNotice,...]]`
in importers/svg_metadata.py returns effective root attrs and bounded provenance notices.
Original root attrs are never changed. XMP evidence must be below a direct root metadata child
in the SVG namespace or without a namespace; RDF wrappers inside it remain supported. MaxPageSize
elsewhere, including defs and foreign metadata, cannot supply physical scale. XMP structure uses
exact xmpTPg `http://ns.adobe.com/xap/1.0/t/pg/` and stDim
`http://ns.adobe.com/xap/1.0/sType/Dimensions#` namespaces; <=1 MaxPageSize, exactly one each
positive finite field <=1e9 mm after unit conversion, unit in supported
mm/cm/inch/in/point/pt/pica/pc/pixel/px plus case-insensitive long/plural names. Duplicate/invalid
metadata needed for fallback is ValueError; complete root dimensions may retain them with a warning.
Absent root dimensions may use valid XMP axes; percentage root dimensions require XMP and use its
page dimensions, not a guessed external viewport. Malformed absolute dimensions still reject.
Without XMP/percent, existing viewBox inference remains unchanged. Conflicting explicit dimensions
win with a notice, independently by axis. Preserve aspect mapping through resolve_svg_viewport.
`SvgDocument.viewport_attributes: tuple[tuple[str,str],...] = ()` added last, validated like root attrs.
Report builder validates viewport_attributes when present, still displays raw root dimension tokens.
ImportCoordinates source_units adds `%`; percentage token is a single finite positive percentage.
REPORT_SCHEMA_VERSION=2; encoder writes2; decoder accepts strict1/2, schema1 excludes percent tokens
and migrates into current records. Unknown versions/keys still reject. No new fields in persisted
report dictionary; notices describe XMP/layers. Old absent object report handling remains unchanged.

## CSS
Frozen `SvgCssRule(selector: str, declarations: tuple[tuple[str,str,bool],...], specificity: int,
order: int)` in importers/svg_css.py. `parse_stylesheets(root)->tuple[SvgCssRule,...]` compiles all
embedded SVG/unnamespaced style text offline, max65536chars and256 expanded simple selectors.
Metadata subtrees are pruned; foreign-namespace style elements are inert. Legitimate SVG styles
inside defs remain document-wide rules in source order.
`cascade_attributes(tag: str, attributes: dict[str,str], rules: tuple[SvgCssRule,...])->dict[str,str]`
returns a new attr mapping with winning presentation values encoded in inline style; raw source
attributes remain available for retained records. Support tag/*/.class/#id, comma lists and comments;
reject malformed, @rules, nested/escaped/compound/combinator selectors. Resolve precedence by
important flag, specificity, source order; inline normal outranks normal selectors, stylesheet
important outranks normal inline, inline important highest. Validate declaration grammar, property
names and local clip-path references at compilation. Validate paint semantics only for winning
values in the element's actual context; unused or overridden paint does not manufacture material
or fail a clip silhouette. Geometry/unsupported properties stay rejected. Existing direct resolve_style remains
usable. clip-path none/url(#localID) is noninherited; clip-rule inherited nonzero/evenodd.

## Source records and clip expansion
Frozen `SvgClip(application_id: str, source_id: str, units: str, matrix: Affine2D,
elements: tuple[SvgElement,...])`: nonempty IDs<=256, units userSpaceOnUse/objectBoundingBox,
validated reference-local-to-mm matrix; <=64 clip shapes with local matrices, no child clips.
`SvgElement.clips: tuple[SvgClip,...]=()` and `layer_path: tuple[str,...]=()` appended after
fill_is_white; clips<=8, layer depth<=64/each label1..256. Definition elements are not document material.
Original attrs retained. Clip definition transform composes before child local transforms; its own
ancestor styles supply clip-rule, not target style. Support basic shapes and local use of basic shapes;
reject text/groups/nested clipping inside definitions explicitly. Circle/curve source budgets apply.
Each clip application has a unique stable scope ID shared by affected flattened descendants.
CSS display:none suppresses subtree; visibility can be overridden; empty/hidden clip shape sets clip
all material out. Opacity/fill/stroke and stroke appearance values (including dash) are ignored
for clip silhouettes; inherited clip-rule controls fill. Unsupported winning paint on visible
material still rejects explicitly.
Local bbox clip coordinates are finite unitless numbers (percent length syntax supported as /100 in
this normalized frame); absolute-unit bbox lengths reject. Clip-chain/cycle/reference budgets apply.

## Geometry and orchestration
`fill_svg_paths(paths, rule)->list[Polygon]` in core/svg_fill.py delegates existing simple nesting,
then bounded polygonized signed winding for complex rings. Complex input<=2048 nonzero segments,
<=32768 intersecting segment pairs, <=2048 faces, <=2000000 face/segment operations, existing
100000 element output points. Original source orientation retained; implicit fill closure preserved.
No arbitrary snapping or validity repair. Stroke restrictions remain independently explicit.

`clip_application_matrix(clip: SvgClip, document: SvgDocument, rendered: tuple[SvgRendered,...])
-> Affine2D` computes reference/bbox-to-mm matrix from unclipped source path bounds. Bridge uses
this matrix together with each local shape matrix to derive physical curve tolerance before decoding.
`apply_svg_clips(document: SvgDocument, rendered: tuple[SvgRendered,...],
clip_materials: dict[str,tuple[BaseGeometry,...]]) -> tuple[SvgRendered,...]` in core/svg_clip.py.
Bridge constructs each unique application's physical clip material with existing path parser/renderer,
forcing fill with its clip-rule and no stroke. Core obtains unclipped target/group bounds from paths
in inverse application coordinates and composes bbox then reference matrix in the matrix helper.
The apply function unions physical definition shapes and intersects original material with every
application. Source paths are unchanged; empty output
is retained as empty geometry tuple, unsupported degenerate bbox is ValueError. Cap total clip and
result coordinate work using existing budgets; all visible clip fragments must remain valid/finite.
Preflight clip union/intersection overlays before GEOS work: <=2048 nonzero boundary segments,
<=32768 intersecting segment pairs. Bound clip application count times document element count
to <=500000 before application-wide traversal; existing generated-coordinate budgets also apply.
Bridge flips each application matrix once, never its local shape matrices twice. Cached applications
are local to one import only. No host publish until complete import success.
Circle evidence rejects elements with any clips with an explicit notice; later geometry conversion
may interpret final material separately. Reports measure clipped material while path counts remain
original source facts; emitted notices distinguish that historical source evidence.
