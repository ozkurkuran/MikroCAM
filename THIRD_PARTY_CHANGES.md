# Third-party changes

## 2026-09-26 — FlatCAM Evo Beta_1.0 baseline

- Source repository: https://bitbucket.org/marius_stanciu/flatcam_beta
- Source branch and commit: `Beta_1.0`, `e046a2a33926003765f83d6402b96fe6c5c3bcf7`.
- Previous fork baseline: `mekatrol/flatcam` at `d0a86cf4f1ac41a206b20f316d4a29f28a93bbff`.
- License: MIT, as recorded in the upstream `LICENSE`; copyright notices retained.
- Reason: user-selected current Evo baseline for the Python 3.13 compatibility slice.
- Files: the 208 upstream changed paths between these commits; exact inventory is available
  with `git diff --name-status upstream-evo-baseline upstream-evo-beta1-baseline`.
- Changes made during import: none; a fast-forward retained all 61 upstream commits unchanged.
- MikroCAM commit: `e046a2a33926003765f83d6402b96fe6c5c3bcf7` (same commit after fast-forward).
- Verification: baseline tags point to the original commits; source branch and selected tag
  match. Runtime verification remains part of `001-evo-py313-baseline`.

Later documentation changes import MikroCAM's own Spec Kit files and replace the root
contributor guide. The upstream guide remains available at `upstream-evo-beta1-baseline:CLAUDE.md`.

## 2026-09-26 — Python 3.13 reference behavior adaptations

- Source repository: https://github.com/ozkurkuran/flatcam-8.994-py313
- Source tag/commit: `baseline-8.994-py313`, `6ba378bca139aa306f8c94f09461a98f95d3c75b`.
- License: MIT for the FlatCAM reference repository; existing module copyright notices retained.
  The vendored Descartes adapter has a separate BSD origin and is not relicensed by that
  repository's root MIT terms; its source/downstream license evidence is recorded in NOTICE.md.
- Source files: tests/test_runtime_compatibility.py, tests/smoke_app.py,
  appParsers/ParseSVG.py, descartes/patch.py.
- Destination files: tests/test_runtime_compatibility.py, tests/smoke_app.py,
  tests/reference/svg_paths.json, appParsers/ParseSVG.py, descartes/patch.py.
- Reason: preserve the eight proven compatibility behaviors and end-to-end CAM journey
  on Evo's different object/lifecycle APIs.
- Adaptations: use Evo Geometry.flatten instead of importing the legacy multipart helper;
  obj_options/kind and parsed CNC geometry assertions; asynchronous project reload and its
  settings dialog; isolated QSettings/IPC; real render and normal cleanup checks. SVG
  handling preserves open subpaths, holes and disconnected contours while keeping Evo's
  curve sampling. Polygon paths support Shapely 2, GeoJSON and empty geometry.
- MikroCAM commit: `d30cc6c8` (`fix: adapt legacy geometry and smoke regressions to Evo`).
- Additional independently implemented startup/lazy-import/pinning fixes: `1786e70f`.
  These are not ports from another fork. No kpkrisnop, neo, dwrobel or FlatCAM-Plus code
  was imported in this feature.
- Verification: see specs/001-evo-py313-baseline/validation.md for failing-before evidence,
  all upstream tests, complete legacy behavior mapping and three successful smoke cycles.

## 2026-09-26 — Exact-version license and attribution collection

- Reason: provide source-traceable notices for every pinned runtime/development/optional
  image dependency, preserving separate copyleft and vendored-component terms.
- Sources/versions: all 58 requirements pins from the verified Windows CPython 3.13
  environment; exact PyPI wheel URLs and published artifact hashes are recorded in
  `THIRD_PARTY_LICENSES/inventory.json`. Installed license bytes match their RECORD hashes.
- Files: `THIRD_PARTY_LICENSES/**`, `LICENSE`, `NOTICE.md` and the offline inventory tests.
  License texts and supplied bundled notices are copied without modification; JSON/README
  records identify their source members and SHA-256 digests.
- Missing wheel notices: PyOpenGL 3.1.10 and pyserial 3.5 main license texts come from their
  exact published source archives. Their archive URLs, hashes and member names are recorded.
- Source-vendored qdarktheme 1.1.1: preserve its MIT source license and original theme
  attribution; retain complete immutable upstream license snapshots for Google's Material
  design icons (Apache-2.0) and Colin Duquesnoy's QDarkStyleSheet code (MIT). Original
  resource commits are unrecorded and this collection does not claim otherwise.
- Source-vendored Descartes 1.1.0: exact archive metadata names Sean Gillies and declares BSD,
  but published archives/wheels lack full text. Full BSD-3-Clause notices are copied from
  explicitly identified downstream conda-forge/Debian records, not invented or attributed
  to the source archive. The preexisting Shapely 2 adapter changes remain documented above.
- Bundled imagetracer.js 1.2.5: copy the complete unchanged header from svgtrace 2023.0.1;
  preserve Andras Jankovics/FredHappyface attribution and its explicit Unlicense exception.
- This collection adds notice text, attribution evidence and metadata, not executable
  dependency modules, a new dependency, browser binary, artwork or native DLL. Existing MIT
  holders remain; MikroCAM contributors'
  2026 copyright is added for their work. Dependency/vendored terms remain separate.
- Distribution limitations: NOTICE and inventory retain inherited artwork credits and
  explicitly record incomplete per-file provenance, unrecorded resource revisions and the
  Rasterio native-DLL audit gap. This work does not assert a cleared installer/binary release.
