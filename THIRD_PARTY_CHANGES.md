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

- Source: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commit `cec6a094ddc520e129d29ec8855a637ca5296a24`
  (drilling ToolDB overwrite fix). Existing FlatCAM Evo copyright headers are retained.
- Destination: `appPlugins/ToolDrilling.py`, `replace_tools()` only.
- Adaptation: copy accepted replacement settings into the source Excellon object before
  the real default-order UI rebuild reloads its tools. Database records remain independent.
- Regression: exact and tolerance matches survive two rebuilds and reach the actual Qt form.
- MikroCAM commit: `e4224b68` (`fix: persist drilling database replacements`).

## 2026-09-27 — Preserve distinct Excellon milling tools

- Source: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commit
  `6e13950a6b1568539c1b7b1eba459086cdc5ab05` (Excellon drill duplication).
- Destination: `appPlugins/ToolMilling.py`, `build_ui_exc()` only; inherited notices retained.
- Adaptation: sort full-precision tool records once for requested ascending/descending order;
  preserve source order otherwise. Reset displayed totals at each rebuild.
- Regression: equal displayed diameters retain two distinct tools and two drill hits through
  repeated real Qt table rebuilds in all three order modes.
- MikroCAM commit: `4aac5778` (`fix: preserve distinct Excellon milling tools`).

## 2026-09-27 — Preserve milling dwell through level changes

- Source: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commit
  `97ea33b1d84a2e39b9c35880a28e001d227ac2d0` (dwell parameter left behind).
- Destination: `appPlugins/ToolMilling.py`, `on_level_changed()`; inherited notices retained.
- Adaptation: remove Beginner/Advanced assignments that replace the selected tool's dwell
  toggle with application/object defaults. The stored duration and toggle remain paired.
- Regression: real `CNCjob.generate_from_geometry_2()` and default preprocessor retain
  `G4 P4.2` across both directions of repeated level changes.
- MikroCAM commit: `e8ac6db5` (`fix: preserve milling dwell through level changes`).

## 2026-09-27 — Restore cutout and gap controls independently

- Source: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commit
  `97ea33b1d84a2e39b9c35880a28e001d227ac2d0` (cutout UI restoration).
- Destination: `appPlugins/ToolCutOut.py`, `update_ui()`; inherited notices retained.
- Adaptation: use the cutout mode radio value for automatic/manual controls and explicitly
  restore gap-specific controls from the gap combo value, including while signals are blocked.
- Regression: actual Qt controls retain automatic/manual and Thin/Mouse Bites states separately.
- MikroCAM commit: `3c15f77c` (`fix: restore cutout and gap controls independently`).

## 2026-09-27 — Preserve explicit cutout database machining settings

- Audit reference: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commit
  `f239fcbb8f34b300516f6a97ad50e6798924b07d` (Phase 5 canonical database backfill).
  This commit retains the milling-to-cutout overwrites upstream; the correction below is
  independently implemented in MikroCAM, not ported from that source.
- Destination: `appPlugins/ToolCutOut.py`, database matching and picker callback; notices retained.
- Correction: remove six post-copy assignments that replace dedicated cutout Z, multidepth and
  pass depth with milling values. Dedicated cutout settings remain authoritative in both routes.
- Regression: exact, tolerance and picker insertion retain intentionally distinct machining
  values in stored data and actual Qt controls; original records/files remain unchanged.
- MikroCAM commit: `d2d2b71b` (`fix: preserve explicit cutout database settings`).

## 2026-09-27 — Populate canonical machining database defaults

- Source: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commit
  `f239fcbb8f34b300516f6a97ad50e6798924b07d` (Phase 5 ToolDB defaults).
- Destination: `defaults.py` and `appDatabase.py`; existing notices and MIT permission retained.
- Adaptation: retain the six machining namespaces and twelve application-only exclusions;
  use their canonical factory keys for new records and existing normalization backfill.
  Current application values are copied for creation; explicit loaded values remain unchanged.
  Keep existing numeric conversion, segmentation metadata and strict database validation.
- Regression: new in-memory records include the milling/drilling laser settings and every
  eligible machining setting before save/reload; backfill excludes unrelated UI namespaces.
