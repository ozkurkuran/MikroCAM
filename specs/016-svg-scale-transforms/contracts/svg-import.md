# SVG import contracts

## Limits and source coordinates
No public persistence format. All values/records are immutable. Source bytes <=16 MiB, strict UTF-8
(with optional BOM); reject DOCTYPE/entity declarations before parsing. <=10000 XML elements,
<=64 element depth, <=32 reference depth, <=10000 expanded drawable elements. Numbers <=64 lexical
characters and finite/nonbool, local/final coordinate magnitude <=1e9. Transform text <=4096 chars,
<=128 operations; finite coefficients <=1e12 and nonzero finite determinant. <=500000 generated
points/document, <=100000 points/element, <=256 closed rings/element. Fail before unbounded expansion.
CURVE_TOLERANCE_MM=0.01; curve flattening and round stroke tessellation each use half this budget.

Affine2D reuses the existing core.placement tuple convention `(a,b,d,e,xoff,yoff)`:
x'=a*x+b*y+xoff; y'=d*x+e*y+yoff. SVG matrix(a,b,c,d,e,f) maps to `(a,c,b,d,e,f)`.
compose_affine(outer,inner) means outer(inner(point)). Source import affine is distinct from the
existing downstream CAM-to-machine Placement, which is not changed or duplicated.

## core.svg_models
Public constants MAX_SVG_BYTES=16777216, MAX_SVG_ELEMENTS=10000, MAX_SVG_DEPTH=64,
MAX_SVG_REFERENCE_DEPTH=32, MAX_SVG_POINTS=500000, MAX_ELEMENT_POINTS=100000,
MAX_SVG_RINGS=256, CURVE_TOLERANCE_MM=0.01.
Frozen SvgNotice(code:str,message:str,element_id:str=''): bounded code<=64/message<=512/id<=256.
Frozen SvgPaint(fill:bool=True,stroke:bool=False,width:float=1.,linecap:str='butt',
linejoin:str='miter',miterlimit:float=4.,fill_rule:str='nonzero'):
strict booleans, finite width in[0,1e9], cap butt/round/square, join miter/round/bevel,
miterlimit finite in[1,1000], fill_rule nonzero/evenodd.
Frozen SvgPath(points:tuple[Point2D,...],closed:bool=False): >=2 bounded finite exact tuple points,
<=MAX_ELEMENT_POINTS; closed paths require >=4 coordinates and exact first==last. No implicit repair.
Frozen SvgViewport(width_mm:float,height_mm:float,matrix:Affine2D,notices:tuple[SvgNotice,...]=()):
positive finite dimensions<=1e9 and validated matrix.
Frozen SvgElement(element_id:str,kind:str,attributes:tuple[tuple[str,str],...],matrix:Affine2D,
paint:SvgPaint): kind path/rect/circle/ellipse/line/polyline/polygon; bounded ID, unique string attrs.
Frozen SvgDocument(source_name:str,source_sha256:str,viewport:SvgViewport,
elements:tuple[SvgElement,...],notices:tuple[SvgNotice,...]=()): bounded name<=256, exact hex SHA256,
<=10000 elements, notices<=200. Attribute values remain source facts, no mutable XML crosses layers.
Frozen SvgRendered(paths_mm:tuple[SvgPath,...],geometry_mm:tuple[BaseGeometry,...],
notices:tuple[SvgNotice,...]=()): valid finite planar Shapely geometry, bounded generated coordinates.
Frozen SvgImportResult(document:SvgDocument,rendered:tuple[SvgRendered,...]): one result per element,
<=500000 total generated path/geometry coordinates. geometry_mm property flattens geometry tuples;
notices property combines bounded document/render notices. No source or host object is mutated.

## core.svg_transform
parse_svg_length(text:str)->float: exact complete number plus optional px/mm/cm/in/pt/pc suffix;
unitless and px are local user units; absolute suffixes use CSS 96px/in equivalents. Reject %, em/ex,
unknown suffixes, nonfinite/trailing text. Values may be negative for coordinates.
parse_svg_numbers(text:str)->tuple[float,...]: complete SVG comma/whitespace number list, including
signed decimals/exponents; no ignored garbage. Callers validate count and positivity.
validate_affine(matrix:Affine2D)->None, compose_affine(outer,inner)->Affine2D,
apply_svg_point(matrix,point)->Point2D, affine_scale_bound(matrix)->float (finite Euclidean/Frobenius
upper bound for physical error amplification, excluding translation).
parse_svg_transform(text:str|None)->Affine2D: identity for absent/empty; complete transform list;
translate1/2, scale1/2, rotate1/3 (degrees), skewX/Y1, matrix6. Reject singular/collapsed mappings.
resolve_svg_viewport(attributes:tuple[tuple[str,str],...])->SvgViewport:
root width/height use length*25.4/96; absent viewBox means px-to-mm identity scale. viewBox has four
numbers with positive width/height. Both dimensions absent may use viewBox width/height as px;
one absent derives via viewBox aspect ratio; emit inferred-size notice. Without viewBox require
both dimensions. Default xMidYMid meet; support none and all nine alignments with meet. Reject slice,
unknown/defer syntax and unresolved root units. Matrix includes negative viewBox origin and margins.

