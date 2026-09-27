# Data model: reviewed manufacturing files

Strict frozen dataclasses in core/manufacturing_models.py. Exact tuple containers, exact nested
records, no bool-as-int, nonempty strict UTF8 text. Names max256bytes, paths4096bytes, details512bytes,
SHA256 exactly64lowerhex. Constants MAX_MANUFACTURING_FILES=64, MAX_MANUFACTURING_BYTES=16777216,
MAX_MANUFACTURING_TOTAL_BYTES=67108864. FORMATS=('gerber','excellon'),
ROLES=('F.Cu','B.Cu','PTH','NPTH','Edge.Cuts','Other'); proposals may additionally be 'unknown'.

- ManufacturingEvidence(origin:str,format_hint:str='unknown',role_hint:str='unknown',
  units_hint:str='unknown',detail:str=''): origin contents/metadata/filename, hints valid enums,
  unit MM/IN/unknown, nonempty detail. Evidence can contain unknown hints to explain ambiguity.
- ManufacturingInspection(source_name:str,source_sha256:str,byte_count:int,format_hint:str,
  role_hint:str,units_hint:str,evidence:tuple[ManufacturingEvidence,...],issues:tuple[str,...]=()):
  bytes1..16MiB,0..32 evidence,0..20issues, each512bytes, enums as above. Shape validation here;
  classifier determines meaning. Known Other remains distinct from unknown.
- ManufacturingFile(path:str,source_bytes:bytes,inspection:ManufacturingInspection|None,error:str=''):
  regular-file path is checked in bridge; record requires bounded nonempty text. Success requires
  immutable bytes1..16MiB, exact inspection bytecount/SHA and empty error. Failed row requires
  inspectionNone, bytesb'', nonempty error<=512bytes. Source bytes never enter report codec.
- ManufacturingAssignment(source_index:int,kind:str,role:str,output_name:str): index0..63;
  kind known format, role known ROLES, trimmed printable outputname UTF8max256bytes. Gerber permits
  every role; Excellon permits PTH/NPTH/Other only. Public validate_assignment(kind,role) handles this.
- ManufacturingReview(files:tuple[ManufacturingFile,...],assignments:tuple[ManufacturingAssignment,...]):
  files1..64 unique path strings, total sourcebytes<=64MiB. Assignments1..64 distinct valid indices,
  only successful files, unique output names casefolded. Input assignment order is preserved.
  Same-basename or same-content distinct files are legal; the UI exposes their identities.
- ManufacturingReport(inspection:ManufacturingInspection,kind:str,role:str,parsed_units:str,
  units_origin:str): confirmed compatible assignment, parsed_unitsMM/IN, units_originexplicit/parser.
  explicit requires matching inspection.units_hint; parser is required when source hintunknown.
  Original source name/hash/evidence plus chosen role and actual pre-host-conversion units persist.

core/manufacturing_codec.py report_to_dict/report_from_dict: schema_version1 plus report fields,
exact keys at every level, fresh JSON list/dict containers, strict enum/UTF8/64KiB bound. No paths,
bytes, object refs or project-global state. None is handled in bridge as old/missing, not by codec.

Bridge-only frozen ManufacturingReceipt(source_index:int,owner:object|None,error:str): success
has actual factory object and empty error; failure has None and nonempty bounded error. Object
names can be changed by normal collection publication; UI reads owner.obj_options['name'] after
queued publication instead of guessing a name. Receipts are never serialized into core reports.

UI transitions: uninspected -> inspected/editable -> reviewed -> importing -> per-row imported or
failed/pending. Any editable source/assignment change invalidates review. Imported rows are locked,
deselected and excluded from later review; a new review is required for remaining rows. During
the single worker all editing/close is disabled. A failure stops iteration; earlier objects remain.
