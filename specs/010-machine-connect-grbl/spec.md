# Feature Specification: Read-only GRBL connection

**Feature Branch**: `010-machine-connect-grbl`
**Created**: 2026-09-27
**Status**: Specified
**Input**: Roadmap 10: MachineController, state machine, GRBL, Serial and FakeGRBL;
connection, status and DRO, read-only. User directs completing the roadmap in order.

## User Scenarios & Testing

### User Story 1 - Explicit connection and disconnection (Priority: P1)
An operator selects a GRBL controller port and connects explicitly. They see whether the
connection is opening, available, failed or closed, and can disconnect from every state.
Opening the application or refreshing available ports does not connect automatically.

**Why this priority**: The operator needs a trustworthy connection boundary before any
later machine-control feature can exist.
**Independent Test**: A simulated controller connects, reports a failure, disconnects and
reconnects without sending motion or changing persistent settings.

**Acceptance Scenarios**:
1. **Given** no connection, **when** ports are refreshed, **then** no port is opened.
2. **Given** a selected compatible port, **when** Connect is pressed, **then** the application
   remains responsive and displays connection progress followed by actual status or a diagnostic.
3. **Given** a busy/unavailable port or a dropped connection, **when** communication fails,
   **then** the port is closed, coordinates become unavailable and reconnection remains explicit.
4. **Given** any connection state, **when** Disconnect or window/application close is requested,
   **then** the communication worker stops and releases its owned port without machine commands.

### User Story 2 - Truthful machine and work coordinates (Priority: P1)
The operator reads machine state and X/Y/Z coordinates in mm, with machine and work positions
clearly distinguished. Missing, stale or unverified values never appear as current zeroes.

**Why this priority**: Incorrect units or reused offsets can mislead an operator even before
this application is allowed to move the machine.
**Independent Test**: Simulated reports with mm/inch units and changing offsets yield analytic
positions; missing units, malformed reports, reset and timeout invalidate the displayed evidence.

**Acceptance Scenarios**:
1. **Given** valid report units and a machine position plus work offset, **when** a status arrives,
   **then** both machine and work coordinates are displayed in mm using the same offset.
2. **Given** only one coordinate system without an offset, **when** a status arrives,
   **then** that system is shown and the other remains explicitly unavailable.
3. **Given** an unknown unit setting, **when** coordinates arrive, **then** no converted DRO
   is presented as authoritative until units and a fresh status are known.
4. **Given** cached coordinates or offsets, **when** the controller resets, units change,
   communication becomes stale or the connection closes, **then** obsolete evidence is invalidated.
5. **Given** an alarm, hold, jog or externally running controller, **when** status arrives,
   **then** its actual condition is displayed; connection success does not imply Idle.

### User Story 3 - Read-only machine panel (Priority: P2)
The operator opens a compact Machine panel from the existing application, selects a port,
connects, observes state and coordinates, and disconnects without leaving CAM work.

**Why this priority**: Existing CAM workflows need a small usable connection surface.
**Independent Test**: A desktop/panel test injects the simulated transport, verifies status and
coordinate updates, then closes the panel and application with no remaining I/O worker.

**Acceptance Scenarios**:
1. **Given** a closed panel, **when** its menu action is used repeatedly, **then** one panel is
   reused and no duplicate connection or polling worker is started.
2. **Given** incoming status, **when** the panel updates, **then** I/O remains outside the GUI
   thread and only the GUI thread accesses widgets.
3. **Given** this read-only slice, **when** the panel is used, **then** it offers no jog, zero,
   home, unlock, reset, spindle/laser, streaming or arbitrary-command control.

### Edge Cases
- No ports; duplicate Connect requests; connection attempts while already connected.
- Partial/multiple serial lines, optional or reordered fields, unknown states, malformed or
  nonfinite coordinates, missing axes and oversized/incomplete records.
- Settings/status arriving in either order; missing offset; intermittent offset reports;
  changed units; controller startup banner during a session.
- Delayed/missing replies, partial writes, read/write/open failure and disconnect during polling.
- Close during connection setup; a report queued just before panel closure; repeated reopen.

