# Validation: Laser contour and hatch

## Pre-implementation analysis
Three stories, eighteen tasks. FR-001/002 map to T004–T006/T011–T012; FR-003/004 to
T007–T008; FR-005 to T009–T010; FR-006 to kernel and worker cancellation tests;
FR-007/008 to T011–T015; FR-009 and SC-004 to T016–T017. SC-001 uses independently
authored analytic geometry fixtures, SC-002 error/cancel tests, SC-003 desktop smoke.
All eight constitutional gates pass without exception. No new dependencies, schema,
controller, manufacturing action or external source port. Execution evidence pending.

## Implementation evidence

Tests preceded the missing core/domain modules (three collection failures) and bridge/UI.
The initial full integration passed 935 tests and 310 subtests. Independent numeric review
then exposed missing boundary hatch rows at exact 90/180/270-degree rotations. Five new
regressions failed before the shared Placement fix; exact cardinal coefficients now preserve
these rows without duplicating transform logic. All 136 placement/core planning tests pass.

Offscreen integration covers 16 panel/worker and 24 bridge cases. Late queued completion after
cancel and small-window controls each failed before their fixes. Snapshot/publication stay
on the GUI thread, calculation runs in the worker, close/hide/shutdown cancel safely, sender
identity rejects stale results, and scrollable controls leave Generate/Cancel visible.

Real desktop smoke passed startup/About, Gerber/Excellon, isolation, 26,367-character G-code,
project save/reopen, then generated 110 laser paths, replaced only the owned Geometry,
preserved source copper and selection, reopened the panel, rendered OpenGL and shut down
normally. The `.venv/laser-cam-smoke.png` screenshot was visually inspected; controls fit a
small window through scrolling. This is a synthetic software smoke, not physical PCB output.

New modules are below 600 lines and functions below 80; UI 292/25, worker 39/11, bridge143/37.
Legacy appMain adds only six menu-hook lines. No dependency, controller or persistence schema
was added. Hosted CI remains the delivery gate.

After the cardinal-boundary fix, the complete suite passes **944 tests and 310 subtests**
in 54.64s (2 original placeholders skipped, 3 inherited SWIG warnings). Import/growth checks
pass. The final transform fix is covered by exact coordinate/scan tests; the earlier desktop
smoke used 30-degree hatch, whose behavior is unchanged.
