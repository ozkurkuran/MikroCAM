# Quickstart validation

Use the pinned CPython3.13 environment. Run dedicated import_report model/codec/bridge/UI tests,
then full pytest and tests/smoke_app.py. The full suite includes frozen references and layer/growth
checks. Desktop requires normal OpenGL; test records use no manufacturing hardware.

Import two analytic SVGs with different source units and an inferred-size example. Select each
Geometry/Gerber object, expand its report and compare root mapping, mm bounds, open/closed counts,
precision and notices to independent expected facts. Save/reopen and verify exact retained reports.
Switch to a preexisting ordinary object, delete one import and reject malformed SVG; no stale report.
Old objects without data remain usable; invalid/newer encoded reports display unavailable evidence.

Read contracts/import-report.md for limits/format. Record exact runtime head, counts, real desktop
results and final-head CI in validation.md. Reports describe the import instant, never machining
readiness or subsequent edits. Do not claim physical-machine validation.
