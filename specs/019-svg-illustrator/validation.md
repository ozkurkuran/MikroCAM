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

## Genuine vendor-export follow-up (2026-10-04)
Branch `test/vendor-svg-fixtures`; tests in `tests/test_vendor_export_fixtures.py`. Two unmodified
genuine Illustrator SVG exports now complement the authored analytic fixture above; license,
source URL, SHA-256 and Git blob hash are in each `provenance.json` under `tests/reference/cad-source/`.

- `illustrator-wortschule-hilfsverb/hilfsverb.svg`: Adobe Illustrator 25.3.0 export (MIT,
  [wort-schule/wort.schule@eea2cf5d](https://github.com/wort-schule/wort.schule/blob/eea2cf5d856bff46ebc96b1dd472e869a604c31e/app/assets/images/montessori/hilfsverb.svg),
  retrieved 2026-10-04). The root has only `viewBox="0 0 141.732 141.732"`; the 50x50 mm page comes
  solely from XMP `MaxPageSize` (Millimeters), reported per axis. Geometry and Gerber, with and
  without flip, match bounds derived from the exported circle coordinates within 0.01 mm; the
  report keeps absent source units and the source SHA-256.
- `illustrator-commons-history-of-china/History_of_China_for_template_heading.svg`: Adobe
  Illustrator 24.1.0 export (public domain, PD-self by Lá»‡ XuÃ¢n,
  [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:%22History_of_China%22_for_template_heading.svg),
  Commons SHA-1 verified; only the Windows-invalid file name was changed). It has nested layer groups,
  embedded class CSS, a fill:none construction rect, nonzero compound lettering with 25 counters and a
  stroke-only frame whose bounds and area (exact ring, rel 1e-9) are asserted analytically.

Bug found and fixed (test first): Illustrator SVG 1.1 exports write
`style="enable-background:new 0 0 W H"` on the root, which the importer rejected as an unsupported
CSS property. The property only prepares filter background input; filters remain unsupported, so it
cannot change material. Its SVG 1.1 grammar is now validated and otherwise ignored; malformed values
still fail. The Commons fixture fails on the pre-fix importer and passes after commit `ae99f4c3`.
In a scratch probe of 731 Commons SVGs with an Illustrator marker, imports rose from 24 to 91: 67 of
88 files blocked only by this property now import; 21 fail later on other explicit limits.

Remaining genuine-export limits, unchanged and explicit: 507 of those 731 files (69%) are rejected
because the 016 import contract refuses every DOCTYPE, even the fixed SVG 1.1 public DOCTYPE that the
020 detector already inspects offline (459 plain, 48 with internal entity subsets). Next most
common: pattern (46), gradient/paint-server references (25), font properties or text (23) and the
complex-fill budget (8). Accepting the fixed public DOCTYPE without an internal subset would need its
own spec because it changes the 016 contract; it is recommended as follow-up work.

Search record: Commons CirrusSearch `incategory:Valid_SVG_created_with_Adobe_Illustrator` intersected
with CC-Zero, PD-self, PD-user, PD-author, CC-BY-4.0 and CC-BY-3.0, plus the Diagrams and Unspec
categories, size below 900 KB (1129 files fetched before Wikimedia rate limiting, 731 with an
Illustrator marker); GitHub code search for `xmpTPg:MaxPageSize` with `Adobe Illustrator` and
physical `stDim:unit` values, permissive repositories only. Rejected: `Counting the triangles.svg`
(CC0 but a derivative of a PNG whose license could not be traced), `Ageha inverted.svg` (current
bytes hand-corrected by a later editor), `Apple Mac Mini M4.svg` (product depiction, mask
unsupported), Assemblyline `al-robot.svg` (only copies of government branding with unclear
provenance), Openclipart Illustrator files (internal entity DTDs) and company or university logos
in permissively licensed website repositories (the code license does not cover third-party marks).

Still open: genuine Illustrator clipping. Only 18 genuine Illustrator files in the probe contain
clip paths; 17 fail earlier on other limits and the remaining one carries an Inkscape re-save
marker, so clipping stays covered by the authored analytic fixture only. Physical manufacturing
remains unverified.

Local checks at test head `51b65b3d` (CPython 3.13.13, `.venv/repro-a`): new fixture file 18 passed;
`tests/architecture` 83 passed; `pip check` clean. Full suite: 5856 passed, 3 skipped, 310 subtests,
12 failed only because the optional `resvg_py` (requirements-visual) is absent from that venv; the
same 12 fail identically on unmodified origin/main `70800e5b` there, and those five visual test files
pass (46) with the main `.venv`. Logs: `.venv/vendor-fixtures-*.log` (ignored). PR Windows CI is the
delivery gate.
