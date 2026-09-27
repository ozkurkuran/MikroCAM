# Validation: selected PDF vector page

## Requirements and constitution

| Requirement | Evidence |
| --- | --- |
| FR001 | Legacy page/affine prototype and permissive-reader/license comparison in research.md |
| FR002–003 | Reader isolation, inherited boxes, units/rotation and affine/path tests |
| FR004–005 | Analytic crop/flip, fill winding/holes, white paint, strokes and delayed clipping tests |
| FR006 | Source/decoded/tree/operator/state/path/point/overlay limits and malformed records |
| FR007 | Explicit page/options review; every source/option edit invalidates creation |
| FR008–009 | Fresh bytes/report/WKB verification; two initializer source guards; defaults retained |
| FR010 | Real MM/IN Geometry, DXF reparse and lossless source/report serialization tests; desktop/full below |

SC001–002 use analytic physical bounds/topology, including different pages and independent
subpaths. SC003 covers unsupported/invalid input, forged review and source changes before and
during initialization. SC004 uses actual Geometry/export/serializer paths and normal defaults.
SC005 requires the full suite, desktop and final-head CI before delivery.

All eight gates remain YES: core/domain/bridge/UI import direction, short legacy hooks, one
licensed pinned lazy reader justified by existing limitations, mm authority and optional schema1,
tests before algorithms/guards, no machine/controller changes, independent helper reuse and full
BSD license, and three stories within39 tasks. No architecture exception or project-format change.
The extra concrete core/pdf_paths.py keeps current-path state separate from paint/clip state.

## Test-first and audit evidence

Record/codec, reader, physical frame/operator and factory tests initially failed for missing
modules before implementation. Additional regressions first failed for cumulative stroke output,
combined sampled/final point limits and malformed/indirect annotation containers, then passed
after the bounded fixes. Luna independently reviewed frame/path/clip/paint/reader/factory semantics;
the falsey malformed annotation finding was fixed with three direct regressions. The explicitly
bounded miter range1..1000 is documented consistently with the shared stroke helper.

Reader limits use pypdf's public context-local configuration plus pinned instance-level hooks;
final operand tails cannot be silently dropped. A crosshatch test rejects excessive intersection
candidates before GEOS face creation. Source mutation after object assignments is caught by the
second initializer guard. Same-source forged geometry is rejected by fresh interpretation.

Actual Geometry tests pass for MM and IN: selected second page, physical crop and flip, expected
12.7/25.4/38.1/38.1mm bounds and322.58mm² area; DXF contour reparse, normal default tool data,
Latin1 exact PDF bytes and schema-one report survive real JSON serialization after source deletion.

## Focused checks and dependency provenance

Initial PDF/architecture batch:319 passed in78.22s. Subsequent reader/report/UI/license batch after
annotation fixes:104 passed in1.76s. Both reproducible environments have pypdf6.19.0 installed and
`pip check` is clean; reader/license tests passed in each. The exact wheel SHA256 is
7e5d6e730e7dae87d560a2cee218b852f6498c8be61966f3cd02ead971e48d14. Original BSD-3-Clause license
hash a97ac230e5f33ef10a5367a850eb01f91f1a0b064e34742c7794d2294557f524 is inventoried unchanged.
No AGPL runtime, borrowed algorithm, external process, raster conversion or vendor fixture added.
Largest new production module325lines; longest function56lines. Final growth/complete checks below.

## Full suite and desktop

Pending final runtime commit, complete suite and actual desktop screenshot inspection.

## Delivery

Pending focused PR, final-head Windows CI and merge. Authored software fixtures do not establish
physical manufacturing accuracy or vendor-wide PDF compatibility.
