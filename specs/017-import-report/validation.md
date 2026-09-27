# Validation: retained import quality reports

Status: delivered; implementation, full suite, desktop and final-head Windows CI passed.
Three stories, 34 tasks; no dependency, renderer, worker or machine communication added.

## Requirements and constitution
FR001–004 / SC001–002: source root attributes and actual flip are retained in the immutable import
result. The core builder reports original tokens/unit labels, viewBox/aspect, physical viewport,
root-to-mm mapping, material bounds and atomic validity counts from that exact result. Source
open/closed counts preserve explicit closure even when fill implicitly closes a path. Precision
and bounded notices are recorded; no re-import/resampling or bounding-box scale inference occurs.
Dimension tokens and unit labels cross-validate, including absent and unitless cases.
FR005–006 / SC003: each selected Geometry/Gerber owns one parented, collapsed Properties section,
placed after its basic information. Names/notices are plain text with visible control escapes.
The historical-evidence label prevents import-time measures from being presented as a live audit.
Missing/invalid data clears prior content; ordinary objects hide the section.
FR007–009 / SC004: a separate optional schema-1 report field survives existing project encoding.
Old absent fields retain None; unsupported/corrupt reports show unavailable evidence without
blocking normal object access. Tool options, source and material are untouched by report storage.
Failed imports preserve previous reports and cannot publish partial success.
FR010 / SC005: focused data/codec/host/lifecycle and actual desktop evidence are below; full suite
includes source/reference/architecture/growth regressions. No change to frozen reference artifacts.

All eight gates pass: pure core facts/codec, bridge host boundary and thin UI; eight aggregate
legacy lines added, below 50; concrete records/widget, existing mm authority and independently
versioned summary; tests first; no controller path; independent code/existing licenses; three stories.
Largest new module 211 lines, largest function 40 (limits 600/80). No complexity exception.

## Tests first and audit
Model, codec, source, bridge and UI tests first failed on missing modules/fields. Thirteen additional
red regressions exposed accepted malformed/nonpositive dimensions and mismatched unit labels;
strict cross-validation fixed them without inventing missing dimension facts. Independent audit
found no further blocking issue. Codec count limits are explicit range checks, not proof of source
provenance; the actual builder computes counts from the immutable import result.
134 new report tests cover strict records, schema/version/unknown-key/UTF8/size limits, unchanged
WKB, source facts/flip, components versus explicit paths, two owners, no re-import, failed import
atomicity, real object serializers/old fields, plain-text rendering, stale-state clearing and parent
lifetime. Combined with 55 existing SVG import/host cases: 189 passed in 2.76 seconds.

Runtime head: `30e73ffe3bce41b2373b8d9161d338a81906875f`.
Full suite command: `python -m pytest -q --junitxml=.venv/import-report-pytest.xml`.
Full suite: 3218 passed, 2 skipped, 11 warnings, 310 subtests passed in 225.04 seconds.
The two skipped upstream Qt placeholders and existing dependency warnings remain unchanged.
Ignored local log is .venv/import-report-pytest.log.

## Actual desktop
At that runtime head, `python tests/smoke_app.py` exited 0. Two SVG imports describe the same physical
material using mm and cm tokens. Selection displays the correct owned units/source SHA, physical
bounds, component/path counts and precision; save/reopen preserves both report dictionaries and
source text exactly. Marker: IMPORT_REPORT_SELECTION_ROUNDTRIP_OK 2; existing
SVG_PHYSICAL_SOURCE_ROUNDTRIP_OK also passed.
Root inspected the 3840x2089 .venv/import-report-smoke.png: the expanded report is visible below
Gerber basic properties, with historical label, source identity, cm units and viewport facts.
All earlier CAM/project/laser/manual/console/preflight/streaming/dry-run journeys passed, ending
JOB_ACTIVE_SHUTDOWN_OK, PREFLIGHT_SHUTDOWN_OK, MACHINE_SHUTDOWN_OK and SHUTDOWN_OK. Existing
editor/QThreadStorage teardown warnings remained after successful owned shutdown.
Local evidence: .venv/import-report-smoke.log and .venv/import-report-smoke.png.

## Limits and delivery
[Operator guide](../../docs/IMPORT_REPORT.md), [schema and interfaces](contracts/import-report.md).
Reports are historical import summaries, not current edited-geometry audits or manufacturing
approval. Initial complete reports are SVG; missing old/non-SVG reports remain unavailable.
Other source detection/import workflows stay in later slices. No physical machine was exercised.
[PR18](https://github.com/ozkurkuran/MikroCAM/pull/18) merged as `24f89b608ef356659369cde407d2d48ca03e8a29`.
[Windows CI](https://github.com/ozkurkuran/MikroCAM/actions/runs/36291546754) passed in 5m25s at final head `3fe1391333e92a7ea3b3e6dfb048f8d2bdb86a80`.
