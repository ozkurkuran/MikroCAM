# Feature Specification: Laser contour and hatch

**Feature Branch**: `006-laser-contour-hatch`
**Created**: 2026-09-27
**Status**: Specified
**Input**: Roadmap slice 6: outer/inner/trace/pad/board-edge contours, angled and cross
hatch with clipping, integrated Laser CAM panel and existing Geometry canvas preview.

## User Scenarios & Testing

### User Story 1 - Select meaningful contours (Priority: P1)
As a PCB CAM user I can select outer copper, inner copper holes, trace, pad or an explicit
board outline, so I preview the boundaries needed for my intended process.
**Why this priority**: Correct geometry and feature meaning precede filling an area.
**Independent Test**: A reference board with a hole, island, flash pad and trace yields the
expected boundaries for each mode, with placement applied once and source unchanged.
**Acceptance Scenarios**:
1. Outer mode returns exterior rings; inner mode returns holes, including multipart copper.
2. Trace/pad modes use Gerber feature metadata clipped to final copper; unavailable metadata
   raises an explanation rather than treating every copper island as a pad or trace.
3. Board mode uses an explicitly selected closed outline; open or missing outlines fail.

### User Story 2 - Fill the chosen area (Priority: P1)
As a CAM user I can set spacing and angle, add cross hatch, and explicitly choose copper
or board-minus-copper, so generated segments cover my intended area without crossing holes.
**Why this priority**: Hatch paths are the initial PCB material-removal workflow.
**Independent Test**: Analytic rectangular, holed and disconnected regions produce clipped
parallel segments at the requested spacing and angle; cross hatch adds the perpendicular set.
**Acceptance Scenarios**:
1. All exposure segments lie within the selected area; gaps across holes/islands stay separate.
2. Cross hatch adds angle+90 degrees and preserves each family's scan-line identity.
3. Board-minus-copper requires a valid explicit board containing the copper; no bounding box
   or inferred board size is substituted. Empty results report no paths.
4. Invalid spacing/nonfinite values, excessive work and cancellation fail explicitly without
   publishing partial geometry. Identical input produces identical ordered paths.

### User Story 3 - Preview from the desktop (Priority: P2)
As a user I open Laser CAM from the Evo tools menu, choose loaded Gerber/outline objects,
load my recipe JSON, configure placement/contour/hatch and generate an ordinary Geometry
preview, so I can inspect the result on the current canvas.
**Why this priority**: The pure geometry becomes a usable CAM workflow.
**Independent Test**: Desktop smoke opens the panel, loads a recipe, generates/replaces a
preview, sees it on canvas and exits cleanly without modifying source objects.
**Acceptance Scenarios**:
1. Reopening Laser CAM reuses the panel. Input errors are visible and no recipe defaults appear.
2. Generation works from detached data off the GUI thread; cancel, close or changed inputs
   prevent stale results being published. New requests cannot overlap existing work.
3. Preview uses placed mm paths through existing Geometry; source selection remains usable,
   and only an owned earlier preview is replaced. No CNC/laser hardware action is offered.

## Requirements
- **FR-001**: Support none/outer/inner/trace/pad/board contour selection with explicit semantics.
- **FR-002**: Preserve copper topology and source data; trace/pad positives are intersected with
  final Gerber copper to respect clear polarity. Closed board outlines are explicitly selected.
- **FR-003**: Generate angled hatch at finite positive mm spacing, optionally perpendicular
  cross hatch; clip each segment to the selected area, never join through excluded regions.
- **FR-004**: Expose copper versus board-minus-copper choice and require a containing board
  for subtraction. Board contours trace the supplied outline including cutouts.
- **FR-005**: Use the shared Placement exactly once for source-to-output placement; keep
  ordered plain paths and original scan indices for later interlace/multipass work.
- **FR-006**: Reject invalid, empty, unsupported and over-complex requests; support cooperative
  cancellation with no partial publication and deterministic results.
- **FR-007**: Integrate a translated thin Laser CAM panel with explicit recipe JSON input,
  geometry controls, shared placement controls, progress/status and cancel action.
- **FR-008**: Generate off the GUI thread from detached data; publish via the bridge on the
  GUI thread, reuse the panel and replace only its owned ordinary Geometry preview.
- **FR-009**: Maintain architecture/growth gates; core/domain tests require neither Qt nor
  hardware. GUI smoke and hosted regression checks must pass.

### Key Entities
- Feature snapshot: detached final copper, optional trace/pad areas and optional board area.
- Plan options: contour mode, fill polarity, hatch spacing/angle/cross-hatch choice.
- Laser path: immutable mm points, role, optional hatch family and integer scan index.
- Laser plan: original LaserJob plus ordered placed paths; no machine command or new format.

## Success Criteria
- **SC-001**: Every reference contour and hatch example agrees within 1e-8 mm, including holes,
  angles, disconnected regions and nonidentity placement; no segment crosses an excluded area.
- **SC-002**: Invalid/unsupported/complexity/cancel examples publish zero partial previews.
- **SC-003**: A real desktop workflow produces and replaces one Geometry preview and shuts
  down normally; source copper remains byte-for-byte equivalent.
- **SC-004**: Complete tests, architecture and +50 legacy budget pass without new dependencies.

## Assumptions and hazards
Depends on 005. This feature generates geometry only; it does not connect, arm, emit or move
a machine. Recipe parameters remain explicit model data, with editing/interlace in 007 and
export in 008. No new project or persistent plan format. Hatch spacing is a visible geometric
input, not an inferred machine recipe. Physical laser qualification remains external.

Geometry hazards are wrong polarity, double placement, omitted clear areas and stale previews;
explicit polarity, final-copper clipping, shared placement and request cancellation cover them.
Generation has idle/running/cancelling/error states; every running request can be cancelled.
Fixed work limits bound memory/latency and fail rather than silently reducing detail.
