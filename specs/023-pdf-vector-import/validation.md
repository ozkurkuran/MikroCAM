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
Largest new production module325lines; longest function56lines. Legacy top-ten growth is+6/50
against82e4722e. Final focused reader/operator/geometry/bridge/UI/license checks:181 passed in3.05s.
Original notice bytes intentionally retain their recorded line endings; `git -c
core.whitespace=cr-at-eol diff --check` passes without rewriting licensed source bytes.

## Full suite and desktop

Runtime commit `b0a11e052bc5db96ef8865476e3bf779c5bd9b77`: complete suite passed4503tests,
2skipped upstream templates,11existing dependency warnings and310subtests in263.22s. Frozen
reference, existing PDF/SVG and all previous behavior remain covered.

At this exact runtime head the actual desktop completed all journeys and SHUTDOWN_OK, including
PDF_VECTOR_SELECTED_PAGE_CROP_FLIP_DXF_PROJECT_OK. Root inspected780x680 PDF review screenshot.
Visual review found crop placeholders disappeared after entering values. UI-only commit
`611dc0c2ef9487a4bb6c4f40131c76508be8eae2` adds persistent minX/minY/maxX/maxY labels and
accessible names;18UI/report tests pass. A second complete desktop run at this head exited0;
the updated screenshot was inspected and labels remain visible. Geometry/reader/factory logic is
identical to the complete-suite head; final-head Windows CI reruns the full suite.

Desktop proof uses two authored compressed pages, chooses the second, crops physical coordinates
and flips once. Normal Geometry is exported to DXF and reparsed, then project save/reopen after
deleting the original PDF retains exact source bytes, report, geometry and normal defaults.
Existing native Qt teardown warnings remain. Screenshot `.venv/pdf-vector-smoke.png` is a local
validation artifact, not shipped source data.

## Delivery

[PR24](https://github.com/ozkurkuran/MikroCAM/pull/24) merged final head
`ae811f40dfcbc618f39f78f492f2ce78640fd4fd` as
`47141e972169d3b6d5383ee534fd958008539c6f`.
[Final-head Windows CI](https://github.com/ozkurkuran/MikroCAM/actions/runs/36299527969)
passed in6m39s. All39tasks complete. Authored software fixtures do not establish physical
manufacturing accuracy or vendor-wide PDF compatibility.
