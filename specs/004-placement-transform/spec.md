# Feature Specification: Placement transform

**Feature Branch**: `004-placement-transform`
**Created**: 2026-09-26
**Status**: Implemented
**Input**: Roadmap slice 4: one core coordinate transform for translation, rotation,
bottom-layer mirroring and origin, shared by laser, preview and later GRBL.

## User Scenarios & Testing

### User Story 1 - Place board coordinates consistently (Priority: P1)

As a CAM developer, I need a single placement operation so preview and generated paths
refer to the same board location and orientation.

**Why this priority**: Later laser and machine features must agree about coordinates.
**Independent Test**: Transform known millimetre points under each operation and their composition.
**Acceptance Scenarios**:
1. Given identity placement, when coordinates are transformed, then they are unchanged.
2. Given an origin, mirror, angle and translation, when applied, then the order is subtract
   source origin, mirror, rotate counterclockwise, add destination translation.
3. Given a bottom-layer mirror, when applied with zero rotation, then X relative to the origin
   reverses sign while Y is retained; origin maps to the destination translation.

### User Story 2 - Use the same placement for complete geometry (Priority: P1)

As a CAM developer, I need board geometry and individual coordinates to use exactly the same
placement and to be reversible, so paths can be compared without losing holes or units.

**Why this priority**: Separate geometry/point calculations could produce different output.
**Independent Test**: Compare transformed geometry vertices to transformed points and invert them.
**Acceptance Scenarios**:
1. Given polygon holes, disconnected shapes, lines or empty geometry, when placed, then their
   geometry types, topology and area/length are preserved within numerical tolerance.
2. Given valid placement, when a point or geometry is placed and then inversely transformed,
   then its original coordinates are recovered within 1e-9 mm for the reference cases.
3. Given a non-finite or malformed input, when used, then it fails explicitly without silently
   choosing defaults or mutating the source geometry.

### Edge Cases

- Negative coordinates/translations, zero or full rotations and combined mirror/rotation.
- Non-finite numbers, booleans masquerading as numbers, malformed point pairs and invalid geometry.
- Empty geometries and multi-part polygons with holes.
- Z coordinates are unsupported: this is an explicitly planar placement; reject them rather than
  silently dropping data or applying an ambiguous 3D interpretation.

## Requirements

### Functional Requirements

- **FR-001**: Provide one immutable millimetre placement with source origin, translation,
  counterclockwise rotation in degrees and optional X-coordinate mirror for the bottom layer.
- **FR-002**: Apply operations in the documented order with one shared affine coefficient definition.
- **FR-003**: Place individual points, sequences of points and planar geometry consistently.
- **FR-004**: Provide inverse placement using the same transformation definition.
- **FR-005**: Reject non-finite/malformed inputs and nonplanar geometry explicitly; preserve inputs.
- **FR-006**: Run without UI, host or hardware dependencies, with no duplicated placement implementation.

### Key Entities

- Placement: source origin (mm), destination translation (mm), rotation (degrees), mirror flag.
- Planar coordinates/geometries: input and output in millimetres; no implicit inch conversion.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All documented reference examples match expected coordinates within 1e-9 mm.
- **SC-002**: Round-tripping 100 deterministic placements/points and representative geometries
  meets the same tolerance without topology loss.
- **SC-003**: Point and geometry paths agree for every reference vertex, and invalid examples fail explicitly.
- **SC-004**: The complete regression suite and architecture/growth checks remain green.

## Assumptions

- Depends on slice 002 only. This supplies a reusable core operation; UI controls and laser/machine
  consumers arrive in their own roadmap slices. No current host transform code is replaced.
- One mirror axis suffices for the initial bottom-layer flip; adding other placement models
  including future affine fiducials requires the later roadmap feature.
- No job file format, machine movement or laser emission is introduced.
