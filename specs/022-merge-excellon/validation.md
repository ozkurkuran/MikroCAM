# Validation: reviewed Excellon merge

## Requirements and gates

FR001–003 / SC001: selected owner identity, current MM/IN tool operations, exact diameter
groups and complete sequential tool mapping have pure and bridge tests. Cached geometry
and historical source text are deliberately unrelated in fixtures. Absent drill/slot keys
are supported for sparse programmatic records. The normal parser fills both keys at completion;
actual parser/export cases and explicitly sparse records are tested separately.

FR004–006 / SC002–003: exact first-representative duplicate removal records every source
reference; reversed slots retain original direction. Analytic capsule checks cover holes,
endpoint/interior drill-slot contacts, crossing/parallel/collinear slots and exact tangency.
The first 200 conflict details accompany the full total; creation checks that total.
The dialog remains inert until explicit analysis/creation and displays current-default policy.

FR007–009 / SC004: exact fresh review equality and collection membership checks run at both
factory checkpoints. Tests reject changed names, units, IDs, diameters, endpoints, removal,
replacement and forged output records. Current source settings/caches are not operation
authority. Complete source state and factory defaults are checked unchanged on success.
Input/tool/operation/coordinate bounds and malformed records fail before publication.

FR010 / SC005: shared slot-capable factory preserves the prior SVG/Geometry API. Actual
MM/IN routing/G85 and slot-only exporter/parser cases pass. Full and desktop evidence follows.

Eight gates remain satisfied: strict core/bridge/UI boundaries, six-line legacy menu hook,
shared factory with multiple real users, explicit unit/default ownership, tests first,
no hardware I/O, no external code or dependencies, three stories and 39 tasks. No schema
addition or frozen reference change. Largest new module168lines and largest function53lines. Legacy growth is+6 of the allowed+50
against12704264. Initial merge/shared plus architecture suite:274passed in75.10s. Final focused
merge/shared/SVG/Geometry compatibility suite:392passed in25.89s, including actual METRIC/INCH
zero-diameter export rejection, four mixed-unit merge roundtrips and four shared slot export cases.

## Tests first and audit

Physical tools/models/review/bridge/factory/UI tests first failed for missing APIs. A design
audit prompted support for sparse operation records; follow-up actual-parser testing corrected
the audit assumption because ParseExcellon normalizes both keys at completion.
MM/IN exact-equality regressions document binary roundoff remaining distinct. A red UI
regression showed 12-digit formatting hid this distinction; shortest round-trip float text
and column sizing now expose the actual unequal diameters. Two red regressions then showed legacy export precision could round a positive diameter to zero.
The shared factory now rejects an emitted zero-diameter tool header before publication. A further
red regression showed JSON tuple-to-list slot persistence changed an otherwise identical operation
fingerprint. Hashing now uses operation kinds/counts/order and original point bytes, independent of
equivalent list/tuple container types. The desktop fixture uses normal imported tuple slots unchanged;
only the comparison snapshot normalizes this documented JSON representation difference.
Final test evidence is recorded here as completed.

## Full suite and actual desktop

Production runtime commit: `d0a96f6accbda21157bdb10e87a4a1b4de7ba8fd`.
At that head, `python -m pytest -q --junitxml=.venv/excellon-merge-pytest.xml` passed:
4269 tests, 2 skipped, 11 existing dependency warnings and 310 subtests in259.58s.
Frozen reference, architecture and growth checks use base12704264.

The first desktop attempt exposed a helper-only field-name error: the actual host option is
`tools_drill_feedrate_z`. Test-only commit `fcff46bc213d6de26bd774ce12fcb24f0b2f2338`
uses that field and authors matching source object/tool settings, since normal host UI rebuilds
tool settings from object options. Production code remains identical to the full-suite head.
At this head `python tests/smoke_app.py` exited0 through all prior journeys and SHUTDOWN_OK,
with EXCELLON_MERGE_SELECTED_DRILL_SLOT_ROUNDTRIP_OK reporting two removed exact duplicates.
Normal imported slot tuples pass project JSON roundtrip without modifying the input fixture;
source snapshots normalize only equivalent tuple/list slot container representation for comparison.
All physical operations, original source text, object/tool settings and destination defaults survive.
Root inspected `.venv/excellon-merge-smoke.png` (800x720): two sources, five input tool mappings,
two output tools, retained slot, two duplicate references and zero conflicts. Existing Qt teardown
warnings remain. Final-head CI reruns the complete suite.

## Provenance and limits

Independent implementation using existing MikroCAM shared factory and pinned Shapely
centreline distance. No external code copied. Exact normalized floating-point equality is
deliberate; no hidden positional/diameter tolerance. Existing exporter quantization applies.
Authored operations verify software behavior and preservation, not physical manufacturing.

## Delivery

Runtime commit, PR, final-head Windows CI and merge pending.
