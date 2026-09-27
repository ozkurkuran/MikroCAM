# Validation: SVG drill candidate review

Status: implementation, exact-head full suite and actual desktop complete; GitHub delivery pending.
Three stories, 36 tasks, no dependency or machine communication added.

## Requirements and design gates
FR001–004 / SC001: dedicated File/Import review uses existing bounded physical SVG import, exact
flip and resolved inherited white-fill facts. Native circle axes and sampled full closed paths are
validated as circles; bounding boxes alone, empty rendered shapes, compound/open/hidden/isolated
artwork and stroked white circles cannot qualify. Source identity and tolerances remain visible.
FR005–007 / SC002–003: initial selection is empty. Unique reviewed centres form deterministic
nonchained diameter groups within0.01mm, represented by their mean. Duplicate evidence collapses;
conflicting overlaps are excluded. Grouping rechecks that mean tool diameters do not create overlap.
Factory defaults/units are preserved; one boundary conversion precedes complete geometry and
synchronous local-use source export. Failure returns before collection publication.
FR008–010 / SC004–005: path/flip edits clear review; same-path byte changes are caught by bounded
SHA verification before creation. Plain text feedback, cancellation and parent-owned dialog lifetime
are tested. Existing Excellon persistence is used; no new project schema.

All eight gates pass. Core/domain/bridge/UI imports respect the dependency direction; only6legacy
hook lines added. Concrete records/functions/dialog, existing dependencies/units/placement, no
controller path, tests first, three stories. Largest new module214lines; largest function59lines.
Neo MIT behavior trace and full notice are retained; no external module copy/merge.

## Tests first and audit fixes
Initial tests failed on missing records, white-fill helper, grouping and bridge/UI APIs. Additional
red regressions caught grouping-induced overlap and duplicate physical centres, source hash changes,
UI accepting None/fail, and an empty ellipse with an omitted radius inventing a native circle.
The fixes preserve existing material and explicit source facts. Closed arc paths may contain a
redundant closing point; fitting removes only redundant terminal/consecutive coordinates.
Independent read-only audit found no further blocking issue; root found and tested the empty-render
edge while reviewing later SVG integration. No fixture or frozen reference artifact was changed.

Focused feature tests:161passed before the final empty-render regression; detector43passed after it.
Architecture plus then-current detector/grouping:158passed in66.29s. Actual MM/IN Excellon parser,
geometry/local exporter/reparse verify a2.54mm tool and25.4/50.8mm centre; supplied defaults persist.
Final runtime head: `569f10d84502b9edba4d031d83d1a34b537ccd9d`.
Full command: `python -m pytest -q --junitxml=.venv/svg-drill-pytest.xml`.
At final runtime head: 3380 passed, 2 skipped, 11 warnings, 310 subtests passed in 224.50 seconds. The two existing upstream placeholders and dependency warnings remain unchanged.

## Actual desktop at final runtime head
`python tests/smoke_app.py` exited0. Import review shows three physical candidates; selecting first
and third creates two tools/two holes at(15,37)/(35,37)mm with0.8/1.2mm diameters. Export/reopen and
project save/reopen preserve them and source SVG bytes remain unchanged.
Marker: SVG_DRILL_REVIEW_EXCELLON_ROUNDTRIP_OK. All prior SVG/report/CAM/project/laser/manual/
console/preflight/streaming/dry-run journeys pass through JOB_ACTIVE_SHUTDOWN_OK,
PREFLIGHT_SHUTDOWN_OK, MACHINE_SHUTDOWN_OK and SHUTDOWN_OK. Existing Qt teardown warnings remain.
Root inspected760x600 `.venv/svg-drill-smoke.png`: unchecked middle hole, readable mm values,
source hash, tolerance/heuristic notice, proposed two-tool summary and enabled explicit creation.

An initial smoke asserted a fixed 0.001 mm roundtrip tolerance inconsistent with default inch
output at four decimals. The check now uses the configured coordinate/tool output quantum
(0.00254mm default), plus0.0001mm for the existing0.03937 conversion approximation on this<=37mm
fixture. It does not loosen the unexported object check (1e-6mm). No exporter behavior was changed.
Local logs: `.venv/svg-drill-pytest.log`, `.venv/svg-drill-smoke.log` (ignored).

## Provenance and limits
Original MIT analytic fixture: `tests/reference/svg-drills.svg`, exact SHA256
`e36bdbcba42c63164e9ddd392957fccd8adfd168f0f0c5c965c8702a780aaa48`; marked-text-off for byte stability.
This is Proteus-style artwork, not a genuine Proteus export. No authentic licensed vendor fixture
was found; real Proteus export compatibility and physical drilling remain unverified. The workflow
is a reviewed heuristic; it does not infer slots, general clipping or manufacturing intent.
See [operator guide](../../docs/SVG_DRILLS.md) and [contract](contracts/svg-drills.md).
Neo behavior adaptation implementation commit: `60c16b76603c191707982ebd0aec5d074fedbdbe`;
source/license details in THIRD_PARTY_CHANGES.md. PR/CI/merge links pending delivery.