- MikroCAM commit: `eb91977c55278dcde7d0ce1328a151ab9a05cb86` (`fix: populate canonical machining database defaults`).

## 2026-09-27 — Keep each queued drilling job's output independent

- Source: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commit
  `6e13950a6b1568539c1b7b1eba459086cdc5ab05`; existing notices retained.
- Destination: `appPlugins/ToolDrilling.py`, multi-tool CNC job assembly.
- Adaptation: replace shared plugin output accumulators with initializer-local values.
  Resetting only when the button is clicked does not isolate jobs already queued together;
  local ownership also prevents a later job from mutating an earlier parsed-path list.
- Regression: actual job initializer and two-tool assembly run twice, both sequentially and
  with both requests queued before workers start; a deterministic CAM boundary isolates
  assembly behavior. Output and parsed records remain equal and independently owned.
- MikroCAM commit: `0b4a46e996d69b950f2c3b193d60863481d71ddd` (`fix: isolate output of queued drilling jobs`).

## 2026-09-27 — Safe plot workers and object deletion

- Source: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commits
  `d6cb96d4d8a0318f3f0376ebf6f6991924c2708d` and
  `8df6abc0ce4dad0ad338aca5dd5e90b480b68c87`; inherited notices retained.
- Destination: `appObjects/AppObjectTemplate.py`, `GerberObject.py`, `ExcellonObject.py`.
- Adaptation: mark deletion before releasing widgets, disconnect safely and defer Qt widget
  destruction; repeated deletion is harmless. Keep plain options alive for in-flight workers.
  Plot workers read a snapshot of stored options instead of touching Qt widgets, preserve
  explicit visible=False, and stop when deletion occurs during setup. The GUI Follow handler
  updates stored state before plotting. No upstream appMain restructuring is imported.
- Regression: gated queued plots after deletion, real background-thread plotting with forbidden
  widget access, deletion during setup, actual deferred Qt destruction, repeated deletion and
  the real Follow checkbox path. Nine tests pass after reproducing the failures first.
- MikroCAM commit: `4a28365f8581867c05e4eb70893c95343b2c68e8` (`fix: keep plot workers independent of widget lifetime`).

## 2026-09-27 — Preserve selected milling machining flags

- Source: Krisnop Saimuey, `kpkrisnop/flatcam`, MIT commit
  `97ea33b1d84a2e39b9c35880a28e001d227ac2d0` (remaining level-change flag corrections).
- Destination: `appPlugins/ToolMilling.py`, `on_level_changed()`; inherited notices retained.
- Adaptation: remove Beginner/Advanced writes that reset the selected tool's extra-cut and
  exclusion-area flags. Preserve the stored extra-cut length. Upstream diagnostic prints
  are not imported; offset type/value and job-type writes are outside this correction.
- Regression: real level changes retain explicit true flags through both transition orders.
- MikroCAM commit: `1b6fdfe7149f481c0a62d0e44306d602d722bc35` (`fix: preserve selected milling machining flags`).

## 2026-09-27 — Keep milling level changes read-only for machining settings

- Independent MikroCAM finding during the audit of MIT upstream
  `kpkrisnop/flatcam` commit `97ea33b1d84a2e39b9c35880a28e001d227ac2d0`.
  That upstream commit retains the offset/job overwrites; this correction is not a port.
- Destination: `appPlugins/ToolMilling.py`, `on_level_changed()`; existing notices retained.
- Correction: remove writes replacing per-tool offset type/value and job type. Entering
  Advanced restores the one selected tool's actual choices with scoped Qt signal blockers,
  then refreshes job/custom-offset visibility explicitly. Basic keeps advanced controls hidden.
  Multiple-tool machining data is preserved; existing signal-blocked states remain unchanged.
- Regression: real Qt combo signals connected to actual `form_to_storage()` demonstrate
  no writes during either level sequence, unchanged selected/other tools, visible custom
  offset 0.42 and Isolation job, and functioning ordinary editing after restoration.
- MikroCAM commit: `06eac8e62b5c7ad566e4d4cbd4dcbc8cc45c0dfa` (`fix: keep milling level changes read-only`).

## 2026-09-27 — Discard render submissions that finish after deletion

