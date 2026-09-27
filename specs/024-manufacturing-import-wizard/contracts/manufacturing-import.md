# Manufacturing import contracts

## Pure classification

importers.manufacturing_classify.inspect_manufacturing_bytes(data:bytes,name:str)->ManufacturingInspection.
Validate immutable source1..16MiB/nameUTF8max256bytes. SourceSHA uses exact bytes. Recognize
Gerber contents from real FS/MO/aperture command markers, Excellon from M48/tool/unit headers;
ignore ordinary comment text for format signatures. Filename extensions gbr/ger/gtl/gbl/gko
suggest Gerber, drl/xln/exc suggest Excellon; tap is ambiguous without content. Conflicting
non-unknown format hints yield unknown plus an issue. No CNC execution or content conversion.

Read complete Gerber TF.FileFunction markers including compatible G04 #@! comments and Excellon
semicolon #@! equivalents. Cap metadata detail fields512UTF8bytes/evidence32. Copper,L1,Top→F.Cu;
Copper,Ln,Bot→B.Cu; Copper,Ln,Inr→Other. Require positive bounded integer layers and validarity.
Profile,P/NP→Edge.Cuts. Plated,i,j,PTH[,Drill/Rout/Mixed]→PTH;
NonPlated,i,j,NPTH[,Drill/Rout/Mixed]→NPTH; Blind/Buried, mask/legend/Other→Other.
Unrecognized/malformed FileFunction yields unknown and an issue. Distinct recognized role
evidence disagreement also clears role proposal; malformed metadata cannot be hidden by a filename.
Filename whole tokens F_Cu/F.Cu, B_Cu/B.Cu, Edge_Cuts/Edge.Cuts, PTH, NPTH and gtl/gbl/gko
extensions provide explicit reasons. No substring PTH-in-NPTH match, geometry-derived plating,
automatic Other for unknown, or silent metadata precedence. Case-insensitive filename matching;
standard metadata spelling is exact. Repeated identical evidence is deduplicated.

Unit markers Gerber MOMM/MOIN and legacy G71/G70, Excellon METRIC/INCH and M71/M72 yield MM/IN.
Missing/conflicting units are unknown with a visible parser-assumption issue. No scale conversion
occurs here. Evidence/issue order deterministic, hash/name make same-content files distinguishable.

## Gerber command boundary

importers.gerber_statements.gerber_statements(data:bytes)->tuple[str,...] decodes Latin1 exactly,
splits complete ordinary `*` commands and `%...%` blocks, preserves complete AM macro bodies,
splits combined non-AM extended statements into individually wrapped blocks, and removes only
TF/TA/TO/TD attribute statements. Ordinary G04 comments are retained/ignored as comments, including
metadata comment variants, without discarding adjacent drawing commands. Whitespace outside
commands is ignored, unfinished/malformed delimiters fail. Bound100000commands,1MiB/statement.
Never copy the legacy parser; feed these statements to existing Gerber.parse_lines.

## Files and review

bridge.manufacturing_import.inspect_manufacturing_files(paths:tuple[str,...])->tuple[ManufacturingFile,...].
Require1..64paths; resolve canonical paths, deduplicate preserving first occurrence. Each must be a
regular file; boundedread cap+1. Per-file OSError/size/classifier errors yield failed rows with bounded
plain error text. Total successful bytes<=64MiB or fail the inspection atomically. Same-basename
and same-hash distinct paths remain. No URL/archive/directory traversal. User source files unchanged.

review_manufacturing_files(files:tuple,assignments:tuple)->ManufacturingReview validates immutable
records and user-confirmed known assignments, including explicit Other. It does not silently fill
unknown roles. Each selected successful file is reread and reclassified; require exact bytes and
inspection equality before returning review. Source errors say inspect/review again.

import_manufacturing_review(app,review)->Iterator[ManufacturingReceipt] checks all selected files
again before creating any object. Reject invalid/replaced/forged inspection/bytes. Then import in
assignment order, yielding actual initialized owner or failed receipt. Stop at first failure;
remaining rows are pending. UI excludes prior successes on subsequent reviews. No rollback.

Each initializer guards current source hash before and after assignments, parses immutable reviewed
bytes and requires successful nonempty finite valid planar material. Gerber parse_lines return
None/drill accepted; fail/defective/unknown result becomes initializer'fail'. Excellon parse_lines
mustreturnNone then create_geometry mustnotfail and mustcontain operation material. Rejectempty/
invalid returned material. Gerber artwork retains Gerber kind even if layer role is PTH/NPTH.
Persist exactsourcebytes via Latin1 source_file and strict manufacturing_source report before
secondguard. Preserve normal factory tool/options defaults; do not recreate tools outside parser.
Normal AppObject.new_object performs one source-unit→host-unit conversion. Current hostunits must
be MM/IN and remainconsistent. Factory exceptions/sentinel/different-object returns are errors.

read_manufacturing_report(owner)->ManufacturingReport|None has no file I/O; missing/Nonevalid,
malformedstoredvalueValueError. Short GerberObject/ExcellonObject init+ser_attrs+UIhooks preserveoldprojects.

## UI and worker

ui.manufacturing_import.ManufacturingImportDialog(app,parent=None),parent-owned modal,
setAcceptDropsTrue. add_paths(paths),inspect_files(),review_selected(),import_selected() publicslots.
Controls add_button,inspect_button,review_button,import_button,table,status_label,close_button.
Table columns include checkbox/source (fullpath tooltip),formatcombo,rolecombo,units/evidence,
outputname and outcome. Expose files tuple,review None|ManufacturingReview,imported_indices:set[int].
add/drop onlycollectlocalpaths; explicitinspection reads. Duplicatedcanonicalpathsignoredwithnotice;
fileerrorrowsvisibleuncheckeddisabled. Unknown validrowsremaineditable and selected untilresolved.
Repeatedbasenames/hashesshowwarningswithoutdiscardingrows. Everyeditinvalidatesreview.

Review collectsselectedknowncompatibleassignments and revalidates sources; importonlyenabledafter
successfulreview. One app.worker_task emits a worker that consumes the bridge receipt iterator;
Qt signals deliver progress and finished to the owning dialog. Lockedit/closewhilebusy, keepdialog
alive, returnallreceipts evenonfailure. Queued object publication precedes progress fromsameworker;
read actualownername onUI delivery. Importedrowslocked/deselected, failurevisible, laterrowspending;
newreviewrequiredforretry. No automatic reopen/reimport or silent fallbackparser.

open_manufacturing_import(app) gets short FileImportaction'Production file set...'. Existingcanvas
dropbehaviorunchanged; wizardhasitsownmultipledroptarget. ui.manufacturing_report exposes
ManufacturingReportSection andattach_manufacturing_report(owner), collapsedhistoricalplainfacts,
hidemissingoldreports/clearinvalidrecords, samecomponentusedbyGerberandExcellon.

## Verification

AuthoredGerber/Excellon + licensedexistingCADcorpus: compactX2+drawsamephysical line, macros,
conflictingroles/kinds, missingunits/plating, PTHvsNPTH, innercopper, tapambiguity, boundedbytes/
commands, duplicatepaths/names/content, sourcechanges before/duringimport, parserdefective/failure,
normalMM/INdefaults, workerstop/retry/no-repeat, Latin1source+reportsprojectroundtrip, actualdesktop
multi-drop→review→fourroleobjects→projectreopen. Fullsuite/architecture/growth/finalCIrequired.
