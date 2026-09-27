# Implementation Plan: Safe-plane XY dry run
Branch: 014-dry-run. Date: 2026-09-27. The dependency 013 delivery gate must pass before
implementation can merge.

Use Python 3.13, the existing standard library/core/PyQt6, and no new dependencies or persistent
format.

Three stories and 29 tasks. `core/dry_run.py` handles pure derivation and lineage; `ui/dry_run_worker.py`
and `panel.py` provide the owned worker, review, and transfer flow. Add a small button and shutdown
seam to the existing preflight panel, with no legacy hook.

Reuse the parser, Placement, preflight, PreparedJob, and the existing Machine panel, Controller, and
Transport.

## Constitution Check
I: Yes. Pure core and Qt UI only.
II: Yes. No new legacy logic.
III: Yes. One concrete policy, with no framework.
IV: Yes. Millimetres, Placement, and source authority remain unchanged.
V: Yes. Pure and Fake behavior tests come first.
VI: Yes. Output start is removed; explicit clearance, review, live proof, and stop behavior are
reused. Physical claims are excluded.
VII: Yes. No external code is copied; the existing MIT source assessment applies.
VIII: Yes. Three stories and 29 tasks; modules stay within 600 lines, functions within 80 lines,
and public hints are included. No complexity exception.

## Validation
Validate analytic unit, mode, linear, arc, and helix cases; source preservation and rejection cases;
generation, lineage, and worker limits; and Qt transfer, invalidation, and shutdown. On the actual
desktop, run a Fake dry job and verify the first move is vertical, output start is absent, and
existing pause/stop behavior remains intact. Run the full pytest suite, import and growth checks,
and final-head Windows CI. Record invalidation in `invalidation.md`.

Sol may implement the pure generator with tests or the thin UI. Root reviews coordinate, mode, and
lineage behavior and handles integration.
