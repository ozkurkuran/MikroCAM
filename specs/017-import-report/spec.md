# Feature Specification: Import quality report

**Feature Branch**: `017-import-report`
**Created**: 2026-09-27
**Status**: Specification review
**Input**: Roadmap 017: import quality report for scale, units, validity, open paths and precision.

## User Scenarios & Testing

### User Story 1 — Understand what was imported (P1)
A PCB designer imports an SVG and checks its original sizing information, resolved physical size,
source mapping and approximation precision before manufacturing. Independent test: an equivalent
mm/inch pair and an inferred-size drawing produce truthful, distinguishable reports.
Acceptance:
1. Source name/identity, explicit or inferred dimensions, source unit labels, viewBox/aspect policy,
   resolved millimetre dimensions and source-to-mm mapping are visible without guessing missing facts.
2. The report distinguishes the physical viewport from the material bounds and any vertical flip.
3. It states the actual declared curve precision and all bounded import notices. A result without
   complete supporting facts is never labelled as an exact scale or manufacturing guarantee.

### User Story 2 — Review geometry quality on the selected object (P1)
The designer selects an imported Geometry or Gerber object and reads a compact, read-only report
alongside its properties. Independent test: alternate between two imports and an ordinary object.
Acceptance:
1. The report shows valid/invalid/nonempty material evidence, material component counts, original
   open/closed path counts and retained centreline notices for the selected import.
2. An open source path that was implicitly filled is still reported as open; rejected imports do
   not display a previous object's successful report.
3. The report identifies its measurements as import-time evidence. Later editing, scaling or source
   changes do not make that historical result a claim about current geometry or machine readiness.
4. Names/notices render as text. Selecting/deleting objects never leaves another object's report.

### User Story 3 — Keep reports through project round trips (P2)
The designer saves and reopens a project and can review the original import evidence again.
Independent test: round-trip two distinct reports and open a project created before this feature.
Acceptance:
1. A supported report survives without changed counts, source identity, units or precision.
2. Old objects without a report remain usable and do not gain invented quality evidence.
3. Unknown, corrupt or excessive report data is identified as unavailable/invalid; it does not
   prevent access to otherwise loadable existing geometry or trigger another import.

### Edge Cases
Missing dimensions; mixed source units; nonzero viewBox; flips/nonuniform transforms; empty or
unpainted paths; inferred scale; bounded notice truncation; edited source/geometry; duplicate names;
object deletion; old project fields absent; corrupt/newer report versions; malformed imports.

## Requirements
- **FR001** Build a report from the import's recorded facts, with source identity, original sizing,
  source units/mapping, resolved mm dimensions and material bounds.
- **FR002** Distinguish explicit facts, inferred sizes and unavailable values; never guess a CAD
  source, fabrication scale or manufacturing suitability.
- **FR003** Include geometry validity/nonemptiness, material and open/closed source-path counts.
- **FR004** Disclose approximation precision and notices, including retained Geometry centrelines.
- **FR005** Display the selected Geometry/Gerber import's report in its properties without changing
  machining parameters, geometry or source text.
- **FR006** Label measurements as historical import evidence, separate from subsequent edits and
  existing CAM-to-machine placement.
- **FR007** Preserve supported report data on save/reopen; load older objects without a report.
- **FR008** Reject invalid/unsupported report data explicitly and bound serialized size/counts/text;
  no remote loading, machine action or repeated geometry import is involved in display.
- **FR009** Keep successful reports attached to their owning object through selection/deletion;
  failed imports cannot publish partial or stale success evidence.
- **FR010** Verify data, lifecycle, project compatibility and actual desktop behavior while retaining
  all earlier import/CAM/reference journeys.

### Key Entities
Import identity and original coordinate facts; import-time quality measurements; precision and
notices; selected object's retained report; unavailable/unsupported historical evidence.

## Success Criteria
- **SC001** Analytic SVG examples report source units, physical bounds and mapping consistent with
  the imported result within 0.000001 mm for linear geometry.
- **SC002** Every tested open/closed source path and material component is counted exactly, including
  implicitly filled open paths and explicitly retained centrelines.
- **SC003** Switching/deleting objects and a rejected second import never displays another object's
  report; text containing markup remains literal.
- **SC004** Save/reopen retains supported evidence exactly; old/corrupt/newer report examples leave
  normal object access usable and visibly avoid fabricated success.
- **SC005** Report display performs no import or machine action and completes within one second for
  the maximum supported summary. Full tests, architecture checks and desktop roundtrip pass.

## Assumptions and Scope
The initial complete report is for SVG, directly consuming roadmap 016. Other formats remain
unchanged until they supply comparable recorded facts; lack of a report is explicit. Source/CAD
classification, SVG drill recognition, Illustrator/XMP/clipping and the multi-file wizard remain
018–024. Reporting does not repair geometry or resample curves. All evidence describes the import
instant; a report is not a live geometry audit or manufacturing approval. Three stories, tests first.
