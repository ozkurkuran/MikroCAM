# Validation: SVG physical scale, transformations and solid strokes

Status: local validation complete; PR/final-head Windows CI and merge pending.
Three stories,37tasks. No new dependency, external source-code copy or manufacturing-machine path.

## Requirements and constitution
FR001–004/SC001–002: strict absolute CSS96px units, full root/viewBox dimensions/origin/meet/none,
root transform outside viewBox, nested/local-use mapping, finite matrix order and one optional flip.
Source affine is distinct from existing Placement; host MM/IN conversion happens exactly once.
FR005–008/SC003: inherited/inline paint, local stroke before affine, caps and per-corner miter→bevel,
simple nonzero/evenodd winding, source open/closed metadata, explicit centreline/color/inference
notices, physically scaled curve tolerance. Self-intersection/clipping/general compound scope019
is explicitly unsupported. No guessed font layout or renderer/CSS parity.
FR009–010/SC004: bounded UTF8/source/numbers/XML/reference/path/geometry traversal; complete path
syntax checked before library allocation. Unsupported appearance and malformed input fail without
publishing partial geometry. Exact source file/text is preserved, including BOM/CRLF.
FR011/SC005: independent analytic whole-document source, unchanged original path fixtures and
frozen PCB/reference suite, actual Geometry/Gerber desktop save/reopen and all prior journeys.

All eight gates pass: layered pure core/domain and thin UI/host seams; legacy aggregate shrinks101
lines; concrete data/functions, existing mm authority, tests first, bounded offline behavior,
existing licenses/no new dependency, three stories. Largest new module272lines, function47lines
(limits600/80). No complexity exception. No frozen capture helper or golden file changed.

## Tests first and audit fixes
Initial module/behavior tests were red before implementation. Dedicated regressions exposed CSS
case/comment/escape bypass, currentColor transparency, malformed color functions, lost viewport
inference notices, additive ellipse endpoint error, GEOS clipped-miter versus SVG bevel semantics,
coincident open endpoints, closed zero-length caps and Gerber's old hole-filling QR workaround.
The actual desktop first exposed Geometry source_file missing after reopen. A separate fix registers
and initializes that already existing source field; three constructor/JSON/inherited serializer
regressions first failed, then passed, including old dictionaries without the field. Existing
FlatCAMObj missing-field migration preserves the empty default; no new project format was invented.

363 new SVG tests cover models/units/transforms, curves/material, bounded XML/style/color/path
syntax, bridge/host atomicity, reference facts and real object source persistence. Old direct
ParseSVG helper expectations remain unchanged; new SVG fill uses explicit winding rules.
Authored fixture SHA256: d51453ef6998bd33a67c7a2c92b4fec1f01d2e88920855e728235fb5e56d5fb3.
Independent physical bounds(10,10)-(30,20)mm; flip(10,30)-(30,40)mm; area200mm².

Full suite at `4df76b41ae9290bc626f37faa410a10f677b3615`:
`python -m pytest -q --junitxml=.venv/svg-final-pytest.xml`
**3084passed,2skipped,11warnings,310subtests in212.63seconds.**
Architecture/import/growth and frozen reference checks are included. The two existing upstream Qt
drafts and SWIG/Shapely warnings remain. Ignored local evidence: .venv/svg-final-pytest.log/.xml.

## Actual desktop
At the same runtime head, `python tests/smoke_app.py` exited0. Geometry and Gerber SVG imports,
physical bounds/area, unchanged source SHA/text, save/reopen and fixture cleanup passed:
SVG_PHYSICAL_SOURCE_ROUNDTRIP_OK. Root inspected the3840x2089 .venv/svg-smoke.png, showing both
objects and their coincident20x10mm material. The source fixture remains byte-identical.
All previous CAM/project/laser exports, read-only console, manual/preflight/job/dry-run journeys
passed, ending JOB_ACTIVE_SHUTDOWN_OK, PREFLIGHT_SHUTDOWN_OK, MACHINE_SHUTDOWN_OK and SHUTDOWN_OK.
Existing editor/QThreadStorage teardown warnings follow successful owned shutdown; no physical
controller or laser was used. Local evidence: .venv/svg-smoke.log and images.

## Limits and delivery
[Operator guide](../../docs/SVG_IMPORT.md), [contract](contracts/svg-import.md).
Curve centreline flattening and round-stroke tessellation each reserve0.005mm of the0.01mm physical
budget, adjusted conservatively for affine amplification. Precision/resource limits can reject
otherwise legal SVG; no browser rendering equality or manufacturing accuracy is claimed. General
intersecting compound paths, clipping, text/fonts, external CSS/resources, dashes and fractional
opacity remain explicit errors. Positive color is CAM material; white is not a subtraction tool.
PR/CI links and final merge evidence will be recorded after successful delivery.