## Domain and bridge
importers.svg_document.parse_svg_document(source:bytes,source_name:str)->SvgDocument:
bounded stdlib XML traversal, namespace-local SVG tags, immutable records. Compose viewport/parent/
element matrices once; local use x/y translation precedes referenced-node transforms. Only local
href/#id or xlink:href; unique IDs, no cycles/external refs. Unused definitions/metadata are not drawn.
Unsupported nonempty CSS, nested svg/symbol viewport, text/fonts, image/script, clip/mask/filter/marker,
dash/non-scaling stroke, unresolved percentages or geometry-affecting style fail explicitly.
Presentation attributes inherit; inline style overrides; explicit inherit uses parent values.
Basic display:none/visibility:hidden and zero opacity produce no material; fractional opacity,
paint servers and compositing are not inferred. Solid colors indicate positive material, not a
color-dependent boolean subtraction; a notice documents this CAM policy. Preserve original attrs.

bridge.svg_paths.element_paths(element:SvgElement,tolerance_local:float)->tuple[SvgPath,...]:
use existing pinned svg.path only at bridge for path syntax; adapt line/Bezier/arc components into
bounded core curve flattening. Separate Move/Close subpaths. Primitive geometry uses the core helper.
No legacy transform, root scale or font inference. All local lengths normalize before geometry.
bridge.svg_import.import_svg_bytes(source:bytes,source_name:str,*,flip:bool=True,
object_type:str='geometry')->SvgImportResult: parse, construct paths, render per element, enforce
whole-document budgets before returning. Apply optional flip once about viewport physical height.
Geometry may retain otherwise unpainted open centrelines with an explicit CAM notice; Gerber omits
them and rejects empty solid output. Painted open paths implicitly close for fill, without changing
original centreline/closed metadata. No source modifications or partial result on errors.
load_svg_file(path:Path|str,*,flip=True,object_type='geometry')->SvgImportResult reads at most cap+1.
host_geometry(result:SvgImportResult,units:str)->list[BaseGeometry] converts MM/IN exactly once.

## Geometry core
core.svg_curves exports flatten_cubic(start,c1,c2,end,tolerance)->tuple[Point2D,...],
flatten_quadratic(start,control,end,tolerance)->tuple[Point2D,...],
flatten_arc(center,radii,rotation_deg,start_deg,sweep_deg,start,end,tolerance)->tuple[Point2D,...].
All are pure, bounded and finite; include exact endpoints, use tolerance-aware subdivision/sagitta
with depth/point guards. Stroke curvature uses the same physical tolerance budget independently.
core.svg_paint.primitive_paths(kind:str,attributes:tuple[tuple[str,str],...],
tolerance:float)->tuple[SvgPath,...] handles rect (including rx/ry), circle, ellipse, line, polygon,
polyline with local length normalization. path kind belongs to bridge. Zero dimensions are empty;
negative dimensions are errors. No open-path closure except polygon/closed primitives.
render_svg_paths(paths:tuple[SvgPath,...],paint:SvgPaint,matrix:Affine2D,*,
retain_centerlines:bool=False)->SvgRendered:
fill nonzero/evenodd for bounded valid simple rings, including implicit closure for open paths with
>=3 distinct points; reject self-intersecting rings until compound-path scope. Expand stroke on
source paths before affine transformation with cap/join/miterlimit. Union fill and stroke per element.
Preserve transformed paths for later import report/drill features. No cross-element boolean color
compositing. Output finite valid planar geometry, all resource excess is explicit failure.

## Host integration and validation
ui.svg_import.import_svg_geometry(filename,object_type,units,flip,app)->list[BaseGeometry]|None:
call bridge; emit bounded source notices via existing app log/inform; return None and error on failure.
camlib.Geometry.import_svg replaces old parse/scale/text extraction with this thin adapter, keeps
existing flatten/merge/tool population, and returns 'fail' before mutating host on failure. No
parameter/default-tool behavior is changed. GUI and Tcl share the seam; no new menu/panel.
Exact shared signatures precede delegation; root coordinates all commits. Analytic unit/transform,
fill/stroke, malformed/resource, mm/IN host and atomicity tests precede implementation, then full
reference/import/growth and actual desktop Geometry/Gerber + save/reopen + old journeys.
