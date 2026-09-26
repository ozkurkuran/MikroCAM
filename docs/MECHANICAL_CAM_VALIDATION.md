# Mechanical CAM correction validation

Validated on 27 September 2026 with Windows / CPython 3.13 x64, using the existing
`repro-a` environment and pinned dependencies. This delivery follows the merged
[reference dataset](../specs/009-reference-dataset/validation.md) and completes the
mechanical correction row in [ROADMAP.md](ROADMAP.md). It adds no machine transport,
hardware execution, dependency, updater or project-format change.

## Corrected behavior and introducing commits

| Correction | Introducing commit | Behavioral evidence |
| --- | --- | --- |
| Drilling ToolDB replacements persist in the source Excellon tools before UI rebuild | `e4224b68dcc773d69a7b4ef64123b6fa12649f45` | [Drilling replacement tests](../tests/test_mechanical_tool_regressions.py): exact/tolerance matches survive two actual rebuilds and reach the Qt form; geometry and database input remain intact. |
| Distinct Excellon milling tools are sorted by full diameter, never matched repeatedly by rounded display value | `4aac5778509f6f6d601de75baff759fb5bcc76da` | [Milling table tests](../tests/test_mechanical_milling_regressions.py): `.8001` and `.8002` retain two tools/hits in source, ascending and descending order through repeated rebuilds; totals reset. |
| Milling dwell survives Basic/Advanced changes | `e8ac6db5fb67e55825acf73de50ca19e41dab3b8` | [Level-change tests](../tests/test_mechanical_dwell_regressions.py): real CNC generation with the default preprocessor keeps `G4 P4.2`. |
| Automatic/manual cutout controls and gap-specific controls restore independently | `3c15f77cceb2c5c94554e21b86c36e73b5505a79` | [Cutout UI tests](../tests/test_cutout_ui_regressions.py): Thin/Mouse Bites with either cutout mode, including blocked combo signals. |
| Dedicated cutout Z, multidepth and pass depth survive DB insertion instead of being overwritten by milling settings | `d2d2b71bc071c2a23645cd0459918b56331b1220` | [Cutout DB tests](../tests/test_cutout_database_regressions.py): three distinct settings through exact, tolerance and picker routes; actual controls and unchanged input records/files. |
| New DB records and normalization use six supported machining namespaces and twelve application-only exclusions | `eb91977c55278dcde7d0ce1328a151ab9a05cb86` | [New/default DB tests](../tests/test_database_new_tool_defaults.py): laser settings and eligible keys exist before save/reload; backfill preserves explicit values and avoids unrelated UI namespaces. |
| Existing DB consumer fixture models the newly required persistent source tools | `85b1e2ccd47965e7c0f057289e679b54e40eecf3` | [Existing database suite](../tests/test_tools_database.py) retains its copy-isolation checks and adds a source-setting assertion. |
| Each queued multi-tool drilling initializer owns its G-code and parsed-path accumulators | `0b4a46e996d69b950f2c3b193d60863481d71ddd` | [Drilling assembly tests](../tests/test_drilling_job_accumulation.py): sequential requests and requests queued together cannot concatenate or share earlier output. These tests isolate real assembly with a deterministic CAM boundary. |
| Plot workers read stored options independently of Qt widget lifetime; deletion starts before releasing widgets | `4a28365f8581867c05e4eb70893c95343b2c68e8` | [Worker lifetime tests](../tests/test_plot_worker_lifetime.py): queued/background plots, forbidden worker widget access, deletion during setup, deferred destruction and the real Follow path. |
| Extra-cut and exclusion-area flags survive level changes | `1b6fdfe7149f481c0a62d0e44306d602d722bc35` | [Level-change tests](../tests/test_mechanical_dwell_regressions.py): both transition orders preserve explicit true flags and extra-cut length. |
| View level does not overwrite per-tool offset type/value or job type | `06eac8e62b5c7ad566e4d4cbd4dcbc8cc45c0dfa` | [Level-change tests](../tests/test_mechanical_dwell_regressions.py): selected `3 / 0.42 / 2` and another tool remain unchanged; Advanced restores selected controls without `form_to_storage` writes; ordinary editing still works. |
| Shape submissions already in progress cannot resurrect removed objects | `0adafe98ba330e0b453c00ddc5210435c4a05000` | [Submission lifetime tests](../tests/test_shape_submission_lifetime.py): blocked single/batch/mark submissions complete after removal without orphan shapes; both collection removal paths set the deletion guard first. |

Regressions reproduced the failures before their fixes. These are bounded adaptations of
the audited MIT `kpkrisnop/flatcam` changes, plus independently implemented corrections.
The dedicated cutout-settings, offset/job preservation and late-submission corrections
are explicitly distinguished from upstream ports in [THIRD_PARTY_CHANGES.md](../THIRD_PARTY_CHANGES.md).
Original FlatCAM/Evo notices remain; upstream diagnostic prints and broad appMain changes
were not imported.

## Final verification

The final local full-suite log, `.venv/mechanical-final-pytest.log`, records:

```text
1369 passed, 2 skipped, 11 warnings, 310 subtests passed in 165.72s (0:02:45)
```

The two skips are the inherited empty upstream Qt test templates. The suite uses the
existing offscreen Qt and isolated settings configuration. Warnings are retained in the
log; this result does not claim a warning-free run. The implementation commits above were
integrated with main at `036ff2fe` before this documentation-only delivery.

The real desktop [smoke harness](../tests/smoke_app.py), with temporary settings/APPDATA and
an isolated IPC pipe, also passed. `.venv/mechanical-final-smoke.log` records `ABOUT_OK`,
`PROJECT_SAVE_OK`, `PROJECT_ROUNDTRIP_OK`, `LASER_PREVIEW_OK`, `LASER_MULTIPASS_OK`, successful
SVG and DXF ZIP exports, `RENDER_OK` and `SHUTDOWN_OK`. The reopened project retained
`smoke_gerber` (Gerber), `smoke_drill` (Excellon), `smoke_iso` (Geometry) and `smoke_cnc`
(CNCJob). This exercises Gerber/Excellon import, isolation/CNC generation, save/reopen,
rendering, the existing laser workflow and normal application cleanup with listener,
worker and pool shutdown assertions.

Desktop screenshots remain local ignored evidence: `.venv/about-smoke.png`,
`.venv/startup-smoke.png` and `.venv/laser-cam-smoke.png`. Native Qt teardown warnings
appear after cleanup; no timeout or failed shutdown assertion is reported. The smoke
uses production-style native teardown only after its cleanup/output assertions.

Reproduce from the repository root with the pinned environment (example PowerShell path):

```powershell
$python = 'E:/VSCode/Flatcam/MikroCAM/.venv/repro-a/Scripts/python.exe'
$env:QT_QPA_PLATFORM = 'offscreen'
& $python -m pytest -q
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
& $python tests/smoke_app.py
```

The desktop run needs a Windows desktop session. No real machine or hardware cutting was
performed, and the mechanical smoke does not individually drive every ToolDB regression;
the focused behavior tests provide that coverage. This document records local evidence.
PR Windows CI is a separate required review check, not claimed complete here.