- MikroCAM commit: `f983d153ebe4ea8091ccbc5650db053f131ac6ae` (exact-version notice collection).
- Product identity and update-boundary wiring are independently implemented in `bbd37168`;
  no runtime source from another fork was imported for this branding change.

## 2026-09-27 — Licensed PCB regression inputs (feature 009)

- Reason: preserve ten authentic, distinct PCB designs covering KiCad, EasyEDA, Altium,
  Eagle and Proteus, plus DipTrace and Fritzing, for independent parser/CAM reference captures.
- Destination: `tests/reference/boards/**`; the manifest records all 60 retained source
  files (3,612,881 bytes), original relative paths, archive members and SHA256 values.
  Original archives and notice files are retained; selected members are extracted verbatim.
- Source `jaseg/gerbonara` at `736107f7a4fa1f9858d4da93879ca00015893628`:
  `tests/resources/eagle-newer/` (GYW, MIT), `altium-composite-drill/` (LimeSDR-QPCIe v1.2,
  CC-BY-3.0), `diptrace/` (FD1 keyboard/mainboard/panel, BSD-3-Clause), `fritzing/`
  (analog gyro, MIT). Each original per-directory license and README attribution is retained.
  Gerbonara's root license is not used to infer rights for unidentified third-party fixtures.
  Its Fritzing README records prior manual Gerber corrections; those bytes remain unchanged here.
- Source `bothlab/maze-hardware` at `da73d2e3b6f5859b22398242fc484e0d9278aa5f`:
  Sliding Gate Proteus source/manufacturing archive, selected artwork, original license
  and documentation (CERN-OHL-W-2.0). PDS source is retained. Gerber drill maps are expressly
  classified as artwork; they are not relabelled Excellon drill data or synthesized outlines.
- Source `Kurisu-g/STM32F103-Minimal-System-PCB-` at
  `a70700ad2be9c5f96b5c2774294fa48912a5d35d`: EasyEDA source and manufacturing archive,
  top copper, PTH/NPTH and board outline, original MIT license and README.
- Source `kyo-ta04/Pico2ROMEmu_PCB` at `de3a29370d760e93451975094372e08484cd6777`:
  KiCad source and production archive, top copper, PTH/NPTH and edge cuts, original MIT
  license and README.
- Source `dusjagr/IVcurve_tester` at `f9a75be640c3651594d7e1b18a765c956d8d8d5c`:
  KiCad MUX-ADG706 source/production archive, top copper, PTH/NPTH and edge cuts, original
  MIT license and README.
- Adaptations: only destination organization and newly written provenance metadata; no
  edits to admitted source bytes. No executable source from these repositories is imported.
  Reference captures are generated independently by the two unchanged pinned engines,
  retaining the input designs' terms and attribution where applicable.
- MikroCAM data/codec commit: `1a407552` (`test: curate ten licensed PCB references with strict provenance codecs`).
  The capture harness (`a3f60b22`) and comparison logic (`7eaef7d0`, `a055271c`, `613948aa`)
  are independently implemented, not copied from those projects.

## 2026-09-27 — Persist drilling database replacements

- Source: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commit `cec6a094`
  (drilling ToolDB overwrite fix). Existing FlatCAM Evo copyright headers are retained.
- Destination: `appPlugins/ToolDrilling.py`, `replace_tools()` only.
- Adaptation: copy accepted replacement settings into the source Excellon object before
  the real default-order UI rebuild reloads its tools. Database records remain independent.
- Regression: exact and tolerance matches survive two rebuilds and reach the actual Qt form.
- MikroCAM commit: `fix: persist drilling database replacements` (this commit).

## 2026-09-27 — Preserve distinct Excellon milling tools

- Source: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commit
  `6e13950a6b1568539c1b7b1eba459086cdc5ab05` (Excellon drill duplication).
- Destination: `appPlugins/ToolMilling.py`, `build_ui_exc()` only; inherited notices retained.
- Adaptation: sort full-precision tool records once for requested ascending/descending order;
  preserve source order otherwise. Reset displayed totals at each rebuild.
- Regression: equal displayed diameters retain two distinct tools and two drill hits through
  repeated real Qt table rebuilds in all three order modes.
- MikroCAM commit: `fix: preserve distinct Excellon milling tools` (this commit).

## 2026-09-27 — Preserve milling dwell through level changes

- Source: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commit
  `97ea33b1d84a2e39b9c35880a28e001d227ac2d0` (dwell parameter left behind).
- Destination: `appPlugins/ToolMilling.py`, `on_level_changed()`; inherited notices retained.
- Adaptation: remove Beginner/Advanced assignments that replace the selected tool's dwell
  toggle with application/object defaults. The stored duration and toggle remain paired.
- Regression: real `CNCjob.generate_from_geometry_2()` and default preprocessor retain
  `G4 P4.2` across both directions of repeated level changes.
- MikroCAM commit: `fix: preserve milling dwell through level changes` (this commit).

## 2026-09-27 — Restore cutout and gap controls independently

- Source: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commit
  `97ea33b1d84a2e39b9c35880a28e001d227ac2d0` (cutout UI restoration).
- Destination: `appPlugins/ToolCutOut.py`, `update_ui()`; inherited notices retained.
- Adaptation: use the cutout mode radio value for automatic/manual controls and explicitly
  restore gap-specific controls from the gap combo value, including while signals are blocked.
- Regression: actual Qt controls retain automatic/manual and Thin/Mouse Bites states separately.
- MikroCAM commit: `fix: restore cutout and gap controls independently` (this commit).
