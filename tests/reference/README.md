# Compatibility and PCB references

svg_paths.json captures the fixed input and expected geometry from the MIT 8.994 port's
tests/test_runtime_compatibility.py at baseline-8.994-py313 (6ba378bc). Coordinates and
areas use absolute tolerance 1e-9. These small regressions are not the later reference-dataset
feature's multi-CAD golden output collection. Source and adaptations: THIRD_PARTY_CHANGES.md.

## Authentic board corpus

`boards/manifest.json` admits ten distinct board designs, retaining 60 original files
(3,612,881 bytes). These are data fixtures, not new runtime dependencies or imported
application code. Files and selected archive members are unchanged; original archives,
source notices and available editable projects are retained. The manifest binds source
revision/path, origin evidence, role and byte hashes. `.gitattributes` preserves these bytes.

| Board | Origin | Original terms |
| --- | --- | --- |
| GYW workshop export | Eagle | MIT |
| LimeSDR-QPCIe v1.2 | Altium | CC-BY-3.0 |
| FD1 keyboard | DipTrace | BSD-3-Clause |
| FD1 mainboard | DipTrace | BSD-3-Clause |
| FD1 panel | DipTrace | BSD-3-Clause |
| Analog gyro | Fritzing | MIT |
| Sliding Gate | Proteus | CERN-OHL-W-2.0 |
| STM32F103 minimal system | EasyEDA | MIT |
| Pico2ROMEmu | KiCad | MIT |
| I-V curve multiplexer | KiCad | MIT |

Per-board notices apply to the source data and derived captures where applicable; MikroCAM's
MIT source license does not replace them. The Fritzing fixture includes upstream manual
Gerber fixes, described in its retained README; MikroCAM does not rewrite that export.
The Proteus drill-map layers are Gerber artwork, not Excellon holes. Missing optional drill
or outline layers are not invented. Four Gerbonara candidates without specific redistribution
evidence and Chibi's version-unspecified CC BY-SA notice were excluded.

## Capture and comparison

The frozen sources are `baseline-8.994-py313` at
`6ba378bca139aa306f8c94f09461a98f95d3c75b` in the separate reference repository and
`upstream-evo-baseline` at `d0a86cf4f1ac41a206b20f316d4a29f28a93bbff` in this repository.
The latter is the preserved initial Evo fork; the running MikroCAM source uses the later
user-selected Beta_1.0. Their differences are evidence, never silently updated expectations.

Use a clean standard CPython 3.13 x64 environment with `requirements-dev.txt` and
`requirements-image.txt` to recapture both old sources: 8.994 imports Rasterio eagerly.
Offline codec/comparison tests need only the existing core/development environment.
Both engines and the candidate must use the same interpreter/dependency versions and
capture helper bytes for a controlled comparison. No desktop or manufacturing hardware is used.
Git attributes preserve those helper bytes across checkouts, including the Qt settings sandbox;
changing the harness is a reviewed recapture change rather than an implicit golden update.

From the repository root, run the explicit commands in
[`specs/009-reference-dataset/quickstart.md`](../../specs/009-reference-dataset/quickstart.md).
Every capture requires clean declared source and a fresh output directory. Baseline labels
enforce exact revisions; current capture requires its full explicit revision. Input, source,
configuration and runtime evidence are recorded in schema-1 compressed JSON. Actual exceptions
or timeouts are retained per stage; capture completeness does not mean every CAM stage succeeded.

Comparison requires an explicit baseline, distance in mm and area in mm². It checks topology,
GEOS discrete vertex Hausdorff distance, symmetric-difference area, ordered CNC paths and
drill/slot multiplicity. A narrow default-preprocessor word comparison also detects emitted
Z/feed/spindle/dwell/mode/tool changes. Comments and numeric spelling do not count; X/Y words
use distance tolerance and other numeric words are exact. It does not interpret modal state.

Exit 0 means all comparable stages match, 1 means measured differences with no unavailable
stage, and 2 means invalid or indeterminate evidence. Repeated baseline failures remain
indeterminate. Reports are written exclusively outside input directories; there is no
automatic golden-update option. See the feature validation record for actual captured
outcomes and observed differences; these developer comparisons do not run the G-code.

## Authored SVG document reference

`svg-physical-transform.svg` is an original MikroCAM MIT fixture, separate from the frozen capture
harness and PCB corpus. SHA256: `d51453ef6998bd33a67c7a2c92b4fec1f01d2e88920855e728235fb5e56d5fb3`;
Git preserves its exact bytes. Independent local bounds (20,20)-(60,40), viewport 100x50 mm and
viewBox 200x100 imply physical bounds (10,10)-(30,20) mm, area 200 mm²; flip gives (10,30)-(30,40).
`test_svg_reference.py` also exercises the unchanged path fixtures through the new bridge. The old
helper inferred parity holes; the new importer requires explicit evenodd or nonzero winding.
Both behaviors are characterized without changing those original expectations or golden data.

## Genuine vendor SVG exports

`cad-source/` also retains three unmodified third-party SVG exports, retrieved 2026-10-04, as data
fixtures only (no runtime dependency, no code). Each folder keeps the original license or license
statement and a `provenance.json` with exact source URL/revision, author, SHA-256 and Git blob hash;
`.gitattributes` keeps their bytes, including CRLF and mixed line endings.

| Folder | Producer | Terms | Source |
| --- | --- | --- | --- |
| `proteus-breath-analyzer` | Proteus Design Suite PCB SVG | Apache-2.0 | TengoCharlie/breath-analyzer `5872bbe2` |
| `illustrator-wortschule-hilfsverb` | Adobe Illustrator 25.3 with XMP | MIT, (c) 2022 Stefan Wintermeyer | wort-schule/wort.schule `eea2cf5d` |
| `illustrator-commons-history-of-china` | Adobe Illustrator 24.1 | Public domain (PD-self), Lá»‡ XuÃ¢n | Wikimedia Commons |

Only the Commons file name was changed, to remove Windows-invalid quotes. Search scope, rejected
candidates and the remaining gaps are recorded in the 018, 019 and 020 validation files.
