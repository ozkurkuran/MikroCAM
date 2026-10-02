# Validation

check-status: PASS / WAITING.

SVG/PDF/Gerber source desteği ve native CAM PASS. B01/B10binary notice/packaging kabulünün alt kanıtı WAITING; source desteğini binary release diye raporlama.

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
| Binary installer/release audit | WAITING / NOT_RUN |75 exact source crate notices retained; wheel build provenance/final bundle still unproven |
| Local checkpoint / remote delivery | PASS / NOT_RUN |Local checkpoint; commit recorded centrally. Push/PR/CI/main remain NOT_RUN |
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