- Follow-up to the MIT `kpkrisnop/flatcam` lifetime audit above; this race correction is
  independently implemented, not copied from an upstream change.
- Destination: `appObjects/AppObjectTemplate.py` and `appObjects/ObjectCollection.py`.
- Finding: clearing before setting deleted leaves a submission window; an add already inside
  the shape collection can also complete after removal. Mark deletion before collection clear,
  then discard late single/batch/mark submissions after their concrete add returns.
- Regression: five tests first failed, then passed: blocked background submissions finish after
  removal without leaving orphan shapes, and both collection removal routes set the guard first.
- MikroCAM commit: `0adafe98ba330e0b453c00ddc5210435c4a05000` (`fix: discard shapes submitted during object removal`).

## 2026-09-27 — Review Proteus-style SVG circular drill evidence

- Source: Yacupoma Aguirre Luis Enrique, ProgLuis/FlatCAM9NeoS2, MIT; immutable inspected
  head `914630319725b0d6034801f4808ae345d53b407b`, extraction commit
  `fd9e365ac3c41e713fc329a608e4cafbb8667caa`, style follow-up
  `181c1f2a28d9a03675c4ee42bec234494bfe63e1`.
- Source files/functions: `appParsers/ParseSVG.py` (`svgextract_circular_paths`,
  `extract_proteus_svg_drills`) and `app_Main.py` (`import_svg_drills`).
- License: upstream MIT notice retained in `THIRD_PARTY_LICENSES/FlatCAM9NeoS2-MIT.txt`.
- Adaptation: independently implement the white-opening/concentric-pad convention with exact
  physical transforms, actual circle evidence, bounded work, conflict exclusion, stable tool
  grouping and explicit review/selection. No module copy or automatic drill-object creation.
- Regression: analytic circle/arc/affine/unit/color/ambiguity/selection tests, Excellon roundtrip
  and actual desktop review. Original fixture `tests/reference/svg-drills.svg` is MikroCAM MIT
  artwork, not a genuine Proteus export. Vendor-export validation remains open.
- MikroCAM commit: recorded after implementation in `specs/018-svg-drill-detection/validation.md`.

## 2026-09-27 — Preserve Illustrator-style SVG page, compound fill and clipping evidence

- Source behavior: Yacupoma Aguirre Luis Enrique, `ProgLuis/FlatCAM9NeoS2`, MIT; inspected
  immutable head `914630319725b0d6034801f4808ae345d53b407b`, relevant commits
  `9b73859dea7705b1c7ccaac614d2d05de1e05ca4`,
  `c1e01850fac318126338cc27ba995100dd86ef46`,
  `181c1f2a28d9a03675c4ee42bec234494bfe63e1`.
- Source file/functions: `appParsers/ParseSVG.py`, `svg_read_xmp_max_page_size`,
  `svg_physical_scale`, `svg_source_advisor`, `svg_node_is_visible`,
  `svgcompound_fillrule2shapely`; no source module copied or repositories merged.
- License: existing upstream MIT notice retained in `THIRD_PARTY_LICENSES/FlatCAM9NeoS2-MIT.txt`.
- Independent adaptation: use exact Adobe XMP namespaces only beneath root SVG metadata;
  retain explicit axis dimensions and raw tokens, offline simple CSS cascade/visible layer facts,
  bounded compound winding and local physical clipping. Follow SVG clip-frame semantics instead
  of guessing scale averages or repairing invalid material. Metadata/foreign styles are inert;
  clip silhouettes ignore paint while visible material validates its winning appearance.
- Destination: `mikrocam/importers/svg_metadata.py`, `svg_css.py`, `svg_document.py`, `svg_style.py`;
  `mikrocam/core/svg_models.py`, `svg_fill.py`, `svg_paint.py`, `svg_clip.py`, `import_report.py`,
  `import_report_codec.py`, `svg_drill_circles.py`; `mikrocam/bridge/svg_import.py`.
- Format: report schema 2 preserves percentage source tokens; strict schema 1 records migrate
  without changing persisted field names or the surrounding project format.
