# Feature Specification: SVG scale, transforms and solid strokes

**Feature Branch**: `016-svg-scale-transforms`
**Created**: 2026-09-27
**Status**: Implemented; full validation pending
**Input**: Roadmap 016: viewBox scale, units, matrix/translate/rotate/scale/skew,
inherited stroke-width and conversion of strokes to solid manufacturing geometry.

## User Scenarios & Testing

### User Story 1 — Import at the intended physical size (P1)
A PCB designer uses existing Geometry/Gerber import commands and gets the size and origin in the
file. Independent test: equivalent mm/cm/in/pt/pc/px drawings agree physically in mm/inch workspaces.
Acceptance:
1. Both dimensions, viewBox origin, comma/whitespace syntax and aspect-ratio policy are honored.
2. Unitless/px sizes use 96 px/in. Missing root dimensions may use a valid viewBox in pixels with
   an explicit notice. Unresolved percentages/font-relative root sizes fail with a useful reason.
3. Existing optional vertical flip occurs exactly once about physical viewport height.
4. Invalid scale information leaves source files and existing objects unchanged.

### User Story 2 — Preserve nested drawing transforms (P1)
Grouped artwork retains translations, rotation centres and matrix coefficients in the proper
coordinate system. Independent test: analytic points/bounds verify each transform and nested,
noncommuting compositions before and after physical-unit conversion.
Acceptance:
1. matrix, translate, rotate (with optional centre), scale, skewX/skewY and transform lists work on
   primitives/groups; parent/child transforms compose in SVG order.
2. Local use references retain x/y offsets and inherited transforms. Unused definitions are not
   drawn. Missing, external or cyclic references give an explicit error.
3. Invalid/singular matrices, nonfinite numbers, unsupported syntax and excessive complexity fail
   promptly instead of hanging, returning partial success or guessing a transform.

### User Story 3 — Manufacture the drawn stroke width (P1)
Stroked artwork becomes solid material with the specified width. Group inheritance/local overrides
produce the same outline as explicit styles. Independent test: known paths/primitives verify
bounds/areas under nonuniform transforms, caps and joins.
Acceptance:
1. Inherited stroke/width, presentation attributes and inline overrides determine local stroke.
2. Expansion precedes nonuniform scale/skew; butt/round/square caps and miter/round/bevel joins work.
3. stroke:none and zero width add no solid. Fill/stroke preserve source identity and centreline
   data for later reporting; unsupported appearance is identified rather than silently guessed.
4. Existing supported primitive/path journeys remain through the import menu, without a new wizard.

### Edge Cases
Zero/negative dimensions, exponents, trailing garbage, mirrored/anisotropic transforms, inherited
widths, disconnected subpaths, empty documents, malformed XML, duplicate IDs, deep groups, cyclic
references, huge values/paths and unresolved CSS/clip/external dependencies.

## Requirements
- **FR001** Resolve supported absolute root/element units consistently into authoritative mm geometry
  before the host-unit boundary.
- **FR002** Apply viewport dimensions, viewBox origin and aspect policy; disclose size inference.
- **FR003** Parse complete supported transform syntax; reject unconsumed/nonfinite data promptly.
- **FR004** Compose list/parent/reference/viewport mappings in order, preserving flip/local use.
- **FR005** Resolve inherited stroke properties and inline overrides before expansion.
- **FR006** Expand strokes locally with cap/join/miter semantics, then transform with the path/fill.
- **FR007** Preserve supported Geometry/Gerber import journeys; explicitly identify unsupported
  appearance instead of silently omitting it.
- **FR008** Return source/scale/transform notices and stable geometry for subsequent import-report;
  the report panel and wizard stay in their later slices.
- **FR009** Bound source size, depth, reference expansion, geometry and numeric range. No external
  resource fetching, entity resolution, scripts or inferred browser/font layout.
- **FR010** Fail atomically with a useful reason: no partial object, source modification, machine
  action or change to existing objects.
- **FR011** Verify analytic geometry, equivalent-unit fixtures and real desktop imports while
  preserving frozen reference outputs.

### Key Entities
Source identity/viewport; accumulated source mapping; inherited paint; resolved geometry with
source element identity and notices. Source import mapping describes file coordinates; existing
CAM-to-machine Placement remains authoritative afterwards.

## Success Criteria
- **SC001** Equivalent supported units/mm-inch workspaces agree within 0.000001 mm for linear
  analytic fixtures without unexplained scale/origin changes.
- **SC002** Each transform and nested noncommuting example has independent point/bounds checks;
  malformed transforms terminate with an explicit error.
- **SC003** Straight stroke area/bounds agree analytically; curves have an explicit tested tolerance
  and produce valid planar geometry.
- **SC004** Invalid/unsupported/excessive input leaves objects unchanged and gives an actionable
  diagnostic; bounded representative fixtures finish within ten seconds locally.
- **SC005** CAM/reference, architecture and actual desktop import/roundtrip tests pass, with final
  Windows CI and documented unsupported SVG features.

## Assumptions and Scope
Roadmap 009 supplies regression discipline. Report UI, drill detection, Illustrator XMP/layers/clip
and source detection stay in 017–020. External CSS/fonts/browser layout are not inferred. Complex
appearance is preserved by a tested existing path or explicitly rejected until its planned slice.
No browser-rendering parity is claimed. This feature never communicates with a machine.
