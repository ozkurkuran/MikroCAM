# Data model: bounded PDF vectors

Strict frozen records in core/pdf_models.py. Exact immutable tuples, nonboolean finite numbers,
strict bounded UTF8 text and exact nested records. Export constants MAX_PDF_BYTES=16777216,
MAX_PDF_STREAM_BYTES=8388608, MAX_PDF_PAGES=128, MAX_PDF_OPERATORS=50000,
MAX_PDF_POINTS=500000, PDF_TOLERANCE_MM=0.01. Point2D/Affine2D reuse core placement types.
Bounds tuples are(minx,miny,maxx,maxy), finiteabs<=1e9 and strictly positivewidth/height.

- PdfPageInfo(index:int,media_box:Bounds,crop_box:Bounds,rotation:int,user_unit:float):
  index0..127, effectivecropcontainedinmedia,rotation0/90/180/270,user_unitpositive<=75000;
  all physical page dimensions/coordinates remain within1e9mm after units.
- PdfDocumentInfo(source_name:str,source_sha256:str,pages:tuple[PdfPageInfo,...]):
  nameUTF8nonempty<=256bytes,64lowerhex,1..128pageswithindexexactenumeration.
- PdfOptions(page_index:int,box_mode:str='crop',crop_mm:Bounds|None=None,flip:bool=False):
  index0..127,box_modecrop/media,strictbool; crop boundedpositive withnonnegativeorigin.
- PdfCommand(operator:str,operands:tuple): operatornonemptyASCII<=16,operands<=8;
  eachoperand exact finiteint/floatabs<=1e9,UTF8name/string<=128bytes,or exacttuple<=64finite numbers.
  Grammar/arity/operator support are validated by the interpreter, not this shape record.
- PdfProgram(document:PdfDocumentInfo,page_index:int,commands:tuple[PdfCommand,...]):
  indexinactualpages,commands<=50000.
- PdfImportReport(source_name:str,source_sha256:str,page_count:int,page:PdfPageInfo,
  options:PdfOptions,viewport_mm:Point2D,matrix_mm:Affine2D,bounds_mm:Bounds,
  geometry_count:int,path_count:int,point_count:int,geometry_sha256:str,
  precision_mm:float=0.01,notices:tuple[str,...]=()):
  page_count1..128,pageindex/optionsagree; positiveviewport<=1e9; nonsingularfiniteaffine;
  nonemptygeometrybounds; geometry_count1..500000,path_count1..10000,point_count1..500000;
  geometry_sha25664lowerhex; precisionexact0.01;notices<=200UTF8strings<=512bytes.
- PdfGeometryResult(report:PdfImportReport,geometry_mm:tuple[BaseGeometry,...]):
  nonemptyboundedimmutablevalidplanarfinitepolygonmaterial,<=500000coords,<=1e9mm;
  count/bounds/pointcount and geometrySHA agree withreport (hashlengthframedoriginalWKB).
- PdfImportReview(source_bytes:bytes,result:PdfGeometryResult): exactbytes1..16MiB,
  SHA matchesresult.report.source_sha256. No file/path/host reference in core.

Report codec stores schema_version1 plus report fields as fresh JSON containers, nested page/options
records, no geometry/sourcebytes; strict exactkeys/types/schema/64KiB bound. Source_file contains
lossless Latin1 PDF bytes separately. Review is ephemeral; only report and normal Geometry persist.
