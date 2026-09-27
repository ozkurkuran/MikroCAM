# Research: manufacturing file review

## Existing host behavior

Read appHandlers/appIO.py open_gerber/open_excellon and appObjects/AppObject.py new_object.
Existing multi-select/drop paths enqueue independent per-file workers. They have no batch
transaction, and appIO success commonly returns None rather than an object. The normal factory
returns its initialized object, converts source units to current app units, then queues collection
publication. Its initializer must return `fail` to prevent publication; `defective` is returned
after publication, so a new bridge must translate that parser result to `fail` inside initialization.

The old main-window drop handler has independent extension checks. `.tap` belongs to both drill
and G-code lists. The new wizard owns its own drop target and dispatches one confirmed kind per
row. Existing drop behavior is not expanded or reused. One sequenced worker makes outcomes and
stop-on-failure order explicit; completed objects are retained. A group rollback would require
new host transaction machinery and could delete useful completed work.

Gerber.parse_file removes whole lines containing X2 attributes and splits ordinary commands.
It can discard drawing commands that share those lines. parse_lines accepts pre-split statements
and returns None, fail, defective or drill. The bridge will tokenize bounded immutable source
bytes, remove metadata statements only, preserve aperture-macro blocks and all drawing statements,
then use parse_lines. Metadata affects role evidence, not geometry or object conversion. Gerber
drill artwork remains Gerber; no automatic circle-to-Excellon callback is requested. Excellon
parse_lines reports failure directly; parse_file otherwise hides its return, so use parse_lines
and create_geometry before publication. Both parsers remain the existing geometry authority.

## Classification sources

The [Ucamco Gerber specification](https://www.ucamco.com/files/downloads/file_en/416/the-gerber-layer-format-specification-revision-2021-02_en.pdf)
defines FileFunction metadata for physical copper layers, plated/nonplated drill spans and board
profiles. Top is L1; an inner copper layer differs from either outer face. Metadata describes
purpose and does not transform artwork. [KiCad's X2 support note](https://www.kicad.org/blog/2016/11/Gerber-X2-Support/)
confirms that the producer can supply this layer metadata. These semantics support conservative
role proposals; the selected import still requires explicit review.

Read embedded Gerber `%TF.FileFunction,...*%` and compatible `G04 #@! TF...*` comments, and
Excellon `; #@! TF.FileFunction,...` comments. Recognize top/bottom copper, Profile and explicit
PTH/NPTH. Inner copper and other described purposes map to Other, never to an outer face. A
plated Blind/Buried span is Other, not PTH. Unknown or malformed metadata remains unresolved.
Filename tokens F_Cu/F.Cu, B_Cu/B.Cu, Edge_Cuts/Edge.Cuts, PTH/NPTH and extensions gtl/gbl/gko
are suggestions with visible reasons. Conflicts between independent evidence sources clear the
proposal. Generic .gbr/.drl and .tap alone never establish a layer or drill plating.

Excellon lacks a retained plating field and can infer units when no explicit marker exists.
Show explicit MM/IN evidence or 'parser assumption' before import; retain actual parsed units
and the source-unit policy in the historical report. Normal legacy coordinate-format defaults
remain in force. The wizard does not claim to validate or improve every legacy parsing rule.

## State, persistence and limits

Use immutable bounded bytes/inspection/assignment/review records. Up to64 files,16MiB each,
64MiB total, distinct canonical paths, bounded metadata and command lists. Read regular files
only; no archive/directory expansion or remote URL fetch. Failed reads remain visible unselected
rows. Same basename or same content in distinct files is retained with visible evidence.

Any edit invalidates the reviewed action. One worker prechecks all selected source bytes/facts,
then creates in order. First failure stops later rows. Completed rows are locked and deselected;
remaining rows need a new review. Per-object schema-one manufacturing_source retains inspection,
confirmed kind/role and parsed-unit facts; source_file preserves exact bytes through Latin1.
Gerber and Excellon receive only optional field/serialization/UI hooks. Old None reports remain
valid, malformed reports clear displayed evidence. No new project format or runtime dependency.
