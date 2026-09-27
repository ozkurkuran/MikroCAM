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
zero-diameter export rejection and six mixed-unit export cases.

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

Pending final runtime head and actual desktop screenshot inspection.

## Provenance and limits

Independent implementation using existing MikroCAM shared factory and pinned Shapely
centreline distance. No external code copied. Exact normalized floating-point equality is
deliberate; no hidden positional/diameter tolerance. Existing exporter quantization applies.
Authored operations verify software behavior and preservation, not physical manufacturing.

## Delivery

Runtime commit, PR, final-head Windows CI and merge pending.
