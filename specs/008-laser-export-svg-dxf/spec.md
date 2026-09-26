# Feature Specification: Per-pass SVG and DXF export
**Feature Branch**: `008-laser-export-svg-dxf`
**Created**: 2026-09-27
**Status**: Implemented (software export; target-app/physical verification recorded separately)
**Input**: Roadmap 8: SVG/DXF transfer to LightBurn/EZCAD, each pass separately identifiable.

## User Scenarios & Testing
### User Story 1 - Transfer placed paths (Priority: P1)
As a CAM user I can export one SVG or DXF per planned pass so I can import the generated
geometry into LightBurn or EZCAD while retaining dimensions, holes, placement and pass identity.
**Why this priority**: Delivers the software handoff for the first laser PCB workflow.
**Independent Test**: Export a placed two-pass 25.4 mm analytic fixture and read it through
independent SVG/DXF parsers; reconstruct mm paths and compare all vertices/order/closure.
**Acceptance Scenarios**:
1. Each pass gets a separately named geometry file; files share the same registration frame.
2. SVG uses physical mm dimensions and a consistent Y-down frame; DXF uses XY modelspace
   with mm unit metadata. The original placed geometry can be reconstructed within tolerance.
3. No clipped gaps are connected, no extra registration/exposure lines appear and no path
   is dropped or duplicated. Source job/preview remains unchanged.

### User Story 2 - Carry explicit settings and instructions (Priority: P1)
As a user I receive the recipe and pass-to-file mapping alongside geometry so I can set
each imported pass's power, speed, frequency and pulse width deliberately in the target app.
**Why this priority**: SVG/DXF geometry alone does not carry portable laser process settings.
**Independent Test**: Unpack the export, match every filename/hash/pass to the exact recipe,
and verify the instructions describe scale, orientation, ordering and manual setting transfer.
**Acceptance Scenarios**:
1. One ZIP contains every geometry file, the unchanged schema-1 recipe, versioned manifest
   and import instructions. Names remain safe even for duplicate-looking or unusual pass names.
2. Manifest records units, bounds, coordinate mapping, interlace N, pass order/settings,
   path count and geometry-file hashes. No output claims to arm a laser or apply parameters.
3. Instructions distinguish structural/parser validation from actual target-app import and
   physical coupon validation; target software may reorder imported paths and must be checked.

### User Story 3 - Export the current plan safely (Priority: P2)
As a desktop user I can choose format and destination for my current successful plan, see
progress/status and cancel an unfinished export without damaging an existing file.
**Why this priority**: Connects the handoff to the usable Laser CAM workflow.
**Independent Test**: Desktop smoke exports both formats from the generated two-pass plan,
verifies ZIP contents and exits; stale/no-plan and cancelled/error cases publish no partial ZIP.
**Acceptance Scenarios**:
1. Export is available only for a valid current plan; edits invalidate it. Export runs off the
   GUI thread from an immutable snapshot while inputs and generation are disabled.
2. File-dialog cancellation changes nothing. Export errors/cancel before atomic publication
   preserve any previous destination and clean the temporary file.
3. Completed export reports its location. Close/shutdown joins workers cleanly; if cancellation
   arrives after atomic publication, report the completed output rather than falsely claiming removal.

## Requirements
- **FR-001**: Export one geometry-only SVG or DXF per recipe pass in a single ZIP package.
- **FR-002**: Preserve placed mm coordinates, path order, closure and clipped separation with
  explicit SVG axis mapping and DXF unit metadata; do not reapply Placement.
- **FR-003**: Use the same bounds/frame for every pass; handle single horizontal/vertical
  paths with a nonzero SVG viewport without adding exposure geometry. Reject derived extent
  overflow even when individual coordinates are finite.
- **FR-004**: Include existing recipe JSON and strict schema-1 export manifest with exact
  parameters, safe ordinal filenames, hashes, bounds, mapping, counts and interlace order.
- **FR-005**: Provide clear LightBurn/EZCAD import instructions: verify mm scale/orientation,
  manually transfer all four parameters and pass order, check target reordering; no physical
  or target-app validation claim without actual evidence.
- **FR-006**: Write atomically, bound export size, support cancellation before publication,
  preserve existing destination on failure and never leave a partial final ZIP.
- **FR-007**: Integrate translated format/export/status controls into the existing panel;
  prevent stale/busy exports and join on shutdown with no widget access from workers.
- **FR-008**: Test independent SVG/DXF readback, schema validation, settings/geometry fidelity,
  file errors/cancellation, UI lifecycle, full architecture checks and desktop smoke.

### Key Entities
Export package (ZIP), pass geometry file, existing recipe, versioned manifest and README.
Manifest is a transfer record, not a replacement for Evo project or LaserJob schema.

## Success Criteria
- **SC-001**: Independent readback of 25.4 mm, hole/gap, reflected/rotated and degenerate-extent
  fixtures agrees with every original vertex within 1e-8 mm, retaining ordered paths per pass.
- **SC-002**: Every pass has exactly one verified file and all four exact recipe parameters.
- **SC-003**: Cancel/error/stale-plan cases preserve existing destination; successful desktop
  export creates valid SVG and DXF ZIPs and exits cleanly.
- **SC-004**: Full tests and architecture/growth checks pass with no new runtime dependency.

## Assumptions and hazards
Requires 007. Only geometry/file transfer is performed; no machine connection, motion or
laser emission. Scale/axis/parameter/order hazards are addressed by mm metadata, analytic
readback, explicit mapping/recipe and import instructions. No claim of calibrated material
settings or completed physical PCB. Target-app import and a real test coupon need an
available licensed target installation and suitable hardware/material; record these separately.
Export states idle/running/cancelling/error/completed; cancel remains available while running.
