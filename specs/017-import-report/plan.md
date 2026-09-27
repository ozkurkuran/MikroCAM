# Implementation Plan: Import quality report

Branch `017-import-report`, 2026-09-27. Three stories, at most 36 tasks. Deliver only after016
passes validation and merges. No dependency, importer re-run, machine communication or geometry edit.

## Summary and technical context
CPython3.13, pinned Shapely2 and PyQt6. Preserve the original SVG root attributes and actual flip
flag in existing immutable source results. Pure core builds a bounded report from those facts and
already rendered geometry. Separate strict schema1 dictionary codecs serialize only the summary.
The existing bridge/UI SVG boundary assigns the encoded report to its owning Geometry/Gerber object
on successful import. A tiny optional legacy serialization field preserves it; absent old fields
retain None. Existing project envelope/version remains unchanged; the new embedded report is
independently versioned. The selected object's Properties UI gets a collapsed, read-only section.
It displays historical import evidence, never current-edit validity or machine approval.

## Constitution Check
| Gate | Result |
| --- | --- |
| I layers | core owns facts/quality/codec; bridge host conversion; UI read-only presentation |
| II legacy | minimal optional field and UI/adapter hooks in Geometry/Gerber, aggregate <+50 lines |
| III simplicity | concrete summary and widget, no registry/new dependency/renderer |
| IV truth | existing mm import mapping, no resampling or independent transform; schema1 summary |
| V tests first | analytic facts, strict codec/migration, host ownership and Qt lifecycle regressions |
| VI safety | no controller/transport access; bounded read-only data |
| VII license | independent code and existing pins, no external copied implementation |
| VIII slices | three stories, <=36tasks, independently testable data/UI/persistence |

All gates pass; no complexity exception. Modules<=600lines, functions<=80, public APIs annotated.

## Structure and ownership
- core/import_report.py: immutable coordinates/quality/report records and analytic builder (Sol).
- core/import_report_codec.py: strict schema1 dict codec, bounds and old/unknown version tests (Sol).
- core/svg_models.py + importers/svg_document.py + bridge/svg_import.py: retain root facts/flip (root).
- bridge/import_report.py: host get/store boundary with no geometry import or I/O (root).
- ui/import_report.py: collapsed selected-object report, plain text, invalid/unavailable states (Sol).
- ui/svg_import.py and Geometry/Gerber host seams/serialization: narrow integration (root).
- Dedicated tests and smoke report additions: root integration, Sol isolated widget/data tests.

Root freezes exact shared contracts before delegation and alone stages/commits. Tests first, then
full suite/import/growth/size, actual desktop switch/save/reopen and old journeys, final-head CI.
