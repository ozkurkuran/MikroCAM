# Feature Specification: Hatch interlace and multiple passes

**Feature Branch**: `007-hatch-interlace-multipass`
**Created**: 2026-09-27
**Status**: Implemented
**Input**: Roadmap 7: interlace N and per-pass power, frequency, pulse width and speed.

## User Scenarios & Testing

### User Story 1 - Interleave hatch rows (Priority: P1)
As a CAM user I can select interlace N so successive row groups are spaced apart while
every clipped hatch segment remains present.
**Why this priority**: Enables a deliberate scan order without changing the selected area.
**Independent Test**: N=3 yields row-index groups 0/3/6, 1/4/7, 2/5/8, including each
disconnected segment exactly once; N=1 retains existing order.
**Acceptance Scenarios**:
1. Given clipped parallel/cross hatch, interlace groups use original row indices, including
   negative indices; perpendicular families are processed separately in order 0 then 1.
2. Given N larger than row count or sparse rows, empty groups cost no traversal and no paths
   disappear. Contours keep their order before hatch, and coordinates/placement stay unchanged.
3. Given invalid N or cancellation, planning fails explicitly and no partial plan is published.

### User Story 2 - Edit and save explicit recipes (Priority: P1)
As a user I can add, remove, reorder and edit named laser passes and save/load my recipe,
so each pass carries its own explicit power %, speed mm/s, frequency kHz and pulse width ns.
**Why this priority**: Makes slice 005's explicit data usable in the desktop workflow.
**Independent Test**: Create a two-pass recipe with different values, reorder, save/reload,
then generate and verify pass order and all four parameters exactly.
**Acceptance Scenarios**:
1. New pass parameter cells start blank; no machine/global defaults are inserted. All fields
   are required and existing core validation rejects duplicates and invalid/nonfinite values.
2. Loaded schema-1 recipes retain every value; save uses the same schema and a failed write
   leaves the previous file intact. Cancelling a file dialog changes no recipe data.
3. Edits invalidate the last plan and cannot alter an active request's immutable recipe.

### User Story 3 - Inspect every planned pass (Priority: P2)
As a user I can generate a plan containing the ordered passes with their explicit settings
and shared interlaced geometry, ready for the following export slice.
**Why this priority**: Ties recipe editing to actual generation rather than a disconnected table.
**Independent Test**: Two passes have distinct parameter values and the same ordered placed
geometry; the Geometry preview draws that geometry once and status identifies pass count.
**Acceptance Scenarios**:
1. Each recipe pass becomes a planned pass in the same order with its own settings and every
   path. Coordinates are placed exactly once; identical immutable geometry can be shared.
2. Changing interlace or recipe parameters clears stale plan state; cancellation/reopening
   and the existing source/preview lifecycle remain valid.

## Requirements
- **FR-001**: Expose integer interlace N from 1 to 1,000,000, with N=1 preserving prior order.
- **FR-002**: Order hatch by family, original scan index modulo N, then scan index; preserve
  original segment order within a row. Preserve contours first, geometry and path count.
- **FR-003**: Provide explicit recipe/pass name and parameter editing, insertion, deletion and
  reordering with core validation and no implicit parameter substitutions.
- **FR-004**: Load/save existing recipe schema 1 without migration or precision loss; failed
  writes must not corrupt existing files. Report all validation/file errors visibly.
- **FR-005**: Expose each planned pass's original validated settings and complete ordered paths;
  preserve single placement and display geometry once, not overlapping duplicates per pass.
- **FR-006**: Invalidate stale results on edits and retain bounded cooperative cancellation.
- **FR-007**: Keep architecture/growth checks green; test first core/domain; desktop smoke passes.

### Key Entities
Interlace N (ephemeral geometric plan option), existing LaserRecipe/LaserPass schema-1 data,
planned pass (one LaserPass and shared immutable placed paths). No new persistent job format.

## Success Criteria
- **SC-001**: Analytic N=1/2/3/sparse/negative/cross-hatch cases retain exactly the original path
  multiset and coordinates in the specified order, including N greater than the row count.
- **SC-002**: Edited/reordered two-pass recipes survive JSON round-trip with exact parameters.
- **SC-003**: GUI smoke creates and previews a two-pass interlaced plan, with no source mutation
  or machine operation; full regression and architecture checks pass.

## Assumptions and hazards
Requires 006. Geometry ordering offers no claim of calibrated heat management or laser output.
Export follows in 008; no hardware/ARM/transport exists. Wrong parameter/unit, omitted rows and
stale plan hazards are addressed by labelled units, strict core validation, multiset/order tests
and existing cancellation/invalidation. UI generation retains idle/running/cancelling/error
states and always offers cancel. Material/device validation remains external.
