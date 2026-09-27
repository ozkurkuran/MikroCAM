# Import report contracts

## Shared source facts (root-owned)
SvgDocument adds root_attributes:tuple[tuple[str,str],...]=() AFTER notices, validated by existing
validate_attributes. Domain fills it from original root.attrib, without changing existing attributes.
SvgImportResult adds flipped:bool=False AFTER rendered; strict bool. Bridge passes actual flip.
Neither change affects source mapping/geometry or the existing positional construction prefix.

## core.import_report (Sol)
Frozen ImportCoordinates(source_width:str|None,source_height:str|None,
source_units:tuple[str,str],view_box:tuple[float,float,float,float]|None,aspect_ratio:str,
viewport_mm:tuple[float,float],matrix_mm:Affine2D,flipped:bool).
Source tokens are trimmed <=128 chars; absent values None. Unit labels are exactly
absent/unitless/px/mm/cm/in/pt/pc (one per width/height).
Each present dimension parses as a positive supported length and matches its unit label;
an absent token requires the absent label. Unknown dimension facts remain explicitly modelable.
ViewBox magnitudes are finite <=1e9 with positive width/height; viewport positive<=1e9.
Existing validate_affine. Aspect resolved canonical
none or one of nine xMin/Mid/MaxYMin/Mid/Max meet strings. Strict tuple/bool/nonbool finite numbers.

Frozen ImportQuality(bounds_mm:tuple[float,float,float,float]|None,geometry_count:int,
valid_count:int,invalid_count:int,empty_count:int,open_paths:int,closed_paths:int,
precision_mm:float|None).
Exact nonbool integer counts 0..500000; geometry_count equals valid+invalid+empty. Bounds finite
<=1e9 and ordered min<=max; absent only when no nonempty geometry. Precision None means unavailable,
otherwise finite nonbool positive<=1mm. Counts describe atomic Polygon/LineString/Point components;
Multi/GeometryCollection recurse within existing coordinate limit. Empty geometries count once.

Frozen ImportReport(source_name:str,source_sha256:str,coordinates:ImportCoordinates,
quality:ImportQuality,notices:tuple[SvgNotice,...]=()). Name nonempty<=256, SHA lowercase64hex;
exact record classes and bounded immutable <=200notices.
build_import_report(result:SvgImportResult)->ImportReport derives root source tokens/units,
viewBox/aspect facts from validated root_attributes; missing recorded source facts are explicit error,
not guessed. Root mapping is result.document.viewport.matrix (includes root/viewBox and optional
flip); element mappings may differ. Material bounds in mm from existing geometry; never resample.
Count source paths using explicit closed flags, including implicitly filled open paths. Report
CURVE_TOLERANCE_MM and all result.notices, preserving truncation notices. No legacy/Qt/I/O.

## core.import_report_codec (Sol)
REPORT_SCHEMA_VERSION=1; MAX_REPORT_BYTES=1048576.
report_to_dict(report:ImportReport)->dict returns fresh JSON-safe schema1 structure.
report_from_dict(value:object)->ImportReport validates exact keys/types and constructs frozen records.
Top keys: schema_version,source_name,source_sha256,coordinates,quality,notices.
Coordinates/quality dictionaries use exactly their dataclass field names. Tuples encode as lists;
None remains null. Notice dictionaries use exactly code,message,element_id. Reject bool as version,
unknown versions/keys, nonfinite/count/matrix/text violations and oversize records; no coercion.
No migration of unversioned records: absence is handled at host boundary, other shapes are errors.
Canonical UTF8 JSON size (ensure_ascii=False,separators comma/colon,allow_nan=False) <=MAX_REPORT_BYTES.
Validate bounded container lengths/text before serializing to measure size. No JSON text I/O needed.

## bridge.import_report (root)
store_import_report(owner:object,result:SvgImportResult)->None builds/encodes and assigns
owner.import_report only after complete success. It never changes source/geometry/options/tools.
read_import_report(owner:object)->ImportReport|None reads optional owner.import_report; None/absent
means unavailable old/non-SVG data; malformed/newer payload raises ValueError. No reparse/file access.
Host Geometry/Gerber constructors default import_report=None and include field in existing ser_attrs.
UI SVG import adapter accepts optional report_owner=None; successful bridge result/host-unit
conversion precedes report assignment. Failed imports preserve any previous report and return fail.

## ui.import_report (Sol)
ImportReportSection(QtWidgets.QWidget): constructor(parent=None); set_report(report:ImportReport|None,
error:str='')->None. Read-only collapsed report with a toggle, summary text and plain multiline text.
Historical-evidence label is always clear. None => unavailable; error => bounded invalid/unavailable
message, never old content. Plaintext formatting for user names/notices. No imports/host/controller I/O.
Public toggle, summary_label, details attributes support smoke tests. details is QPlainTextEdit,
readOnly and bounded to the summary; no rich text. Expanding shows units/root tokens/viewBox/aspect,
viewport, six mapping coefficients, flip, mm material bounds/counts, open/closed paths, validity,
precision, SHA and notices. No editable controls or fake live validity status.
attach_import_report(owner:object)->None: called from each Geometry/Gerber set_ui after common UI
setup. Reuse one owner.ui.mikrocam_import_report widget in custom_box, read through bridge only.
No report => hide the section for ordinary/old objects. Invalid report => show unavailable diagnostic.
Valid report => show historical data. Report stays parent-owned; no global callbacks/worker/cache.

## Validation
Tests precede behavior; pure core without Qt, strict codec/old-field migration, no stale widget state,
plain markup, two distinct owners, failed import preserves previous data, actual project save/reopen.
No new runtime dependency, no machine path, no alteration of 016 geometry or frozen references.