- Evidence scope: authored analytic fixtures and existing reference comparisons. The inspected
  source's named Illustrator examples were not shipped; no genuine licensed vendor-export sample
  or physical manufacturing validation is claimed. Validation results and the implementation commit
  are recorded in `specs/019-svg-illustrator/validation.md` when delivery checks complete.

## 2026-09-27 — Report explicit CAD producer evidence

- Behavior sources: MIT `ProgLuis/FlatCAM9NeoS2`, inspected head
  `914630319725b0d6034801f4808ae345d53b407b`; `appParsers/DXFSourceDetector.py` at
  `7b3ea49f96174a38dd079fba7574982b6ec6f1c4` and `appParsers/ParseSVG.py` source-advisor behavior
  at `9b73859dea7705b1c7ccaac614d2d05de1e05ca4`. Existing full MIT notice is retained in
  `THIRD_PARTY_LICENSES/FlatCAM9NeoS2-MIT.txt`.
- Independent adaptation: bounded producer metadata only, with explicit missing/conflicting/
  unavailable states. No filename, font, layer or geometric-profile scoring; no module copy or merge.
  Source evidence is a historical claim, never proof of authorship or manufacturing readiness.
- Destination: `mikrocam/core/cad_source.py`, `cad_source_codec.py`; `mikrocam/importers/cad_source.py`,
  `cad_producer.py`, `cad_svg_source.py`, `cad_dxf_source.py`; `mikrocam/bridge/cad_source.py` and
  `mikrocam/ui/cad_source.py`, with short existing import/persistence hooks.
- Fixture provenance: KiCad10.0.6 CLI exports from the existing MIT Pico2ROMEmu board,
  copyright2025 kyo-ta04(@DragonBallEZ), upstream `de3a29370d760e93451975094372e08484cd6777`.
  Exact source/output hashes, commands and full MIT license accompany
  `tests/reference/cad-source/kicad-pico2romemu/`. Output-format documentation was researched;
  no KiCad GPL implementation code was ported. The existing upstream Inkscape SVG asset is reused
  without copying or claiming PCB coverage. Illustrator/Proteus markers use authored syntax fixtures.
- MikroCAM implementation commit and complete validation are recorded in
  `specs/020-cad-source-detector/validation.md` after delivery checks.


## 2026-10-01 — Evo ToolLevelling GRBL düzeltmeleri

- Source repository: https://bitbucket.org/marius_stanciu/flatcam_beta
- Source branch/commit: `Beta_1.0`, `e046a2a33926003765f83d6402b96fe6c5c3bcf7`.
- License: MIT; original copyright notices retained.
- Files: `appPlugins/ToolLevelling.py`, `tests/test_levelling_grbl_wire.py`.
- Reason: correct the legacy GRBL wire bugs recorded in MACHINE_CONTROL_ROADMAP phase A.
- Changes: require a real greeting or wake ACK, decode bytes safely, lock response types,
  validate numeric jog inputs, use G10 L20 without $10 writes, and send supported realtime
  commands as single bytes before waiting for the reset greeting.
- These fixes and mock-only regression tests were independently implemented; no external
  fork implementation was copied. No physical device was connected or validated.
- MikroCAM commits: `83cf6e9f` (A1), `26eb6e53` (A2), `207107a4` (A3),
  `1dd63f00` (A4), and the A5 commit containing this entry
  (`git log --format=%H --grep="fix: send legacy GRBL realtime commands as bytes" -1`).
- Verification: A1, A3, A4 and A5 regressions failed before their fixes; A2 lock tests
  passed against existing code. All 47 wire tests pass after fixes. Full-suite and
  Windows CI results are recorded in the phase A pull request.


## 2026-10-01 — Evo Levelling GRBL single-owner handoff

- Source repository: https://bitbucket.org/marius_stanciu/flatcam_beta
- Source branch/commit: Beta_1.0, `e046a2a33926003765f83d6402b96fe6c5c3bcf7`; MIT notices retained.
- File: appPlugins/ToolLevelling.py; independently implemented UI helper/tests/docs.
- Reason: prevent legacy port scanning/connection and GRBL callbacks from bypassing Machine.
- Changes: metadata-only port listing, blocked public connection, GRBL callback guards,
  hidden/disabled serial frame and explicit reuse of Machine. Legacy implementations retained;
  offline MACH3/MACH4/LinuxCNC behavior preserved. No outside fork source copied.
