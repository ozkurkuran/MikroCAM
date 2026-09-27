# Validation: Geometry circles to Excellon

## Requirements and gates

FR001–003 / SC001: current single/per-tool authority, explicit units, conservative physical
circle fitting, role/source identity and bounded exclusions are covered by analytic tests.
Multi-tool tests deliberately use a stale unrelated top-level cache. Primitive geometry
type and validated original WKB are fingerprinted before mm conversion; container shape,
typed tool labels, name and units are also covered.

FR004–005 / SC002: dialog candidates start unchecked, and selection displays mean-diameter
tool groups. Full-spread grouping and final footprint overlap checks are shared with SVG.
Duplicate comparisons use the first retained representative, with visible counts. Absolute
deduplication tolerances can collapse distinct very small contours; this limit is documented.

FR006–008 / SC003–004: source identity and bounded content are checked at both factory guard
points. Tests cover name, units, mode, tool keys, geometry, removal and replacement; failures
before initialization and during export prevent publication. Factory defaults and source
data are retained. Unit conversion occurs once at each explicit boundary.

FR009–010 / SC005: shared circle/group/factory APIs retain unchanged SVG behavior. Tests
cover nesting/node/coordinate/contour/candidate/notice budgets, cyclic lists, invalid and
nonplanar input. Actual host and desktop evidence is recorded below when complete.

All eight design gates remain satisfied. Core is stdlib/NumPy/Shapely only; bridge owns
host access; UI presents selection. The only production legacy change is a six-line menu
hook. Shared abstractions each serve SVG and Geometry. No new dependency, persistent schema,
hardware I/O or external code import. Three stories, 39 tasks.

## Tests first and audit

Shared fitting, pure review/selection and bridge tests first failed for missing modules.
Record and UI tests similarly preceded implementation. Shared grouping/factory tests first
failed for missing APIs. Additional red regressions demonstrated integer overflow validation,
invalid overlapping MultiPolygon parents, and identical WKB for LinearRing/LineString.
Fixes validate bounded children before parent topology and fingerprint primitive type.
Independent audit confirmed those fixes and found a valid source fingerprint could accompany
forged measurements in a constructed review. A red regression preceded requiring exact fresh
review equality at the bridge, including candidates and notices. Absolute small-circle
deduplication and the 10,000-duplicates-per-candidate cap remain explicit conservative limits.
Focused Geometry/shared/SVG suite: 319 passed. Architecture plus initial Geometry checks: 221 passed.
Legacy growth: +6 of the allowed +50 lines against 97e3e920. Actual MM/IN exporter/parser
checks: four cases passed, covering single and multi-tool authority. Largest new module185
lines; no function exceeds80 lines. Full/desktop evidence follows at the committed runtime head.

## Full suite and actual desktop

Production runtime commit: `0c70d8c9e2d89078c6937329b3c73435a5ce759e`.
At that head, `python -m pytest -q --junitxml=.venv/geometry-drills-pytest.xml` passed:
4069 tests, 2 skipped, 11 existing dependency warnings and 310 subtests in243.60s.
This includes frozen references, import boundaries and growth against97e3e920.

The first desktop run exposed a smoke-helper error: deep-copying the host LoudDict followed
its callback into a Qt owner. Test-only commit `3bfa470ab7299546d2eba6b06c4d55c1f3de8632`
now snapshots a plain dictionary and creates a nonempty source tool so tool preservation is tested.
Production files are unchanged from the full-suite head. At that commit,
`python tests/smoke_app.py` exited0 with GEOMETRY_DRILL_SELECTED_EXCELLON_ROUNDTRIP_OK
and all prior SVG/CAD/CAM/laser/manual/console/preflight/streaming/dry-run journeys through
SHUTDOWN_OK. Sources, nonempty tools, settings and source text survived selection, export/reparse
and project reopen. Root inspected `.venv/geometry-drill-smoke.png` (760x600): three physical
circles, only0.8mm and1.2mm selected, middle1mm unchecked, correct two-tool summary and action.
Existing Qt shutdown warnings remain. Final-head CI will rerun the complete suite.

## Provenance and limits

Independent extension of MikroCAM's existing SVG circle-fit/group/factory code. No external
module was copied or merged. Authored analytic geometry verifies measurement, selection,
export and persistence, not manufacturing intent or physical machine operation.

## Delivery

Final reviewed head: `a5bacf1788dd1065f68c6cbf27a8401840ca3024`.
[PR22](https://github.com/ozkurkuran/MikroCAM/pull/22) merged as
`2bf56a92d9610f425169d960d4e026b58bbe148f` after final-head
[Windows CI](https://github.com/ozkurkuran/MikroCAM/actions/runs/36296724041)
passed in6m37s. Delivery documentation changes no runtime.
