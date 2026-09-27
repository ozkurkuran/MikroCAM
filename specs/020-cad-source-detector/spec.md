# Feature Specification: CAD source detection

**Feature Branch**: `020-cad-source-detector`
**Created**: 2026-09-27
**Status**: Ready for planning
**Input**: Roadmap20: DXF/SVG source detection for KiCad, Illustrator, Inkscape, Proteus and Unknown.

## User Scenarios & Testing

### User Story 1 - Understand SVG source evidence (Priority: P1)
A designer imports SVG artwork and sees which supported application its embedded metadata identifies,
with the actual evidence and uncertainty, so source-specific advice has an honest basis.
**Why this priority**: Guessing the source from artwork appearance can give incorrect import advice.
**Independent Test**: SVG samples with explicit producer fields display the expected application;
missing, conflicting and misleading artwork text produce Unknown.
**Acceptance Scenarios**:
1. Given an explicit supported producer marker, import displays the matching application and field.
2. Given only a filename, layer name, ordinary drawing text or generic page metadata, source is Unknown.
3. Given evidence for multiple applications, source is Unknown and the conflicting evidence is retained.

### User Story 2 - Understand DXF source evidence (Priority: P2)
A designer imports DXF artwork and sees the same source categories based on explicit producer
metadata, without units or the DXF format revision being mistaken for the authoring application.
**Why this priority**: DXF drawings often retain little reliable producer information.
**Independent Test**: Known producer comments identify supported applications; unmarked real exports
remain Unknown, and geometry is identical with or without identification metadata.
**Acceptance Scenarios**:
1. Given a supported explicit generator comment, source evidence identifies that application.
2. Given only format version, units, application-table names or drawing text, source remains Unknown.
3. Given unavailable, malformed or excessive metadata, the result explains the limitation without
   changing the existing geometry import behavior or guessing an application.

### User Story 3 - Retain historical source evidence (Priority: P3)
A designer saves and reopens an imported Geometry or Gerber object and can still inspect the source
assessment without reopening or depending on the original SVG/DXF file.
**Why this priority**: Source evidence should remain useful after files move or artwork is edited.
**Independent Test**: Import both formats, save, remove the temporary input and reopen the project;
the source label, evidence and source identity are unchanged.
**Acceptance Scenarios**:
1. Given a completed import, Properties displays read-only source assessment and historical status.
2. Given an old object without source evidence, it opens normally with no invented assessment.
3. Given invalid stored evidence, the display reports unavailable data and never shows stale evidence.

### Edge Cases
Copied producer metadata; mixed application history; namespace aliases; generator words in ordinary
text, IDs or comments without producer syntax; generic Adobe XMP page size; case/version spelling;
missing or conflicting metadata; UTF-8/BOM and existing DXF encodings; malformed XML, entities,
binary DXF, excessive source/evidence, old projects, modified geometry and deleted source files.

## Requirements
### Functional Requirements
- **FR-001**: Return one of KiCad, Illustrator, Inkscape, Proteus or Unknown using a documented finite
  set of explicit in-file producer markers. Additional application families require actual samples.
- **FR-002**: Preserve the marker location and original value, source format, source name and identity
  with every assessment; describe it as application metadata rather than proof of authorship.
- **FR-003**: Return Unknown when evidence is absent, unsupported, conflicting or cannot be inspected;
  preserve the reason and any usable bounded evidence instead of assigning a confidence score.
- **FR-004**: Never infer source from file/path names, geometry, layer names, units or format version,
  and never treat generic XMP dimensions as evidence of Illustrator.
- **FR-005**: Perform bounded offline inspection without network access, external resources, fonts,
  external processes or mutation of source bytes, geometry, units, tools, placement or defaults.
- **FR-006**: Integrate source assessment with existing SVG/DXF Geometry and Gerber import flows.
  Detection limitations must not turn an otherwise successful geometry import into a guessed result
  or a detector-induced import failure.
- **FR-007**: Display readable plain-text evidence and uncertainty in object Properties; preserve it
  through project save/reopen, with old missing and invalid stored records handled explicitly.
- **FR-008**: Validate positive and negative authored marker fixtures plus available licensed or
  locally generated application outputs, clearly separating syntax tests from vendor-export coverage.
- **FR-009**: Preserve all existing reference outputs and report behavior, and run actual desktop
  round trips without connecting to manufacturing equipment.

### Key Entities
- **Source assessment**: source identity/format, one application category, status and evidence.
- **Producer evidence**: a supported metadata field or generator declaration and its original value.
- **Historical display**: retained assessment from import time, independent of current artwork edits.

## Success Criteria
### Measurable Outcomes
- **SC-001**: All documented positive marker fixtures identify the expected category; all ambiguous,
  absent and misleading-marker fixtures remain Unknown with a useful reason.
- **SC-002**: Every claimed application label is backed by visible retained producer evidence; no
  sample is classified by geometry, filename, layer, units or format version alone.
- **SC-003**: Metadata-only variations leave imported geometry, units and tool settings unchanged.
- **SC-004**: SVG/DXF Geometry/Gerber source assessments survive desktop project round trips exactly,
  while old projects open without fabricated source facts.
- **SC-005**: Complete regression, source-limit and malformed-input checks pass, with provenance and
  actual vendor-sample coverage documented for each supported marker family.

## Assumptions
- Builds on import reporting from17 and delivered SVG work16/19; no new CAD format parser.
- Metadata is a claim that may be copied; it is never authoritative manufacturing intent.
- A real unmarked KiCad or other supported-tool export legitimately remains Unknown.
- Generic explicit generator declarations may be tested with authored syntax fixtures; they do not
  establish that every version of that application emits the declaration. Vendor coverage stays explicit.
- No interactive source override, automatic geometry repair/scaling, confidence scoring, or bulk
  import wizard is included. Later roadmap slices consume this assessment if useful.
