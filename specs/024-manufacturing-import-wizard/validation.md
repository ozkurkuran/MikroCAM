# Validation: manufacturing file set review

## Requirements and constitution

| Requirement | Evidence |
| --- | --- |
| FR001–002 | Bounded local collection, canonical deduplication, distinct-name/content preservation and per-row read errors |
| FR003–004 | Separate content/metadata/filename evidence; unknown/conflicting roles; inner copper and plating regressions |
| FR005–006 | Explicit compatible assignments, unique names and fresh-source review; edit/collection invalidation |
| FR007–008 | One existing worker, sequential normal factories, explicit parser failure rejection, first failure stops |
| FR009–010 | Exact Latin1 source bytes and strict schema1 report; actual MM/IN parsers, defaults and serializer roundtrip |

SC001–005 are exercised by classification/guard/UI/actual-object tests and the complete desktop
journey below. All eight constitution gates remain YES. New code follows the existing core,
importer, bridge and UI boundaries, with short legacy hooks and no runtime dependency. No
machine commands, new project format, external algorithm or copied vendor implementation added.
Three stories and39tasks retain a single deliverable.

## Test-first and independent audit

Strict records/codec, classifier and bridge tests preceded implementations. Additional failing
regressions exposed stale review after collecting files, malformed FileFunction casing, eager
Excellon line allocation and extended Gerber block splitting before count limits. The fixes
invalidate old inspection and stop incrementally at the configured limits. Source guards also
reject changes after parsing and host unit changes before factory conversion. Invalid, empty,
nonplanar and excessive geometry trees fail before publication.

Luna reviewed parser/classifier/factory/UI behavior independently. The output coordinate cap
is explicitly in parser source units; the normal host factory owns subsequent unit conversion.
Gerber compact X2 attributes are removed as individual statements, preserving adjacent drawing
commands and complete aperture macro blocks. Excellon parser failure is checked directly.

Authored analytic fixtures cover Gerber strokes, macro holes and Excellon drills with both MM
and IN source/host combinations. The legacy stroke buffer uses its existing width/1.999 rule;
compact commands are compared with independently arranged conventional commands at1e-6mm.
The31 existing licensed reference files span10 boards; provenance remains in the corpus.
No claim of universal vendor compatibility or physical manufacturing validation is made.

## Checks

Focused manufacturing/helper suite:286passed,3existing SWIG warnings in4.29s. Real parser,
normal factory conversion/defaults and actual serialization after deleting source files are
included. Complete runtime suite, desktop and final-head Windows CI are recorded below when run.

Runtime commit: `7092e4cd56bdf3ca36d00b4cb70b8f353242b473`.

Full suite at this head:4789passed,2upstream templates skipped,11existing warnings and310subtests
in281.35s. Architecture and legacy-growth gates passed as part of this run. A simultaneous
desktop run completed the new four-file journey but later timed out in the existing X-jog
journey; it is not counted as a passing desktop run. No runtime machine code changed.

UI-only commit `45ad2010` replaces cramped escaped evidence with a concise cell and readable
multiline tooltip while escaping each untrusted detail. Its regression first failed, then9UI
tests passed. A standalone complete desktop run at this head exited0 with all previous journeys,
MANUFACTURING_DROP_FOUR_ROLES_LATIN1_REPORT_PROJECT_OK and SHUTDOWN_OK. Root inspected the
1100×650 screenshot. Exact source/report/defaults and geometry survive project reopen after
deleting all four source files. Final-head CI reruns the complete suite including the UI fix.

## Delivery

[PR25](https://github.com/ozkurkuran/MikroCAM/pull/25) merged final head
`8c793c2044fdaafb5b53723c1f88a090c617debb` as
`26637e0bd9b3a746a7ad36acdd4421c92d4b6d58`.
[Final-head Windows CI](https://github.com/ozkurkuran/MikroCAM/actions/runs/36300977639)
passed in7m31s. All39tasks complete. Existing physical/vendor validation limitations remain.