## Requirements

### Functional Requirements
- **FR-001**: Enumerate available ports without opening them; require explicit Connect and
  never auto-connect/reconnect, reset or wake the controller.
- **FR-002**: Provide equivalent real-serial and simulated communication boundaries, with
  bounded reads/writes and explicit errors; simulation must cover disconnection and timeout.
- **FR-003**: Represent connection lifecycle and reported machine state explicitly. Unknown
  or unsupported state must remain visible and cannot be treated as Idle.
- **FR-004**: In this slice, transmit only controller status and stored-settings read requests.
  Never transmit motion, setting assignments, reset, unlock, homing or emission commands.
- **FR-005**: Poll without overlapping status requests; limit communication buffers and mark
  status stale after two seconds without a valid report.
- **FR-006**: Validate report units and finite three-axis positions; normalize once to mm.
  Machine position, work position and work offset must remain distinct.
- **FR-007**: Derive an absent coordinate system only when a valid offset is known in the
  current live session. Reset, unit change, disconnect and stale status invalidate cached evidence.
- **FR-008**: Preserve diagnostics for invalid/unsupported reports and communication errors;
  such evidence cannot create valid coordinates or a fabricated safe state.
- **FR-009**: Provide a thin reusable Machine panel with explicit port refresh/connect/disconnect,
  connection state, machine state, distinct machine/work XYZ and unavailable/stale indications.
- **FR-010**: Run serial work outside the GUI thread; deliver immutable snapshots to GUI-owned
  widgets. Closing/disconnecting must join the owned worker before releasing its objects.
- **FR-011**: Retain existing CAM behavior and package import boundaries. Hardware-independent
  logic must be testable without Qt, network, manufacturing hardware or user settings.
- **FR-012**: Make protocol activity diagnosable through bounded messages/application logging;
  the later console slice owns interactive raw commands and a console UI.

### Key Entities
- **Connection**: explicit selected port, opening/connected/closed/error lifecycle and diagnostic.
- **Machine observation**: reported machine state, report-unit evidence, timestamp and freshness.
- **Position snapshot**: optional machine/work/offset XYZ in mm, never invented when unavailable.
- **Communication boundary**: the owned serial connection or equivalent deterministic simulator.

## Success Criteria

### Measurable Outcomes
- **SC-001**: All simulated success, failure, timeout and reconnect scenarios transmit only
  the two allowed read requests; startup, refresh and closing transmit no machine action.
- **SC-002**: Analytic mm/inch and offset cases agree within 1e-9 mm, including both directly
  reported coordinate systems; invalid/missing evidence remains unavailable in every case.
- **SC-003**: Missing status becomes visibly stale within two seconds plus one polling interval;
  simulated disconnect/close completes within two seconds without a lingering worker.
- **SC-004**: Ten panel open/connect/disconnect/close cycles with simulation leave no duplicate
  panel, open transport or running worker; existing CAM desktop smoke still passes.
- **SC-005**: All existing and new tests and architecture checks pass on Windows/CPython 3.13.

## Assumptions
- GRBL 1.1 with the standard three-axis serial interface is the target; other firmware,
  transports, extra axes and actual movement remain outside this slice.
- Serial communication uses the established 115200 setting; no new profile persistence is needed.
- Roadmap dependency is foundation-guardrails; delivery follows reference/mechanical stabilization.
- Simulated hardware proves software behavior; it does not claim a particular real controller
  has been connected or that physical positioning is calibrated.

## Hazard Analysis
- Opening a serial port may cause a controller/adapter reset even without a reset command.
  The panel explains this before an explicit connection; all positions start unverified.
- Read-only Disconnect stops this application's communication, not externally running motion.
  The panel must not label it Emergency Stop or imply physical interlock capability.
- Wrong units, stale coordinates and stale offsets are mitigated by explicit validity and
  invalidation rules. No move, emission, zero or persistent setting can be issued in this slice.
- Later motion/emission slices require their own safety analysis and controller stop behavior;
  this panel must not bypass those future gates by exposing a raw send operation.
