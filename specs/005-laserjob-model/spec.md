# Feature Specification: Laser job model

**Feature Branch**: `005-laserjob-model`
**Created**: 2026-09-27
**Status**: Specified
**Input**: Roadmap slice 5: separate LaserJob, ordered-pass recipe JSON, serialization and
Gerber-to-core geometry bridge, using the shared placement.

## User Scenarios & Testing

### User Story 1 - Keep explicit laser recipes (Priority: P1)

As a CAM user, I need a reusable recipe containing ordered, named passes and explicit laser
parameters, so the next CAM steps do not obtain hidden defaults from the CNC tool database.

**Why this priority**: Laser parameters and CNC machining parameters must stay separate.
**Independent Test**: Save/load a recipe with two different passes and compare every field/order.
**Acceptance Scenarios**:
1. Given named passes with explicit power, speed, frequency and pulse width, when serialized and
   loaded, then names, order, units and values remain unchanged.
2. Given missing, duplicate, non-finite or unsupported data, when loaded, then a specific error
   appears; no global/default recipe values are substituted.

### User Story 2 - Preserve a laser job independently (Priority: P1)

As a CAM developer, I need an immutable, device-independent laser job with source copper,
recipe and placement, so future preview/path generation can use the same data.

**Why this priority**: The job must not acquire CNC fields or depend on the running desktop.
**Independent Test**: Round-trip a job with holes/disconnected copper and nonidentity placement.
**Acceptance Scenarios**:
1. Given a laser job, when stored and loaded, then geometry, ordered recipe and placement agree.
2. Given a placed job, when preview geometry is requested, then it uses the existing placement
   operation exactly once and leaves the source geometry unchanged.
3. Given a future or malformed file version, when loaded, then it fails explicitly.

### User Story 3 - Snapshot Gerber copper (Priority: P2)

As a CAM developer, I need a bridge that converts a Gerber object's current solid copper into
core data, so processing survives host changes without importing host objects into core.

**Why this priority**: Later laser features need a reliable input boundary.
**Independent Test**: Convert mm/inch Gerber examples, including holes and nested/disconnected solids.
**Acceptance Scenarios**:
1. Given a valid Gerber object, when snapshotted, then copper is detached immutable core data in mm.
2. Given inch geometry, when snapshotted, then its coordinates are converted by exactly 25.4 once.
3. Given an unsupported unit, wrong object kind, empty or invalid/nonpolygon geometry, when converted,
   then it fails visibly without consulting global defaults or mutating the host.

### Edge Cases

- Duplicate pass names or duplicate JSON keys, unknown fields and missing required parameters.
- Power outside (0,100], nonpositive speed/frequency/pulse width, non-finite values or booleans.
- Empty/3D/invalid geometry, polygon holes and multipart Gerber lists/collections.
- Unsupported schema versions; serialized jobs remain separate from Evo project/CNC formats.

## Requirements

- **FR-001**: Define separate immutable plain-data laser recipe, pass and job values.
- **FR-002**: Pass parameters MUST be explicit: power percent, speed mm/s, frequency kHz and pulse width ns;
  validate finite positive values, power <=100 and unique nonempty pass names. No machine-specific ranges are inferred.
- **FR-003**: Recipe and job JSON MUST be versioned, deterministic and preserve field values/order.
- **FR-004**: Reject unsupported versions, missing/unknown fields, duplicate keys and invalid values explicitly.
- **FR-005**: Jobs MUST contain detached valid planar copper, recipe and the existing Placement; never CNCJob fields.
- **FR-006**: Gerber conversion MUST preserve topology, convert declared units to mm once and leave source objects intact.
- **FR-007**: Core MUST operate without Qt, legacy imports or device access; only bridge may reference host types.

### Key Entities

- Laser pass: unique name and explicit four laser parameters with stated units.
- Laser recipe: name and nonempty ordered immutable pass list.
- Planar region: nonempty valid polygon/multipolygon copper with holes, in mm.
- Laser job: name, region, recipe and placement; no controller or CNC object reference.

## Success Criteria

- **SC-001**: Every field of reference recipes and jobs survives save/load with stable repeated serialization.
- **SC-002**: All missing/invalid/future-version examples fail, with zero implicit parameter substitution.
- **SC-003**: mm/inch bridge examples agree within 1e-9 mm and retain topology and source values.
- **SC-004**: Full tests and architecture/growth checks remain green with no added runtime dependency.

## Assumptions

- Depends on placement slice 004. UI/pass editing/interlace/path generation/export follow in slices 006–008.
- This models explicit parameters now; later multipass UI consumes them without inventing defaults.
- No machine motion, laser emission, hardware connection or device qualification is performed.
- Recipe/job JSON is a separate exchange file; Evo's project format and CNC model are unchanged.
