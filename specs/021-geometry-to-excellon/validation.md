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
checks: four cases passed, covering single and multi-tool authority. Largest new module183
lines; no function exceeds80 lines. Full/desktop evidence follows at the committed runtime head.

## Full suite and actual desktop

Pending final runtime head, full regression and actual desktop screenshot inspection.

## Provenance and limits

Independent extension of MikroCAM's existing SVG circle-fit/group/factory code. No external
module was copied or merged. Authored analytic geometry verifies measurement, selection,
export and persistence, not manufacturing intent or physical machine operation.

## Delivery

Runtime commit, PR, final-head Windows CI and merge pending.
