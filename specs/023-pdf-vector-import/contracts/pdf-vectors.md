# PDF vector contracts

## Reader boundary

bridge.pdf_reader.inspect_pdf_bytes(data:bytes,name:str)->PdfDocumentInfo and
read_pdf_page(data:bytes,name:str,page_index:int)->PdfProgram.
Require1..16MiB, valid%PDFheader,strictpypdf6.19.0reader, reject encrypted input. Public
apply_configuration context bounds declared/decompressed/array streams to8MiB, page-treeentries512,
depth32, disables legacyglobalconfig handling; reset on exit. Read from BytesIO, never external paths.
No actions/scripts/attachments are executed. PagefactsincludeinheritedMediaBox/CropBox, cropintersection
withmedia, normalizedquarterturnRotate andpositiveUserUnit(default1). Rejectinvalidboxes/units,
>128pages, malformedtrees/references. Read onlyselectedpagecontent; noflatteningallrawstreams.
Rejectselected-pageannotations/transparencyGroup. Contents arrays mustrespectjoint8MiB decodedcap.
Translate ContentStream.operations to strictPdfCommand,<=50000. Strings/names and numeric arrays
bounded asmodels; unsupported complex operands/operatorsraiseValueError. Ignore unusedresources.
Do/Form/image,gs/transparency,sh,patterns,visibletextshow(Tj,TJ,apostrophe,quote),inlineimagesand
marked-contentvisibility constructs are unsupported and clearly rejected. No filter silently drops them.

## Page frame

core.pdf_frame.pdf_page_frame(page:PdfPageInfo,options:PdfOptions)->tuple[Affine2D,Point2D].
Optionsindexmustmatch. Pickeffectivecrop/media, subtractboxorigin andmultiplyUserUnit*25.4/72.
ApplyPDFclockwisepagerotation:0(x,y),90(y,W-x),180(W-x,H-y),270(H-y,x),withappropriateW/Hswap.
Optionalcropmustlieentirelywithinorientedphysicalpage; subtractcroplowerleft. Optionalflipreflects
y aboutcroppedheight exactlyonce. Returnbasephysicalaffine and final(width,height). Initialclipis
finalrectangle(0,0,width,height), so no out-of-page material or cropedge-onlylinesbecomeCAMpaths.

## Pure operator interpreter

importers.pdf_program.render_pdf_program(program:PdfProgram,options:PdfOptions)->PdfGeometryResult.
Grammarfiniteoperatorsq/Q,cm,w,J,j,M,d,m,l,c,v,y,h,re,S,s,f/F/f*,B/B*,b/b*,n,W/W*,g/G,rg/RG,k/K.
PDFmatrix(a,b,c,d,e,f) maps tocore(a,c,b,d,e,f); composecurrentouter*newinner. q/Q savesmatrix,
line/color/clipstate (not currentpath);64depth, no underflow/unbalancedstack. Pathpointsaretransformed
atconstruction. Independentm/re subpaths neverjoin. hclosesonlycurrentsubpath;paint/resetpathonce;
fillimplicitlyclosesitscontours;strokeclosesonlyexplicitlyclosedpaths. Cubicc/v/y flattenphysical
controlhull to<=0.005mm viaexistingflatten_cubic; limits inheriteddepth24/percontour100000.
Linewidthpositive,cap0butt/1round/2square,join0miter/1round/2bevel,miterlimit1..1000(default10).
Dashemptyarray/phase0only;hairlinewidth0 andnonemptydashrejected. Opaquegray/RGB/CMYKvalues0..1;
whiteclears,othercolorsmark. Bpaintsfillthenstroke. BasicW/W* saves pendingcliprule and appliesits
compoundfillclipafterthecurrentpaintingoperator/n, thenresetspath. Clip state followsq/Q.
Nonzero/evenodd fill, strokeunderfullaffine andcurveapprox reusecore SVGgeometryhelpers without
SVGpaint/pad/drill inference. Error messages identifyPDFcontext. SupportedemptytextsetupBT/ET,
Tf/TL/Tc/Tw/Tz/Tr/Ts/Td/TD/Tm/T* canbevalidatedwithoutpaint;nested/unbalancedtextstatefails.
No path/paintoperatorsinsidetextmode. Actualtextshow is rejected. ri/i may beacceptedonlywith
validatedstandardintent/flatnessargs, withoutalteringfixedphysicalapproximation.

