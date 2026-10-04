# Validation: CAD source evidence

Status: implementation, exact-runtime-head full suite and actual desktop passed; final-head Windows CI pending.
Three stories, 38 tasks. No dependency or controller path added.

## Requirements and gates
FR001–004 / SC001–002: finite explicit producer declarations and actual metadata namespaces return
KiCad, Illustrator, Inkscape, Proteus or Unknown. No filename, layer, geometry, units or DXF version
scoring. Missing/unsupported claims stay unknown; conflicting supported/unsupported claims stay
Unknown with evidence. Namespace declarations and generic XMP page dimensions never imply origin.
FR005–006 / SC003: stdlib-only bounded offline parsers; no external DTD/resource loading. Source
byte/XML/line/pair/evidence limits return unavailable without a partial positive. Actual SVG/DXF
Geometry/Gerber handler tests preserve exact BOM/CRLF source identity and geometry/defaults when
producer metadata changes. Successful imports call only short UI-to-bridge hooks.
FR007 / SC004: optional independent schema1 record, strict shape/byte bounds and domain semantic
validation on actual bridge reads/writes. Old missing fields remain None; bad records do not break
object restore and their display clears stale facts. Parent-owned plain-text section is collapsed
and reads retained data only. JSON roundtrips after deleting source files preserve historical data.
FR008–009 / SC005: licensed real KiCad outputs and upstream Inkscape asset are classified with exact
provenance checks; authored syntax cases cover the four application families. Complete regression
and desktop results are recorded below when run.

All eight gates pass: core records/codec, importer parsing, bridge ownership and UI presentation
respect dependency boundaries; only10 net legacy hook/persistence lines; no generic registry or new
dependency; physical ImportReport2 and coordinate/default authority unchanged; tests first; no
hardware I/O; retained MIT behavior trace/licensed fixtures; three stories/38tasks. Largest new
module111lines, largest function40lines. Existing physical-report UI API remains isolated; each
host object calls the source section beside it. No frozen reference harness/output changed.

## Tests first and audit
Missing records/codec/parsers/bridge/UI produced initial red tests. Twelve meaningful host tests
failed before optional fields/hooks were added, then passed for all four kind/format combinations.
Independent audit reproduced foreign nested metadata producing a false Illustrator claim and a
stored claim whose application disagreed with its producer text. Six red regressions preceded
nested-metadata pruning and a domain evidence validator at the bridge boundary; all pass. Core codec
stays independent of domain parsing. Follow-up audit found no new parser/bridge/UI blocker.
Additional tests check exact DTD placement, no partial claims on excess evidence, deduplication,
namespace aliases, genuine unmarked DXF, unsupported encodings and exact identity bounds.
Focused source/import-report/host/persistence plus import-boundary suite:469passed,3existing
dependency warnings in3.90s. Core/schema alone85passed; host12passed.

## Full suite and actual desktop
Final runtime head: `2fac34880ce96d9a5187d1d020552f58b99dfa5c`. Commands: `python -m pytest -q --junitxml=.venv/cad-source-pytest.xml`
and `python tests/smoke_app.py`. Ignored logs/screenshots under `.venv/`.
At that exact runtime head:3880passed,2skipped,11existing dependency warnings,310subtests in234.81s.
Full suite includes frozen reference, architecture and legacy-growth checks against a596e2cf.
Actual desktop exited0 with CAD_SOURCE_AUTHORED_SVG_DXF_GEOMETRY_GERBER_ROUNDTRIP_OK for four
objects. Temporary input files were removed before project reopen; exact source/hash/assessment,
physical geometry and machining defaults survived. All prior SVG/drill/Illustrator/CAM/laser/manual/
console/preflight/streaming/dry-run journeys passed through SHUTDOWN_OK. Existing Qt teardown
warnings remain. Root inspected `.venv/cad-source-smoke.png` (3840x2089): current DXF Gerber,
expanded historical producer evidence and separate imported geometry at expected positions.

## Provenance and limits
KiCad10.0.6 actual exports from existing MIT Pico2ROMEmu board: native input SHA256
`1cbb2ca471872f6ba26830456b17ba00cf9eb9128c60d6161c038e602da88ac9` unchanged.
SVG28830bytes, SHA256`1c0ed05462cb5b9157bba6285a16f4c94909bcaf2c8c93dd7f2ac52e69d05aec`,
is KiCad via PCBNEW root desc. DXF872254bytes,
SHA256`e9aee26f92577f13cee6149e15563bb3993098bea892d0a00f310ce20713f157`, is correctly Unknown;
its KiCad font names do not qualify. Exact CLI argv, version, MIT notice and source/output hashes
are retained in tests/reference/cad-source/kicad-pico2romemu/, all byte-stable via .gitattributes.
Existing Inkscape1.1.1 application asset verifies metadata syntax, not PCB CAM compatibility.
Illustrator and Proteus use authored producer fixtures; genuine licensed vendor-output coverage
remains open. Source metadata is a claim, not proof of authorship or manufacturing readiness.
Fixed SVG1.1 external DTD inspection is offline; existing geometry import still rejects DTDs.
Thus real KiCad SVG verifies source inspection, not new physical import compatibility.

