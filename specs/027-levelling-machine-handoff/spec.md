# Feature Specification: Levelling to Machine handoff

**Branch**: `027-levelling-machine-handoff` | **Created**: 2026-10-01
**Input**: Complete MACHINE_CONTROL_ROADMAP phase B using the user's proposed Machine handoff.

## Clarifications

### Session 2026-10-01
- Q: Route GRBL Levelling to Machine or keep separate bridged control tabs? → A: Use the
  user's earlier explicit proposal: close the legacy path and direct the operator to Machine.
  The request to complete the remaining phases applies that proposal. No new device or
  automatic connection is authorized. A later user correction can steer this decision.

## User Scenarios & Testing

### US1 - One GRBL communication owner (P1)
An operator selects GRBL in Levelling and sees a short explanation and Open Machine button
instead of connection, motion, zero and sender controls. Selecting GRBL or invoking retained
legacy connection/search paths does not open or probe any COM port.

Acceptance: choose GRBL repeatedly and reset/reopen the tool; no serial constructor/open/write
is called. Old GRBL tabs remain hidden and disabled. Direct legacy callbacks cannot bypass
this restriction. An already connected Machine keeps its same owner and connection.

### US2 - Reach the current GRBL workflows (P1)
The operator opens Machine from Levelling to use existing probe-grid, autolevel/preflight and
job workflows. Opening the panel never automatically connects, starts probing, sends an
unreviewed job or transfers a legacy height map.

Acceptance: clicking Open Machine displays/reuses the application's Machine dock, preserving
existing state; no serial I/O occurs. Actual desktop shows the handoff and visible Machine dock.

### US3 - Keep offline controller workflows (P2)
Operators using MACH3, MACH4 or LinuxCNC continue generating probe G-code and importing
height files using their existing Levelling workflow. Switching back from GRBL restores
these controls, and the handoff explanation disappears.

Acceptance: all three controller choices retain offline controls and their prior tests pass
unchanged. GRBL state is not mistaken for an offline controller; no legacy port persists.

## Requirements
- FR001: GRBL selection MUST hide and disable legacy Connect/Control/Sender controls and show
  a localized explanation and one explicit Open Machine action.
- FR002: Levelling MUST NOT open serial ports or enumerate them by opening devices, including
  via direct connection/search callbacks, tool reset, reopening or repeated controller changes.
- FR003: While GRBL is selected, retained legacy TX/read callbacks MUST reject/return without
  writing or reading even when a stale or externally injected serial handle exists.
- FR004: Open Machine MUST reuse the existing dock/owner and MUST NOT connect, probe, send,
  zero or automatically transfer legacy data.
- FR005: MACH3/MACH4/LinuxCNC probe-code generation and height import MUST retain current
  behavior; switching controllers MUST restore the correct offline controls.
- FR006: Retain upstream legacy implementations for future merges, but make their device
  connection/control paths inaccessible from the runtime Levelling workflow.
- FR007: Update PROBING and AUTOLEVEL documentation to explain the single-owner GRBL route.
- FR008: Test failures before implementation, existing Levelling journeys, complete suite,
  architecture checks, actual desktop screenshot and final-head Windows CI MUST verify delivery.

## Edge Cases
Repeated tool reset/controller switching; programmatic call to old callbacks; stale injected
handle; Machine already connected or actively owned; absent app dock before first handoff;
port metadata refresh failures. Handoff does not disconnect or steal an active Machine owner.

## Key Entities
Selected controller; offline Levelling inputs; application-owned Machine dock and its existing
serial owner. This feature introduces no machine protocol, persisted format or job model.

## Success Criteria
- SC001: All selection/reset/search/connection regressions record zero serial opens; all
  blocked GRBL wire paths record zero TX/RX calls, including with an injected mock handle.
- SC002: One button displays the same existing Machine panel without any connection or
  motion; an actual desktop screenshot visibly proves the handoff.
- SC003: All three offline controller choices restore their prior controls and pass existing
  Levelling tool/journey tests unchanged.
- SC004: The complete local suite and final-head Windows CI pass with source attribution
  and architecture rules intact before delivery; physical validation remains open.

## Assumptions and Scope
Machine's probe025, autolevel026 and sender013 already exist. No new controller, bridge to
legacy tabs, automatic connect, legacy code deletion or firmware/network support is added.
Legacy helpers may be exercised in isolated mock-only regression tests, never as runtime I/O.

## Hazard Analysis
Hidden widgets alone cannot prevent programmatic/stale callbacks from bypassing ownership:
block both legacy port construction/enumeration and GRBL TX/read boundaries. Never open a
port to search for devices. Handoff reuses one Machine owner and does not transfer unreviewed
legacy input. Existing Machine admission/stop/preflight gates remain authoritative. This
feature emits no machine motion and makes no physical stopping or output-off claim.
