# Read-only GRBL integration contract

## Transport
`Transport.open() -> None`, `read(size: int) -> bytes`, `write(data: bytes) -> int`,
`close() -> None`. One worker owns all calls. Read size is positive/bounded, write must return
the complete byte count, close is idempotent. Concrete SerialIO uses the selected physical
port at115200, read timeout50ms, write timeout500ms; no URL/network transport. It does not
send wake bytes, reset, unlock, G-code or manipulate DTR/RTS as a connect sequence.
Port enumeration uses metadata only and does not open any port.

FakeGRBL implements the same boundary, records transmissions, returns deterministic settings/
status and can inject partial chunks, delayed replies, failures and resets without hardware.
It rejects unexpected read-only commands so tests detect accidental motion/setting traffic.

## Pure parser/controller
Parser accepts strict bounded GRBL1.1-style status and settings evidence. All numeric vectors
must have exactly three finite decimal coordinates. Unknown state remains visible; it is not
an exception merely because it is not one of the known display states. Unsupported or invalid
status has no authoritative position. General messages/ACKs do not become status reports.

MachineController has explicit connect/disconnect/tick/snapshot operations, injected Transport
and monotonic clock for deterministic tests. It owns the two-command TX allowlist, outstanding
request state, settings transaction, framing buffer and session freshness. Only this object
interprets reports into position snapshots. Every published position is mm or None. On failure,
close and invalidate even when a valid-looking previous snapshot exists. Do not mutate state
from multiple threads and do not let UI code call the transport directly.

## Qt boundary

### Concrete Python API
`models.XYZ = tuple[float, float, float]`. Frozen `GrblStatus(state: MachineState,
raw_state: str, machine_position: XYZ | None, work_position: XYZ | None,
work_offset: XYZ | None)` contains wire-unit values. Frozen `MachineSnapshot` fields:
`connection`, `state`, `raw_state`, `machine_position_mm`, `work_position_mm`,
`work_offset_mm`, `report_units`, `stale`, `last_report_at`, `diagnostic`.
Defaults are disconnected/unknown, empty text, None coordinates/units/timestamp, stale True.

`grbl.parse_status(line: str) -> GrblStatus` raises ValueError for invalid status.
`grbl.parse_report_units(line: str) -> str | None` returns `mm`/`inch` for valid $13,
None for unrelated lines, and raises ValueError for malformed $13.
`grbl.LineFramer.feed(chunk: bytes) -> tuple[str, ...]` accepts <=4096 bytes, emits
ASCII lines, and raises ValueError on invalid ASCII/oversized lines; resets its pending
buffer after failure and discards an oversized record through its next delimiter.
`LineFramer.reset() -> None` clears session framing.

`MachineController(transport: Transport, clock: Callable[[], float] = monotonic)`;
`connect() -> None`, `disconnect() -> None`, `tick() -> None`,
`snapshot() -> MachineSnapshot`. Calls are single-owner; connect records I/O errors in the
snapshot, while a duplicate connect raises ValueError. Connect sends settings/status reads
only. Tick performs one bounded read, processes records and schedules bounded read requests.

`SerialIO(port: str)` accepts physical port names only. `list_ports() -> tuple[PortInfo, ...]`
returns frozen `PortInfo(device: str, description: str)` metadata, without opening devices.
`bridge.machine.make_controller(port: str) -> MachineController` constructs the serial
controller but does not open it. The UI worker accepts a zero-argument controller factory,
called inside its run method, allowing FakeGRBL injection without GUI-owned I/O.
The worker invokes controller operations in its own thread and emits immutable snapshots.
Stop uses thread-safe interruption, always closes in finally, and reaches a finished signal.
The panel updates widgets only on the GUI thread, disables duplicate connects and keeps
Disconnect accessible during connect/connected/error states. Singleton panel opening neither
connects nor recreates a live worker. Closing waits for actual termination; it cannot dispose
of a live QThread. A late snapshot from a finished/old session must not repopulate the display.

## Validation
Tests cover both MPos and WPos, absent/intermittent WCO, mm/inch/unknown units, field order,
invalid vectors, reset/unit-change/stale invalidation, open/read/write/short-write faults,
response timeout, chunk framing/bounds, duplicate connect and repeated lifecycle closure.
Qt tests use fake transport and assert exact transmitted bytes are a subset of `{b'?', b'$$\n'}`.
No test opens a real serial device. Hardware release testing, movement, zeroing, preflight,
streaming, dry-run, terminal and laser control remain outside this contract.

## Review refinements
A GRBL startup banner cancels the previous settings transaction and immediately schedules
one fresh `$$` read. Settings responses are nonblocking event-loop state, never a three-second
blocking wait. Stop preempts them on the next bounded read/worker iteration. Failed or incomplete
settings reads leave units unknown. A malformed status invalidates position/offset and machine
state evidence; a new valid report can recover direct coordinates. Read-only status retries do
not reopen the port. A settings read is retried only after a startup banner or explicit reconnect.
