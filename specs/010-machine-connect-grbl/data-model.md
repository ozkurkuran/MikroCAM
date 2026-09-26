# Data model: Read-only GRBL connection

All published values are frozen dataclasses with immutable finite XYZ tuples or None. No Qt,
serial object, mutable mapping or transport handle crosses in a snapshot.

## Connection and machine state
`ConnectionState`: DISCONNECTED, CONNECTING, CONNECTED, ERROR. Connection success describes
an open channel, not machine readiness. MachineState includes UNKNOWN, IDLE, JOG, RUNNING,
PAUSED, ALARM, HOMING, CHECK, SLEEP, DOOR, ERROR; original state text is retained. Do not claim
PROBING or ESTOP from a GRBL field that does not report that condition. Later active-control
slices add owned-operation states when there is a concrete operation to represent.

`GrblStatus`: reported raw machine-state text plus exactly one directly reported XYZ vector
(MPos or WPos), optional WCO. Unknown optional fields are ignored; malformed/duplicate required
fields, both coordinate systems, wrong axis count and nonfinite values are rejected.

`MachineSnapshot`: connection state, machine state/raw text, optional machine_position_mm,
work_position_mm, work_offset_mm, report_units (`mm`, `inch` or None), stale flag, optional
last valid report timestamp and diagnostic. Invalid or stale positions are None, not zeroes.

## Coordinate evidence
The GRBL boundary uses report-unit evidence from `$13=0` or `$13=1`; inch values multiply by
25.4 once. Work=machine-offset; machine=work+offset. Offset is never inferred from unrelated
snapshots. A directly reported vector remains usable without WCO, while the derived vector
is None. Incoming unit evidence changes invalidate old positions/offset; wait for a new report.
A startup banner invalidates units as well. Stale status clears positions and offset; a fresh
status may recover the direct position, but derivation waits for a new offset.

## Wire and lifecycle
Incremental ASCII records terminated by CR/LF, bounded at 512 bytes/line; read chunks <=4096.
Allowed TX: one-byte `?` and the complete settings read `$$\n`. ACK/error lines belong only
to the outstanding settings transaction; status frames are independent. Preserve meaningful
controller alarms/startup and diagnostics. Do not expose an arbitrary-send controller method.

Disconnected -> Connecting -> Connected, or Error on open/I/O/short-write failure. Explicit
Disconnect from any state closes its owned transport and clears session evidence. New Connect
starts clean; no automatic reconnect. Duplicate Connect while connected is rejected without
opening a second transport. A missing status reply permits a later read-only retry, not an
assumption of Idle or a serial reopen. Poll every250ms with one outstanding query; response
expiry is2s. Settings transaction expires at3s; keep units unknown and surface that diagnostic.
No persistent application or controller format is introduced in this slice.
