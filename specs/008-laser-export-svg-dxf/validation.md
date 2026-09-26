# Validation: SVG/DXF pass export
## Pre-implementation analysis
Three stories/fourteen tasks, all eight constitution gates pass. FR-001/002/003 and SC-001
map to T002–T004; FR-004/005 and SC-002 to T005–T007; FR-006 to atomic/cancel/limit tests;
FR-007/008 and SC-003/004 to T008–T012. T013 distinguishes target-app/physical checks.
No new runtime dependency, legacy code or device behavior. Manifest is new schema1; existing
job/recipe formats remain unchanged. No unresolved design exception. Execution pending.

## Implementation evidence
Format tests first failed for the absent serializers; 24 now pass using independent XML,
SVG renderer and ezdxf readers. The 25.4 mm fixture reads as 72 points (one inch); all path
vertices, order, closure, gaps and nonidentity placement round-trip within 1e-8 mm. Geometry
writers add no registration exposures. Strict manifest and atomic-package tests: 73 pass.
They cover duplicate/missing/unknown/future/nonfinite data, all parameters, ordinal names,
hashes, pass/vertex/path/byte limits, extent overflow, file failures and the publication boundary.

The complete integrated suite passed **1109 tests and 310 subtests** in 58.71s, with two
original placeholders skipped and three inherited SWIG warnings. A subsequent UI regression
caught an old Saved notification overwriting a reentrant new export's Exporting status;
its fix and added case pass in the final **136-test focused suite**, including 39 UI cases.
Final architecture checks: 83 pass. Hosted CI will exercise the complete final 1110-case set.

Real desktop smoke passed all CAM/project/preview/multipass stages, then exported SVG
(45,521-byte ZIP) and DXF (46,969-byte ZIP), each with two 110-path files, recipe, manifest
and README. Both archives were independently reopened; settings/counts/units verified.
The maximized desktop screenshot `.venv/laser-export-smoke.png` was visually inspected;
recipe controls, preview and export status are visible. OpenGL render and normal worker/
process shutdown passed. Logs and synthetic packages remain in ignored `.venv`.

No legacy changes, new dependency or recipe/job schema change. New manifest is schema 1.
Modules/functions remain within 600/80 lines; largest new export module is129 lines/27-line
function. Runtime core/domain imports obey boundaries. No external source code was ported.

## External verification status
Standard uninstall registry entries and Program Files showed no LightBurn/EZCAD/JCZ install.
Target-app import and a physical PCB coupon have not been performed. An asynchronous user
question asks which target application is used. This does not block the software export
implementation, but the roadmap's physical 0.2 milestone remains open. The transfer guide
and archive README state these limits and exact manual scale/axis/settings/order checks.

## Hosted delivery gate
Windows [CI run 36274593478](https://github.com/ozkurkuran/MikroCAM/actions/runs/36274593478)
passes **1110 tests and 310 subtests** in 51.03s; two original placeholders skipped,
three inherited SWIG warnings and clean `pip check`. Independent read-only review found
no actionable defect in units/axis/path order, manifest fidelity, atomicity or UI lifecycle.
[PR 8](https://github.com/ozkurkuran/MikroCAM/pull/8) targets main after 007 merged.
All fourteen software/delivery tasks are complete. Physical milestone remains explicitly open.
