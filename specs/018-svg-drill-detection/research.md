# Research: SVG drill candidates

## Upstream behavior and license
Read-only `neo/main` is ProgLuis/FlatCAM9NeoS2 commit
914630319725b0d6034801f4808ae345d53b407b, MIT, Copyright 2026 Yacupoma Aguirre Luis Enrique.
Original extraction fd9e365ac3c41e713fc329a608e4cafbb8667caa; broader style handling
181c1f2a28d9a03675c4ee42bec234494bfe63e1. Sources: appParsers/ParseSVG.py functions
svgextract_circular_paths/extract_proteus_svg_drills; app_Main.py import_svg_drills.
Neo tests closed path bounding-box radii, white fill/no stroke, concentric larger pad within
0.02, duplicate rounded centres and diameter grouping within 0.01. It auto-creates output.
Decision: independently preserve the useful white-opening convention, require actual circular
geometry and user selection; use existing complete transform chain. Equal bbox dimensions alone
accept squares; automatic inference is not sufficient evidence of manufacturing intent.
Source: https://github.com/ProgLuis/FlatCAM9NeoS2/tree/914630319725b0d6034801f4808ae345d53b407b

## Workflow
Decision: independent source file -> review -> new Excellon. Alternative selected SVG object would
require matching current edited geometry to historical source; a new import action is simpler and
never assumes alignment of changed artwork. Existing SVG load supplies exact mm frame and flip.
No renderer fork and no second XML parser; resolved inherited paint is retained at original traversal.

## Circle evidence
Decision: exact axes for circle/ellipse; path fit to physical coordinates with radial and segment
midpoint residuals, complete monotone winding, bounded angular gaps and at least twelve vertices.
Reject isolated white, compound, open, noncircular and insufficiently resolved paths. Fill must be
white and enabled, stroke absent; pad must have nonwhite enabled fill. Same element may not be pad.
Pad radius must contain opening plus centre offset and tolerance. This remains a heuristic even
for perfect circular artwork. General polygon-to-drill workflow is later roadmap21.

## Conflict and tool grouping
Decision: stable sorted candidates, duplicate equality within centre/diameter tolerances; all
incompatible intersecting holes excluded with notices. Tool groups sorted by diameter, max-minus-min
<=0.01 mm, representative arithmetic mean, stable tool IDs and centres. Chained matches rejected.
Selections validated against immutable current review; no selection means no output.

## Legacy boundary
Existing app.app_obj.new_object initializer runs before collection publication. Populate complete
tools/Points using its authoritative units, create_geometry, generate source via existing synchronous
local-use export, then allow publication. Existing object factory supplies drilling/milling defaults.
Export precision remains existing configured precision and is stated in validation.

## Evidence limits
No genuine licensed Proteus SVG fixture found in Neo or the reference corpus. Existing Proteus
Gerber corpus is not an SVG sample. New SVG is original MIT analytic artwork, not a claimed vendor
export. Genuine Proteus validation stays pending. No machine use is implied by creating Excellon.
All design unknowns resolved; no extra dependency or user permission needed.
