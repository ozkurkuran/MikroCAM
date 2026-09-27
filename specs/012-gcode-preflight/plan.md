# Implementation Plan: Read-only G-code preflight
**Branch**: `012-gcode-preflight` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

## Summary
Bounded pure-core modal analysis feeds an immutable report. A narrow bridge copies complete
CNCJob/file text; a cancellable Qt dock shows declared setup, extents, findings and nominal time.
No controller/serial API is involved. Existing Placement remains the XY transform authority.

## Technical Context
Windows x64/CPython3.13, stdlib plus existing Placement/Shapely, existing PyQt6. No new dependency
or persistent format. Limits:16MiB text,250000 lines,4096 chars/line,64-char decimal token,
absolute magnitude1e9,200 retained findings with full counters. Online accumulation avoids
retaining toolpaths. Target100000 lines<=10s, cancellation<=1s; UI join2000ms retains on timeout.
Strict subset in contracts/preflight.md; unknown semantics fail closed and invalidate complete
bounds/time. Required setup fields start empty; optional rapid rates default to unknown.

## Constitution Check
| Gate | Answer / evidence |
| --- | --- |
| I layers | Yes: pure core values/parser/geometry; bridge source I/O/copy; Qt UI only. |
| II legacy | Yes: only lazy menu hook and shutdown guard, expected<15 aggregate added lines. |
| III abstraction/dependencies | Yes: concrete analyzer/report/worker; no new dependency/interface framework. |
| IV authority/format | Yes: mm normalization once, existing Placement, no new persistence schema. |
| V tests first | Yes: analytic/parser/adverse tests before implementation; no hardware/display required. |
| VI safety | Yes: explicit setup/unsupported blocking and stale/cancel state tests; no physical commands. |
| VII provenance | Yes: independent implementation from official protocol facts; no source port/new license. |
| feature size | Yes: three stories,37 tasks. |
Post-design review: all gates remain yes; no complexity exception.

## Project Structure
- core/gcode_models.py: frozen source/setup/finding/report limits/values.
- core/gcode_lexer.py: bounded source-line/word lexer, structured parse errors.
- core/gcode_motion.py: independent arc construction, transformed extrema/path length.
- core/gcode_parser.py: concrete modal interpreter yielding known movement/dwell/metadata events.
- core/gcode_preflight.py: streaming analyzer, checks/counters/bounds/time/report.
- bridge/gcode_source.py: complete selected-job snapshot and bounded UTF-8 file load.
- ui/preflight_worker.py, preflight_setup.py, preflight_panel.py: bounded analysis, fields/report.
- appMain.py, appHandlers/appLifecycle.py: minimal menu/shutdown integration only.
- tests/test_gcode_{models,lexer,motion,preflight,source,ui}.py and tests/smoke_app.py.
Keep new modules<=600 lines and functions<=80. Split by existing concrete responsibilities,
not speculative strategy/registry abstractions. Public values/functions have type hints.

## Design
Parser state tracks explicit units/distance/plane/feed modes, current XYZ and physical feed,
motion mode, program end and metadata. Validate full block before advancing state. Conflicting
or unused words fail with source line; do not partially accept a block. Feed errors that leave
geometry known are findings; unknown geometry terminates interpretation and marks partial.
Interpreter emits one concrete event per executable block. Analyzer updates exact transformed
extents, rapid/feed/arc counts and distance/time, then discards the event. Arc geometry uses
signed angular sweeps and cardinal extrema in transformed machine XY; include endpoint rounding.

Report retains exact source digest and setup. Total duration None on any unknown contribution;
no-movement file blocked. Diagnostics cap storage at200 while counts remain complete. Cancel
is checked per line and before delivery. No machine APIs, temporary file rewrites or source edits.

UI loads a source snapshot explicitly and requires numeric machine/setup inputs. Existing
Placement is constructed from declared origin/translation/rotation/mirror controls; no duplicate
transform math. Worker receives only frozen core values. GUI-side generation tokens reject old
results; selected-job source is rechecked before display and periodically. File result explicitly
labels its loaded snapshot/digest, not current disk contents. A closed or cancelled worker is
joined before deletion;2s timeout retains the worker/window and host quit is refused.

## Delivery
Tests first, then focused domain/bridge/Qt tests,100000-line/cancel measurement, architecture/
size checks, actual desktop CAM/laser/manual/preflight smoke and complete Windows suite. Record
sources/limitations in validation.md and operator docs. PR is merged only after final-head CI.