core.pdf_geometry owns geometric state/helpers and cumulative budgets. Materialispolygonal,
opaque paintorderunion/difference withcurrentclip. Rejectinvalid/singular/nonfinitegeometry,
empty finalmaterial, over10000subpaths/500000sample+outputpoints. Preflightoverlayswithbounded
edgecounts/STRtreeintersectioncandidates<=32768 and cumulativeedgework<=2000000; postcheckoutput
pointbudget. Existingcompoundfilllimits256rings/2048complexsegments/faces apply. Noimplicitrepair.
Finalsourcefacts/options/frame/bounds/counts/SHA generatePdfImportReport. Hashgeometryusinglength
framedWKB in deterministictupleorder; PdfGeometryResultvalidatesreport-agreement.

## Host and persistence

bridge.pdf_import.load_pdf_review(path:Path|str,options:PdfOptions)->PdfImportReview readsboundedbytes,
callsreader/interpreterandreturnsimmutableexactsource. inspect_pdf_file(path)->PdfDocumentInfo.
create_pdf_geometry(app,path,review,name)->object validatesprintablename/currentMMIN, rereadsand
recomputesfreshreview, comparesfullreportandgeometryWKB; noforgedreviewmaterialisused. Insidenormal
GeometryinitializerverifyboundedfilesourceSHA beforewritesandagainbeforesuccessreturn. Usefresh
physicalpolygonsconvertedonce toobj/currenthostunits;multigeoFalse,normalfactorytools/defaultsretained,
toolsolid_geometrysyncedwhereappropriate. source_file=source_bytes.decode('latin1'),pdf_import=codec
reportdict. Onlyexactinitializedfactoryresultaccepted;failureinitializerreturnsfail/wrapperValueError.
Noexistingobject/defaultmutation. read_pdf_report(owner)->PdfImportReport|None isstrictoptionalcodec
withoutfileI/O; invalidstoredvalue raisesValueError handledbyUI;oldNoneisvalid.
GeometryObjectaddspdf_importNone,ser_attrsentryandshortui.attach_pdf_report hook. Noprojectformat
change. Historicalreportincludespage/crop/flip/physicalbounds/identity andneverclaimscurrentgeometry.

## UI

ui.pdf_import.PdfImportDialog(app,parent=None),parentownedmodal. Controls path_edit,browse_button,
inspect_button,page_combo,box_combo,crop_check,xmin_edit,ymin_edit,xmax_edit,ymax_edit,flip_check,
analyse_button,report_view,name_edit,create_button,status_label. Defaultboxcrop,flipFalse,cropoff.
inspectloadsdocumentfactsandpagechoices. analyseusesexplicitselectedpage/options,showsphysicalreview.
File/page/box/crop/flipeditsclearpriorreviewanddisablecreate; noneiscreatedautomatically. Creator
guarded;failurekeepsdialogopen;actualsuccessaccepts. Expose document:PdfDocumentInfo|None and
review:PdfImportReview|None. open_pdf_import(app) invokedbyshortFileImportmenu'PDF vector page...'.
ui.pdf_report.PdfReportSection andattach_pdf_report(owner) showoptionalplaincollapsedhistoricalreport,
ownedbyobjectUI,hideoldmissingandclearstaleoninvalidrecord. KeepSVGImportReportAPIunchanged.

## Verification

AnalyticReportLab/pypdf-authoredpages,compressed/uncompressed/arrays,inheritedboxes/UserUnit,
rotated/sheared/pathsubpaths/whitepaint/compoundholes/basicclips/crop/flip;unknowncontentatomicfails;
byte/decode/tree/operator/state/point/overlaycaps;MM/INfactory;stale/forgedreview;Latin1exactPDFsource
andreportprojectroundtripwithoutfile;actualdesktopselectedpage/crop/flip→Geometry→DXFexport/reparse
→projectreopen. LegacyPDFtestsandallpriorfeaturesremainrequired. Nophysicalvendorclaims.
