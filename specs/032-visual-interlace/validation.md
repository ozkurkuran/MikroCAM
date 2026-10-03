# Validation

check-status: PASS.

Yerel bitmap/interlace/preview/PNG/JSON/proje desteği;13task kapandı. Native LightBurn bu dilimin teslimi değildir.

Base: c5a666cfb090aa5671f335471c209c4809246726; branch032-visual-interlace; local checkpoint (commit recorded in central IS_TAKIP).
Tested source/notice checkpoint: `77899fec9b5b14b87485c5be6c34bc6e6f79af92eee28e7dc815c6e06468334e`.
Manifest: `.venv/visual-resume-source.json` (201 files SHA256). Runtime/config hashes are unchanged from the prior native API checkpoint; notice inventory and tests are included in this new full run.

| Kontrol | check-status | Kanıt |
| --- | --- | --- |
| Final fullregression + architecture/growth/notices | PASS |5746test,310subtest,3skip,11existingwarning,306.23s; `.venv/visual-resume-final-regression.log` and JUnit; exit0, source unchanged |
| UI/recipe API sonrası ilgili | PASS |27test/4.45s; public hints tamamlandı |
| Native realCAM3formats/project/render/shutdown | PASS |`.venv/visual-api-final-native.log`; source/project roundtrip ve normal shutdown markers; exit0 |
| Module600/function80/publictypehint check | PASS |AST scan; violations=[] |
| Reviewable demo | PASS |600×360,508DPI,N3; PNG mode1, logical union=master, nativeappliedFalse |
| Markdown local links/fences | PASS |Broken=[]; typed source mutation check=[] |
| LightBurn native Open/Save/Preview | WAITING / NOT_RUN |G02dependency; no real program/fixture/version/device supplied |
| Binary installer/release audit | WAITING / NOT_RUN |75 exact source-crate notices retained; wheel build provenance/final bundle audit still open |
| Source publication / delivery record | PASS |[PR#36](https://github.com/ozkurkuran/MikroCAM/pull/36) is open; its Checks and timeline record hosted CI and remote merge state. Local source commit d77a7cb1 is verified |
| Physical machine/laser | NOT_RUN |No COM/USB/emission; outside file-generation scope |

Detailed40acceptance mapping: [matrix](../../docs/design/visual-interlace/validation.md).
Use current source/proof; old5669 and eec55744 checkpoints are separate history.

## 2026-10-03 resume verification

The first resume run used the older repro-a interpreter and failed seven SVG-dependent
tests because resvg_py was absent (5739 passed/7 failed). That FAIL/JUnit is retained.
The actual worktree .venv passed pip check and all seven cases, then the complete
suite passed5746 tests/310subtests/3skips in306.23s. No product-code change or
test skip was used to remove the failures. The201-file checkpoint stayed unchanged.

Two historical vector-only .lbrn2 projects were discovered; they do not close G02.
Current executable/device and a real embedded Image fixture remain required.
Native LightBurn and binary-release acceptance remain WAITING/NOT_RUN.

## Source publication and local main

[PR#36](https://github.com/ozkurkuran/MikroCAM/pull/36) publishes source commit
d77a7cb1. The current PR head, hosted checks and merge result are recorded by
GitHub; previous NOT_RUN/local-only statements retain their checkpoint dates.
Local main separately passed192 visual tests/20.67s and a fresh native desktop
journey/47.94s with normal shutdown, using the SHA-verified resvg_py0.5.0 wheel.
No native LightBurn or binary-release acceptance changed.

## PR review validation — 2026-10-03

Code checkpoint c098a643 fixes IN-unit host-carrier creation and offline SVG font
inheritance, `!important`, TTC/OTC collections. Standard development requirements
include the pinned renderer, with matching license inventory groups.
New regressions first failed: 8 failed/1 passed; after fixes the related group
passed46 tests/82.09s and pip check passed. Fresh complete suite passed
**5755 tests,310subtests,3skips,11existing warnings,399.82s** (exit0), recorded in
`.venv/visual-review-full.log` and `.venv/visual-review-full.xml`.
Fresh real desktop smoke passed (exit0): actual MM and IN factory carriers,
embedded mm-grid/hash preservation, IN project save/reopen, bitmap/SVG/PDF,
PNG/JSON, legacy CAM, OpenGL and normal shutdown. Evidence:
`.venv/visual-review-native-final.log`, marker `VISUAL_MM_IN_CARRIER_EMBEDDED_MM_ROUNDTRIP_OK`.
The first native harness incorrectly changed options units without app_units;
its separate failure log is retained. The corrected harness changes both host
fields and restores them. The product fix did not change between those runs.
Documentation/notice-record newline cleanup changes no runtime or test behavior.
Latest exact-head hosted checks and source merge are authoritative in PR#36.
LightBurn native and binary-release acceptance remain open.
