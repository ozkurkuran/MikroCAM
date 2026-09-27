# Validation: CAD source evidence

Status: implementation and focused validation complete; full suite, actual desktop and CI pending.
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
Pending final runtime head. Commands: `python -m pytest -q --junitxml=.venv/cad-source-pytest.xml`
and `python tests/smoke_app.py`. Ignored logs/screenshots under `.venv/`.

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
Implementation commit, PR, final-head Windows CI and merge pending.