- MikroCAM commit: the implementation commit named `feat: route GRBL Levelling to Machine`.
- Verification: 21 acceptance cases; related 153 tests and 41 subtests pass after the
  documented smoke race correction. Final original head 730d4bde Windows CI passed:
  https://github.com/ozkurkuran/MikroCAM/actions/runs/36929106301.
  Current integration validation is recorded separately in docs/IS_TAKIP.md.
- No physical device was connected or validated.


## 2026-10-02 — GRBL delivery review corrections and visual identity

- Source/license: the same MIT ToolLevelling provenance recorded above; original author notices retained.
- Public GRBL callbacks are rejected for all controller selections; retained implementations
  are accessed only explicitly by mock tests. The hidden legacy report callback uses one realtime byte.
- Character-counting completion commits its phase after the final output-off handoff, so
  a priority hold before that handoff can resume and finish the same job.
- Operator-only inventory validates bounded complete records with the existing GRBL parsers
  and records TX attempts separately from successful complete writes. No physical port was used.
- Before-fix review group: 52 failed / 48 passed; final related/architecture group: 412 passed,
  41 subtests. Full, desktop and final commit Windows checks are tracked centrally.
- MikroCAM visual assets are independently generated from local Shapely/Pillow geometry.
  The replaced upstream Inkscape SVG is retained unchanged as a metadata test fixture at
  tests/reference/cad-source/upstream-inkscape-app-small.svg under the existing source license.
- Protocol facts: https://github.com/gnea/grbl/wiki/Grbl-v1.1-Interface ; no firmware code copied.


## 2026-10-02 — KiCad production transfer (030)
Original MikroCAM implementation; no KiCad source copied. External installed KiCad10.0 CLI performs DRC/Gerber/Excellon on a private snapshot. Primary behavioral references: https://docs.kicad.org/10.0/en/cli/cli.html ; https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/ . Files: mikrocam/core/kicad_transfer.py, mikrocam/kicad/, mikrocam/bridge/kicad_transfer.py, mikrocam/ui/kicad_transfer.py and short appMain hooks. No new CAM runtime dependency. Commit:0830a9e4 (CLI/package), ad2f396d and450d8e5d (review hardening).


## 2026-10-02 — KiCad IPC Bridge (031)
Original standalone MikroCAM action/installer. No source copied from KiCad or other plugins. Optional official kicad-python0.8.0 (MIT) installed only in KiCad’s separate environment; full compatible transitive tree pinned in integrations/kicad/requirements.txt and original dependency license texts retained under THIRD_PARTY_LICENSES/optional-kicad. Reference package https://pypi.org/project/kicad-python/0.8.0/ and https://gitlab.com/kicad/code/kicad-python ; official10 plugin schema and IPC developer docs consulted for protocol/metadata. SDK implementation was inspected to confirm SaveCopyOfDocument and version0.8 method availability; no SDK implementation ported. Files: integrations/kicad/, mikrocam/kicad/install_plugin.py. Commit:f93111dc (IPC/installer); delivery merge90926e0b.

## 2026-10-02 — Visual SVG renderer source notices (032–033)

Optional resvg_py 0.5.0 remains pinned; no additional runtime dependency or upstream
implementation was copied. Its exact PyPI sdist SHA256
6d3bf8e866b4e129524d9432a809138b2d100931d8d635bc81294002abcdfd46 supplies the retained
unmodified Cargo.lock/Cargo.toml/pyproject.toml/LICENSE provenance. The lock covers
75 registry crates; every primary static.crates.io archive matches its checksum.
152 original license/notice files are retained byte-for-byte with source URL/hash
and original license expression in THIRD_PARTY_LICENSES/inventory.json. No upstream
commit was inferred from version alone. Wheel build provenance and final bundle
composition remain unproven. See docs/design/visual-interlace/notice-audit.md.
Original MikroCAM code, tests and synthetic discovery images; implementation is
preserved in a local checkpoint on branch 032-visual-interlace; commit recorded in central IS_TAKIP. Not delivered to main.
