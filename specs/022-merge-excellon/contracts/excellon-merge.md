# Excellon merge contracts

## Pure review
`core.excellon_merge.review_excellon_merge(sources:tuple[MergeSource,...])->ExcellonMergeReview`.
Strict2..64unique source names;<=1000inputtools/operations. Traverse sources in given order, tools in
snapshot order, drills then slots in original order. Equivalent key is exact(diameter,kind,position)
for drills or exact(diameter,kind,sorted endpoint pair) for slots. Preserve first operation orientation
and record every removal. Exact diameter groups sorted ascending become sequential1-basedtools;
within each output tool retain first-encounter order, separately drills and slots. Map every input
tool to its output tool even when all its operations were duplicates. No rounding or average.

Check each retained operation pair using physical Point/LineString distance compared strictly to
(d1+d2)/2. Report same-centre for unequal round holes at identical positions, overlap otherwise;
exact tangency allowed. First200details plus full conflict_count, no partial-positive early return.
Invalid inputs raise ValueError; valid conflicting input returns a review with creation blocked.
Final `validate_excellon_tools` uses the same distance rule and rejects any conflict.

## Host snapshot/guard
`bridge.excellon_merge.snapshot_excellon(owner:object)->MergeSource`.
Require kindexcellon, explicit trimmed printable name, currentMM/IN, tools exactdict1..1000.
Keys exactintabs<=1e18 or nonemptyUTF8str<=240bytes, stablelabels int:value/str:value sorted lexical.
Each tool exactdict with positivefinite tooldia and drills/slots list/tuple. Require both keys (normal
host model supplies them), totaloperations1..1000 per source; emptytools rejected. Drill entries
exact nonempty valid planar ShapelyPoint; slot entrieslist/tuplelen2 such points with distinct endpoints.
Check bounded counts before converting/hashing. Hash name,units,typedlabels,original diametervalue,
original pointWKB, operationtype/order/structure in an unambiguous length-framed stream. Exclude
source_file/solid_geometry/tool.data from geometry authority; never mutate/read external files.
Normalize every physical number once to mm. Missing units, invalidtooldata, nonfinite,3D,degenerate
slots, bounds andunsupportedtoolkeys fail entire snapshot. No cachefallback.

`load_excellon_merge(owners:tuple[object,...])->ExcellonMergeReview` requires2..64distinct identities
and names, snapshots each then pure review. `verify_excellon_merge(app,owners,review)->None` checks
collection.get_by_name(each source_name) is exactowner and recomputed fullreview equalsreview. Stale,
replaced,removed,renamed/unit/tool/point changes or forgedreview raiseValueErrorwithanalyse-again.
`create_excellon_merge(app,owners,review,name)->object` rejectsconflicts then delegates slotfactory
withsourceguardthat verifiesboth beforedestinationwrite andafterlocalexportbeforepublication.

## Shared factory
Add `bridge.excellon.create_excellon_operations(app,tools:tuple[ExcellonTool,...],name,*,source_guard=None)`.
Validatefinaltools,existingname/unitsrules; oneMMtohostconversion,completegeometry/localexport,
normaldestinationdefaults,exactinitializedobjectreturn andexistingtwoguards. Generalized initializer
sets both drills(Point) andslots(tuplePoint,Point). Keep `create_excellon_tools` publicAPI validating
existingDrillTool thenadaptingintonewtoolrecords; noSVG/Geometrybehaviorchange or secondfactorybody.

## UI
`ui.excellon_merge.ExcellonMergeDialog(app,owners:tuple[object,...],parent=None)` parentownedmodalfixedsources.
Controls analyse_button,source_label,tools_table,map_view,duplicates_view,conflicts_view,name_edit,
create_button,status_label. ReviewstartsNone. Analyseclearsstaleview thenload; displayphysicaltool
sizes/counts,completeinputmapping,removedduplicates andblockingconflictcount/details asplaintext.
Createenabledonlyvalidreviewwithoutconflicts+printablename. Explicitclickguardedcreation;failurekeeps
open;successacceptsonlyactualobject. Showdestinationusescurrentdefaults; noautomatedmergeonopen.
`open_excellon_merge(app)` obtainscollection.get_selected(),requiresallselectedExcellon2..64 (never
silentlyfilters). ShortPluginsaction'Review Excellon merge...' inappMain. No sourcemutation/controller.

## Required validation
Exactduplicatesanddifferentdiameterssamecentre; reverse/crossing/parallel/tangentslots; drill-slot;
MM/INsources/output; datatype/limits; sourceidentity/contentchangesatbothguardpoints; fullreview
forgery; sourceentirestate/defaultspreservation; actualExcellonexportparser slots andprojectpersistence;
actualdesktopexplicitselected2sources→review→newmerge→export/reparse→save/reopen. ExistingSVGand
Geometryfactorybehaviormustpassunchanged; exportedprecisionfollowslegacyconfiguredquantum.
