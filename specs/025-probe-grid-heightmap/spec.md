# Feature Specification: probe grid and height map

**Branch**: `025-probe-grid-heightmap` | **Created**: 2026-09-27 | **Status**: Approved design
**Input**: Roadmap 025: ProbeMap, Fake grid probing, save/load and visualization.

## User Scenarios & Testing

### US1 — Define and inspect a bounded map (P1)
A PCB operator defines a regular rectangular grid in G54 work millimetres, clearance and
lowest probe Z, feed, and explicit machine travel limits. The operator sees the points and
the coordinates that will be measured before starting. No action starts from opening a panel.
Independent test: define a 3×2 grid, verify all six positions and reject invalid ranges/counts.
Given missing/invalid inputs, Review fails without any controller write. Given edited inputs,
the previous review becomes unavailable until reviewed again.

### US2 — Acquire with one owner and stop on uncertainty (P1)
With a connected verified idle controller, the operator explicitly starts the reviewed grid.
The UI shows progress and measured heights; stop/disconnect remains available throughout.
Independent test: Fake produces an analytic plane for six points; result matches positions and
heights. Given a missed probe, malformed evidence, alarm, timeout or stop, further points are
not sent and the map is clearly incomplete. Jog/zero/job/console cannot overlap probing.

### US3 — Save, load and view measurements (P2)
The operator saves complete or incomplete maps and reopens them without hardware. The viewer
shows axes, physical coordinates, measured Z and missing points with an explicit completeness
label. Independent test: exact versioned roundtrip after disconnect; malformed maps leave the
current view unchanged and never write to a machine.

## Requirements
- FR001: Use finite bounded G54 work-mm grid axes with 2..64 points each and at most 1024 total.
- FR002: Require explicit min/max machine XYZ, initial position/G54 binding, clearance Z above
  minimum Z, bounded positive probe/travel feed and response deadline; validate every generated
  endpoint and initial upward clearance against the envelope before starting.
- FR003: Review inputs and live initial/G54 evidence; editing invalidates review. Start is explicit.
- FR004: The existing machine owner alone reads/writes the transport and admits at most one
  operation. Probe preparation verifies startup blocks, mechanical mode, units, G54, zero
  temporary/tool offsets and controller-reported spindle/coolant off.
- FR005: Retract to clearance before XY travel, probe vertically, and retract after each sample.
  Record a point only after one correlated successful probe result, command acknowledgement and
  fresh Idle position/offset evidence; a final safe retract is required for COMPLETE.
- FR006: Missing/duplicate/failed/malformed probe result, unexpected ACK, stale status, offset
  changes, out-of-envelope or unexpected position, alarm/reset/disconnect/timeout stop progression.
  Stop is priority and marks physical stopping unverified until independently established.
- FR007: Preserve measured points and incomplete outcome after interruption; never fill missing
  samples with zeros or offer incomplete maps as complete. Reconnect does not resume motion.
- FR008: Versioned bounded exact-schema JSON stores grid, heights, work offset and outcome;
  save uses atomic replacement. Loading/viewing is offline and never creates machine requests.
- FR009: Display a height visualization plus numeric grid and physical coordinate labels,
  including missing points and min/max measured Z; retain provenance as measured/simulated.
- FR010: Fake scenarios cover normal grid, unit conversion, delayed/chunked ACK/results,
  missing/failed/duplicate results, alarm, limits, disconnect, stop and shutdown; prior features pass.

## Entities
ProbeGrid: ordered work-mm X/Y axes. ProbePlan: grid, Z/feed/deadline, machine envelope and
reviewed live binding. ProbeMap: grid, ordered optional heights, G54 offset, origin and outcome.
ProbeObservation: operation phase/progress/map/diagnostic and explicit admission/stop flags.

## Success Criteria
- SC001: Analytic Fake 3×2 plane yields six physical heights within 0.005 mm and a verified final retract.
- SC002: Each injected failure prevents further ordinary motion and leaves truthful partial data.
- SC003: Complete/incomplete maps survive exact save/load; invalid or excessive files are rejected.
- SC004: Actual desktop shows review/start/progress/map/save/load using Fake; no physical device claim.
- SC005: Full suite, architecture/growth, existing desktop journeys and final-head CI pass before merge.

## Hazard analysis
Wrong frame/units can cause a collision: require explicit envelope and fresh bound G54/position,
verified units, absolute-mm commands, and endpoint checks. A stuck/missing probe can plunge:
use bounded downward G38.2, positive feed, response deadline and failure stop. Clearance must be
chosen by the operator; software cannot infer clamps/stock. Unexpected startup/spindle modes are
rejected or verified off before movement. A dropped link cannot prove stopping: best-effort stop,
tainted session, visible uncertainty, no automatic retry/resume. Software checks do not replace
physical emergency stop/interlocks or a probe wiring test. This slice is validated using Fake.

## Scope
No Z compensation or arc segmentation (026), adaptive grid, bicubic interpolation, automatic
resume, probe hardware setup, automatic homing/unlock, laser probing, or replacement transport.
