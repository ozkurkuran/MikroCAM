# Validation: SVG drill candidate review

Status: delivered; implementation, exact-head full suite, actual desktop and final-head Windows CI passed.
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
source/license details in THIRD_PARTY_CHANGES.md.
[PR19](https://github.com/ozkurkuran/MikroCAM/pull/19) merged as `8d79706b506d29e14f1d5d2eebd3f21fa16cb258`.
[Windows CI](https://github.com/ozkurkuran/MikroCAM/actions/runs/36292864325) passed in 6m52s at final head `082f15bd3566a41aeda75799db0baa7377b239d0`.

## Genuine vendor-export follow-up (2026-10-04)
Branch `test/vendor-svg-fixtures`; tests in `tests/test_vendor_export_fixtures.py`; fixture
license, source URL and hashes in each `provenance.json` under `tests/reference/cad-source/`.

Genuine drill review evidence (Illustrator, not Proteus): the unmodified Adobe Illustrator 25.3.0
export `illustrator-wortschule-hilfsverb/hilfsverb.svg` (MIT,
[wort-schule/wort.schule@eea2cf5d](https://github.com/wort-schule/wort.schule/blob/eea2cf5d856bff46ebc96b1dd472e869a604c31e/app/assets/images/montessori/hilfsverb.svg))
draws a white disc concentric with a red disc. With its XMP 50 mm page, drill review returns exactly
one candidate, centre and diameter (18.3600 mm) within 1e-6 mm of values derived from the exported
coordinates, before and after flip, with the heuristic notice. This is artwork, not a PCB.

Genuine Proteus evidence: `proteus-breath-analyzer/B_A_.svg` is an unmodified Proteus Design Suite
PCB SVG export (Apache-2.0,
[TengoCharlie/breath-analyzer@5872bbe2](https://github.com/TengoCharlie/breath-analyzer/blob/5872bbe211318a74ec51ccff3bf4ef2fc1d371b7/pcb%20bt%20woled/B_A_.svg)).
Source detection now identifies it as Proteus (see 020 follow-up). Geometry import, and therefore
drill review, still fails explicitly and atomically: 209 filled, unstroked paths carry
`vector-effect="non-scaling-stroke"`, which the 016 importer contract rejects; a test records that
error for Geometry and Gerber. The same failure affects 30 of the 35 permissively licensed Proteus
SVGs found (the other 5 contain text). A scratch-only diagnostic on a modified copy with
`vector-effect` removed (not retained, not evidence of compatibility) imported 351 shapes but gave
no drill candidate: Proteus writes holes as unclosed four-cubic circles (no `Z`) and this board's
pads are DIL/PPAD shapes, not circular pads, so the conservative heuristic would not apply anyway.

Still open: drill review on genuine Proteus output and physical drilling. Changing the
vector-effect policy or recognising coincident-endpoint circles changes established contracts and
needs its own spec; no behaviour was changed for 018.

Local checks at test head `51b65b3d` (CPython 3.13.13, `.venv/repro-a`): new fixture file 18 passed;
`tests/architecture` 83 passed; `pip check` clean. Full suite: 5856 passed, 3 skipped, 310 subtests,
12 failed only because the optional `resvg_py` (requirements-visual) is absent from that venv; the
same 12 fail identically on unmodified origin/main `70800e5b` there, and those five visual test files
pass (46) with the main `.venv`. Logs: `.venv/vendor-fixtures-*.log` (ignored). PR Windows CI is the
delivery gate.

## Spec 041 takibi (2026-10-04)
Yukarıdaki "Still open: drill review on genuine Proteus output" boşluğu [spec 041](../041-svg-vendor-compat/validation.md) ile kapandı.
Gerçek `proteus-breath-analyzer/B_A_.svg` içe aktarılır ve drill incelemesi 25 adayın tamamını
bulur: merkezler testte dosyanın ham `d` metninden bağımsız hesaplananlarla 1e-6 mm içinde
(flip açık/kapalı), çap 1,0001–1,00014 mm (dört kübik Bezier yaklaşımı), tek takım grubu ~1,00 mm.
Bu, dosyanın yanındaki Proteus CADCAM notundaki `D=1mm` ile uyumludur. Değişen sözleşme: tek alt
yol uçları 1e-6 mm içinde çakışıyorsa kapalı sayılıp aynı daire uyumuyla sınanır (360° şartı
korunur); dairesel destek yoksa ağırlık merkezi ≤0,02 mm ve deliği 0,01 mm payla içeren beyaz
olmayan dolu poligon pad destek olur. Delik merkezi/çapı yalnız beyaz daireden gelir.
Hâlâ açık: fiziksel delme, başka Proteus sürümleri ve diğer EDA araçlarının delik çizim biçimleri.
