# Validation: Placement transform

## Pre-implementation analysis
16/16 specification checks pass; no extension hooks. FR-001/002 map to T003–T004;
FR-003/004 to T005–T007; FR-005 to invalid-input cases T003/T006;
FR-006 and SC-004 to architecture/full-suite checks T008. SC-001/002/003 map to analytic
fixtures, deterministic round-trips and geometry/point comparisons. Two stories, ten tasks.
No unresolved requirement, constitutional exception or dependency.

## Implementation evidence

Tests were added before the core module and initially failed with ModuleNotFoundError.
The final focused placement suite has **55 passing tests**, including 100 deterministic
randomized placements/round-trips, strict absolute 1e-9 mm reference checks, holes/multipart/
empty geometry, non-finite/3D/M rejection, immutable inputs and a fresh-process import/use
without Qt, VisPy, serial or host modules. Review confirmed forward/inverse matrix algebra.
Malformed outer point sequences initially raised TypeError in three cases; a thin validation
now raises the documented ValueError and all four sequence regressions pass.

Before integration with slice 003, the complete suite passed **644 tests and 310 subtests**
in 50.00s (2 original placeholders skipped, 3 original SWIG warnings). The subsequent five
placement checks also pass. Import-boundary checks pass; legacy growth is +0 for this slice.
After integrating slice 003, the complete clean-core suite passed **694 tests and 310 subtests**
in 51.97s, with the same 2 placeholders skipped and 3 SWIG warnings. The runtime module is
113 lines and the largest method 14 lines; no new dependency or legacy edit. No GUI smoke
is required for this pure core slice.

Windows [CI run 36272082050](https://github.com/ozkurkuran/MikroCAM/actions/runs/36272082050)
passed **694 tests and 310 subtests** in 42.83s, with 2 original placeholders skipped;
`pip check` found no broken requirements. [PR 4](https://github.com/ozkurkuran/MikroCAM/pull/4)
was retargeted to main after branding PR 3 merged. All ten tasks are complete.
