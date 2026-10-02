# Implementation Plan: Levelling to Machine handoff

Branch: `027-levelling-machine-handoff`; date 2026-10-01; [spec](spec.md).

## Summary
Provide a localized Qt notice/button, hide/disable legacy GRBL controls, eliminate probing
port scans, block public connection and GRBL serial entry points. Reuse the existing Machine
dock explicitly. Keep offline Levelling and retained upstream implementations.

## Technical Context
CPython 3.13, pinned PyQt6/pytest/pyserial already present; Windows 11 desktop primary.
No storage schema, new dependency, controller or transport. Handoff does zero device I/O.
One new small `mikrocam/ui/levelling_handoff.py` module, test and desktop helper; tiny legacy hooks.

## Constitution Check (pre/post design)
1. Yes: new UI logic under mikrocam.ui; only bridge metadata access, no legacy imports.
2. Yes: legacy edits are guards/short hookups, targeted net growth below 50 lines.
3. Yes: no new abstraction registry/dependency; guard has multiple concrete callbacks.
4. Yes: no unit/transform/format duplication or persistent schema.
5. Yes: test first, mock serial and injected Fake only; no physical connection.
6. Yes: spec hazard analysis; existing one-owner Stop/admission gates reused unchanged.
7. Yes: Evo change attribution updated, no external source copied.
8. Yes: three stories, twelve tasks, independently testable increments.
No complexity exceptions.

## Project Structure
- `mikrocam/ui/levelling_handoff.py`: card attachment, visibility and callback guard.
- `appPlugins/ToolLevelling.py`: attach hook, guarded callbacks, blocked connection and
  metadata-only enumeration; original open/search code retained under private names.
- `tests/test_levelling_machine_handoff.py`: no-port/no-wire, direct callbacks and controller switches.
- `tests/test_levelling_grbl_wire.py`: Phase A tests call retained connection helper with
  mock serial; other wire tests use non-GRBL mock selection, never runtime enablement flags.
- `tests/smoke_levelling_handoff.py`: real desktop selection/handoff and screenshot.
- `tests/smoke_app.py`: invoke the desktop helper in the established end-to-end app harness.
- `docs/PROBING.md`, `docs/AUTOLEVEL.md`, `THIRD_PARTY_CHANGES.md`: route and attribution.

## Test and implementation order
Tests first for blocked direct connection/search, all GRBL I/O callbacks (including queued
worker-capable entry points), repeated controller changes and reused inert Machine dock.
Then implement UI/guards and adapt only the Phase A connection regression to its retained
private helper. Existing tool/journey tests stay unchanged. Desktop harness uses Fake only.
Finally complete suite/architecture, inspect screenshot and require final-head Windows CI.
PR is stacked on Phase A while PR28 is open. No ROADMAP delivery line changes before merge.
