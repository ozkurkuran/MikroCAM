# Feature Specification: Selected PDF vector page import

**Feature Branch**: `023-pdf-vector-import`
**Created**: 2026-09-27
**Status**: Ready for planning
**Input**: Roadmap23: evaluate existing Evo PDF tool first, then page choice, cropping, flip,
independent subpaths and complexity guards; prefer permissive reading alternatives.

## User Scenarios & Testing

### User Story 1 - Inspect a PDF and choose one physical page (Priority: P1)
An operator opens a PDF and chooses one page using its physical dimensions and orientation.
The chosen page must not mix drawing commands from unrelated pages or resources.
**Why this priority**: Correct source-page identity is necessary before interpreting artwork.
**Independent Test**: Inspect an authored two-page document with different marks and dimensions;
select either page and verify its own dimensions, page number and source identity.
**Acceptance Scenarios**:
1. A valid document exposes bounded page choices, physical MediaBox/CropBox dimensions, rotation
   and source identity. One selected page is imported at a time.
2. Unknown, malformed, encrypted or excessive documents fail clearly without creating an object.
3. Original document bytes and recorded selected-page facts are retained with the result.

### User Story 2 - Review bounded page vectors with crop and flip (Priority: P2)
The operator selects the visible CropBox or full MediaBox, optionally crops a physical region,
and explicitly flips the result vertically. Separate paths and compound filled regions retain
correct physical topology, with no unintended bridges between independent subpaths.
**Why this priority**: Artwork needs correct physical dimensions and controllable orientation.
**Independent Test**: Analytic drawings cover different page origins, page rotation, unit scale,
transformed rectangles/curves, separate subpaths, compound holes and rectangular crop boundaries.
**Acceptance Scenarios**:
1. Page geometry respects current page units, full affine drawing transforms and page rotation.
2. Crop coordinates use the oriented physical page frame; the result is clipped and rebased to
   the chosen crop origin. Explicit vertical flip occurs exactly once about the cropped height.
3. Supported opaque filled/stroked paths are interpreted in paint order, including compound fill
   and basic clipping. White paint clears previous material; other opaque colors mark material.
4. Unsupported visible content or excessive complexity fails the chosen page atomically, with
   an actionable message; no partial or raster-derived manufacturing geometry is produced.

### User Story 3 - Create and retain a separate Geometry object (Priority: P3)
After reviewing physical bounds, counts and source facts, the operator explicitly creates a
named Geometry object with normal application defaults. The result can use normal CAM export
and project persistence while the original PDF and import choices remain traceable.
**Why this priority**: The reviewed vectors must become usable persistent CAM input.
**Independent Test**: Import a selected/cropped/flipped page, export/reparse geometry, save/reopen
without the original PDF file, and compare geometry, source identity, choices and defaults.
**Acceptance Scenarios**:
1. No object is created until an explicit successful review and creation action.
2. Changing file/page/crop/flip invalidates the prior review; source-file changes before creation
   require another analysis.
3. Failed initialization creates no partial object and does not change existing project objects
   or machining defaults.
4. Successful Geometry and import provenance survive project save/reopen without the source file.

### Edge Cases
Multiple pages, inherited page boxes, nonzero origins, quarter-turn page rotations, custom page
unit scale, contents arrays, rotated/sheared transforms, graphics-state nesting, independent open
subpaths, even-odd/nonzero holes, cubic curves, clipping, white overpaint, crop edge touches,
empty cropped material, text/image/shading/transparency, Form resources, malformed operators,
compressed-stream expansion, page/tree/path/point/overlay budgets, source replacement and units.

## Requirements

### Functional Requirements
- **FR-001**: Record an evaluation of existing Evo PDF behavior and permissive alternatives before
  selecting the reading path; introduce no mandatory AGPL component.
- **FR-002**: Inspect bounded PDF source bytes and expose distinct page choices with correct
  effective boxes, physical unit scale and quarter-turn rotation. Preserve exact source identity.
- **FR-003**: Interpret only the selected page, preserving independent subpaths and complete
  affine transform order. No source-dependent guessed scale or hole inference is allowed.
- **FR-004**: Provide CropBox/MediaBox choice, an optional bounded rectangular crop in oriented
  page millimetres, and explicit vertical flip. Apply each coordinate conversion once.
- **FR-005**: Preserve supported opaque vector material, compound fill rules, stroked boundaries,
  basic clipping and white-overpaint order. Reject unsupported visible content clearly.
- **FR-006**: Bound file/page/tree/stream/operator/state/path/point and geometric overlay complexity;
  invalid, nonfinite, singular or excessive data must never produce a partial positive import.
- **FR-007**: Show selected page, physical dimensions, crop/flip choices, source identity and resulting
  geometry statistics before explicit creation; parameter changes invalidate review.
- **FR-008**: Create a separate Geometry through normal host defaults and units, with original source
  and versioned optional provenance retained. Source files and existing objects remain unchanged.
- **FR-009**: Reject source changes and creation failures before publication. Preserve physical
  geometry and provenance through normal export and project save/reopen without external files.
- **FR-010**: Verify analytic PDF fixtures, legacy evaluation cases, malformed/complexity limits,
  MM/IN host conversion and actual desktop import/export/project journeys alongside prior features.

### Key Entities
- PDF document/page facts: exact source identity and effective page boxes, units and rotation.
- Import choices: one selected page, box mode, physical crop and explicit flip.
- Vector review: physical material and bounded source/choice/geometry evidence.
- Stored import provenance: versioned page and choice facts linked to original PDF bytes.

## Success Criteria
- **SC-001**: Selected analytic pages retain their own artwork and physical sizes within0.01mm;
  unrelated pages/resources do not contribute geometry.
- **SC-002**: Crop/rotation/flip/affine and compound-path fixtures retain expected topology and
  bounds within0.01mm; separate subpaths never acquire unintended connecting segments.
- **SC-003**: All unsupported/malformed/excessive fixtures fail without creating an object;
  changing source or choices invalidates prior review before publication.
- **SC-004**: Successful creation preserves normal defaults and existing objects. Project reopen
  retains geometry and provenance without the source file; export follows configured precision.
- **SC-005**: Full regression, actual desktop journeys, dependency/license checks and final-head
  Windows CI pass before delivery. No physical manufacturing compatibility is inferred.

## Assumptions
One page creates one Geometry object. No automatic drill extraction, text-to-outline conversion,
raster vectorization, interactive form execution, password workflow or general PDF renderer is
included. Unsupported visible constructs are rejected instead of silently omitted. The existing
legacy PDF tool remains available separately. Optional broader PDF compatibility is future work
only when backed by a licensed real example. Normal project format remains unchanged.
