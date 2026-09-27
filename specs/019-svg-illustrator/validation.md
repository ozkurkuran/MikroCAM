# Validation: Illustrator SVG appearance

Status: delivered; exact-runtime-head full suite, actual desktop and final-head Windows CI passed.
Three stories, 39 tasks, no new dependency or machine communication.

## Requirements and eight gates
FR001–003 / SC001: exact Adobe XMP namespaces, direct root SVG metadata provenance, independent
axis fallback and explicit root precedence are tested. Raw percentages survive in historical
reports. Simple offline CSS has bounded grammar/cascade; metadata and foreign styles are inert.
Layer visibility follows hierarchy and labels are bounded without overflowing the flip notice.
FR004 / SC002: disjoint/nested contours keep the established path; touching/crossing contours
use bounded noding, polygonization and source winding, including duplicate/opposite rings.
Original source paths are retained. Large-coordinate orientation uses robust ring orientation.
FR005–007 / SC003–004: local clip shape union, nested application intersections, definition-owned
clip-rule, paint-independent silhouettes, group unstroked bounding boxes and one physical flip
are checked analytically. Empty clips remove material; edge-only contact cannot create a cutting
line from a polygon. Segment/pair/point/application budgets bound topology work. Missing/external
references, cycles, excess shapes/chains, unsupported definition content and degenerate boxes fail.
Actual Geometry/Gerber failure tests preserve original geometry, tools and source after valid
artwork followed by invalid clipping, empty material or an oversized definition.
FR008–010 / SC005: report bounds describe clipped material; path counts describe original source
evidence. Clipped circles cannot qualify as full drill candidates. Schema2 writes percentage
tokens and reads/migrates strict schema1; old absent reports remain supported. Desktop validation
and complete regression results are recorded below when run.

All eight design gates pass: correct core/importers/bridge/UI dependency direction; zero legacy
production growth; concrete helpers and existing dependencies; one existing physical transform
authority; tests first; no controller path; retained MIT source trace; three stories/39tasks.
Largest changed production module248lines; largest function47lines. Import-boundary plus authored
fixture checks:51passed. No frozen reference helper/output or external dependency was modified.

## Tests first and audits
Initial record/metadata/CSS/compound/clip tests failed before their implementations. Subsequent
red regressions caught the official Adobe namespace spelling, foreign/metadata CSS provenance,
XMP outside root metadata, clipping CSS paint semantics, edge-only intersection material dimension,
clip topology preflight and the many-layer/flip notice overflow. Independent read-only clipping
audit found no further confirmed blocker; six additional analytic scope/reference boundary cases pass (root bbox/viewport transform, repeated use, cycle, exact depth limit and pair preflight).
Focused SVG and report suite:898passed,3dependency warnings in8.32s before final extra scope cases.

## Full suite and actual desktop
Final runtime commit: `fc973e42ba1992d871954d759715a7f7dab6a1a7`. Commands: `python -m pytest -q --junitxml=.venv/illustrator-pytest.xml`
and `python tests/smoke_app.py`. Logs/screenshots remain ignored under `.venv/`.
At that exact runtime head:3625passed,2skipped,11warnings,310subtests in231.82s. Existing upstream
placeholders/dependency warnings remain. Full suite includes frozen reference, architecture and
legacy-growth checks (base04c237da). No runtime edits occurred during validation.
Actual desktop exited0 with SVG_ILLUSTRATOR_AUTHORED_SOURCE_REPORT_ROUNDTRIP_OK, both Geometry
and Gerber roundtrips, retained raw percentages/XMP page/source SHA and unchanged fixture bytes.
All previous CAM, SVG/drill, laser, console, manual, preflight, streaming and dry-run journeys passed,
including JOB_ACTIVE_SHUTDOWN_OK, PREFLIGHT_SHUTDOWN_OK, MACHINE_SHUTDOWN_OK and SHUTDOWN_OK.
Root inspected `.venv/svg-illustrator-smoke.png` (3840x2089): two disjoint clipped material strips,
expanded historical source report and preserved page dimensions. Existing Qt teardown warnings remain.

## Provenance and limits
Original MIT-authored analytic fixture `tests/reference/svg-illustrator.svg`:1529bytes, SHA256
`e248379d4d030c46516f3763938e9aa4df7013342371dc152403c228917f3727`, byte-stable via `.gitattributes`.
XMP page60x40mm; CSS hides construction artwork; evenodd compound contours clipped to two strips
have area130mm², bounds(15,11,35,24)mm or(15,16,35,29)mm after flip.
This is an authored Illustrator-style fixture, not a genuine Illustrator export. Real licensed
vendor-export compatibility and physical manufacturing remain unverified. Unsupported masks,
filters, fonts, external/complex CSS and clipping inside clip definitions fail explicitly.
See docs/SVG_IMPORT.md, docs/IMPORT_REPORT.md and THIRD_PARTY_CHANGES.md for supported semantics,
schema migration and immutable Neo MIT adaptation sources.

## Delivery
[PR20](https://github.com/ozkurkuran/MikroCAM/pull/20) merged as `c6a8441256a45414f7d48e4c1748b34bfaf3733c`.
[Windows CI](https://github.com/ozkurkuran/MikroCAM/actions/runs/36294387159) passed in6m51s at final head `70485359f6d34a2dc0934c4026d54cb16ca0bc61`.