## Delivery
Runtime commit: `2fac34880ce96d9a5187d1d020552f58b99dfa5c`.
Final reviewed head: `38822cb4e8d360cd4a25654fdd37889d3c8d1c6f`.
[PR 21](https://github.com/ozkurkuran/MikroCAM/pull/21) merged as
`5406a0e3148ca059456f6b107f2affc3d9402f0c` after final-head
[Windows CI](https://github.com/ozkurkuran/MikroCAM/actions/runs/36295494584)
passed in 6m37s. Delivery documentation changes no runtime.

## Genuine vendor-export follow-up (2026-10-04)
Branch `test/vendor-svg-fixtures`. Three unmodified third-party exports were added under
`tests/reference/cad-source/`, each with its original license notice, provenance.json, SHA-256
and Git blob hash, kept byte-stable by the existing `.gitattributes` rule. They supersede the
"authored only" statement above for SVG; tests are in `tests/test_vendor_export_fixtures.py`.

| Fixture | Producer evidence | License / source | Result |
| --- | --- | --- | --- |
| `proteus-breath-analyzer/B_A_.svg` (129249 B) | root desc `Created by Proteus Design Suite` | Apache-2.0, [TengoCharlie/breath-analyzer@5872bbe2](https://github.com/TengoCharlie/breath-analyzer/blob/5872bbe211318a74ec51ccff3bf4ef2fc1d371b7/pcb%20bt%20woled/B_A_.svg) | Proteus, identified (after fix) |
| `illustrator-wortschule-hilfsverb/hilfsverb.svg` (53005 B) | generator comment + XMP CreatorTool `Adobe Illustrator 25.3 (Windows)` | MIT, [wort-schule/wort.schule@eea2cf5d](https://github.com/wort-schule/wort.schule/blob/eea2cf5d856bff46ebc96b1dd472e869a604c31e/app/assets/images/montessori/hilfsverb.svg) | Illustrator, identified |
| `illustrator-commons-history-of-china/…svg` (35021 B) | generator comment `Adobe Illustrator 24.1.0` | Public domain (PD-self), [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:%22History_of_China%22_for_template_heading.svg) | Illustrator, identified |

Bug found and fixed (test first): every genuine Proteus SVG export found declares itself only as
`<desc>Created by Proteus Design Suite</desc>`, which the authored marker grammar did not admit,
so real Proteus output was Unknown. Root desc now also admits an anchored `Created by` only when it
names a supported application (authorship text such as `Created by Jane Doe` is neither a claim
nor a new conflict); comments and DXF 999 keep the original grammar; Proteus accepts the optional
`Design Suite` suffix. The stored-claim validator applies the same rule. Fix commit `892f0952`.

Corpus probe (scratch only, not retained): of 731 Wikimedia Commons SVGs carrying an Illustrator
marker (PD/CC0/CC-BY categories), 583 were identified as Illustrator, 74 conflicting (Inkscape
version from a later re-save, correctly Unknown), 72 unavailable (internal-subset entity DTDs or
non-UTF-8 declarations, correctly not guessed) and 2 unknown. All 35 permissively licensed Proteus
SVGs found on GitHub carry the same desc marker and are now identified.

Search record and rejections: GitHub code search `"Created by Proteus Design Suite"` (231 hits,
106 repositories; only 20 MIT/Apache-2.0/CC-BY-4.0 repositories, 35 files, one PCB layout; GPL,
AGPL, LGPL, WTFPL, unlicensed and copied Proteus installation `DATA` files were rejected).
`Labcenter`/`PROTEUS`/`Proteus Design Suite` with `extension:dxf` found no Proteus DXF; the
breath-analyzer `B_A_.dxf` has no marker and its neighbouring `DXFINFO.LOG` reads like an import
log, so its producer cannot be established and it was not retained. Illustrator DXF search
(`"Adobe Illustrator" extension:dxf`, `"Adobe Illustrator Linetype"`, `"AI-LINETYPE"`; 60 hits,
13 repositories) left two permissive candidates: MakerWear/MakerWear (no license when the file was
committed; current terms "MIT for Software, CC 4.0 for Hardware" name no CC 4.0 variant) and
AleBiCi/PPSE_2024 (MIT repository, but the drawing accompanies a third-party RND enclosure
datasheet). Both were rejected. Such DXFs carry only `Adobe Illustrator Linetype No. N` LTYPE
descriptions, which this contract deliberately treats as table values, so they would stay Unknown.

Still open: genuine Illustrator DXF and genuine Proteus DXF detection evidence (none with an
acceptable license found); geometry import of genuine Proteus SVG (see 018 follow-up).

Local checks at test head `51b65b3d` (CPython 3.13.13, `.venv/repro-a`): new fixture file 18 passed;
`tests/architecture` 83 passed; `pip check` clean. Full suite: 5856 passed, 3 skipped, 310 subtests,
12 failed only because the optional `resvg_py` (requirements-visual) is absent from that venv; the
same 12 fail identically on unmodified origin/main `70800e5b` there, and those five visual test files
pass (46) with the main `.venv`. Logs: `.venv/vendor-fixtures-*.log` (ignored). PR Windows CI is the
delivery gate.
