# Research decisions

- Decision: use existing `open_machine_panel(app)` on an explicit button.
  Rationale: it reuses the application dock and does not create/connect a controller.
  Alternative: bridge old tabs to controller; rejected because it duplicates 013/025/026.
- Decision: stop controller-selection port scans and use existing metadata-only `list_ports`.
  Rationale: legacy scanner opens all COM1-256 and bypasses ownership even before Connect.
  Alternative: hide Connect only; insufficient because search opens ports.
- Decision: block public connection unconditionally; retain its original private implementation
  for upstream/mock regressions. Guard all serial read/write/scheduled-motion callbacks when
  GRBL is selected, before side effects. Decorator preserves legacy source/function metadata.
  Rationale: hidden controls and worker scheduling alone cannot prevent stale direct callbacks.
  Alternative: remove legacy implementations; outside user-requested merge-friendly scope.
- Decision: create a small Qt handoff card under `mikrocam.ui`, attach it to the root tool layout outside disabled offline controls.
  Rationale: new presentation belongs to UI; legacy gets only imports/hooks/guards.
- Research agent independently inspected all I/O entry points and confirmed these choices.
  No external fork was read, no dependency introduced, no physical device opened.

Desktop refinement: root-level card is independent of disabled legacy CNC eligibility; one regression failed before this correction.
